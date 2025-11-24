#!/usr/bin/env python
"""
Pipeline Smart Money Complet : Funds → Holdings → Univers → Insiders → HF Trades → Signaux

Stratégie exacte:
1. Top 20 fonds par AUM
2. Top 10 par performance 3Y
3. Top 30 holdings par fond
4. Créer univers de tickers
5. Filtrer insiders et HF trades sur cet univers
6. Générer signaux consolidés
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd
from loguru import logger
from typing import Tuple, Dict, Any

# Ajouter le chemin du projet
sys.path.insert(0, str(Path(__file__).parent))

from src.hedgefollow.smart_money_pipeline import HedgeFollowSmartMoneyPipeline
from src.hedgefollow.insider_tracker import InsiderTradingTracker
from src.hedgefollow.hf_tracker import HedgeFundTracker
from src.utils.monitoring import metrics, check_scraping_health
from src.config import RAW_HF_DIR
from src.utils.io import save_df


def setup_logging(verbose: bool = False):
    """Configure le logging."""
    logger.remove()
    
    level = "DEBUG" if verbose else "INFO"
    
    # Console colorée
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level=level,
        colorize=True
    )
    
    # Fichier de log
    log_file = Path("logs") / f"smart_money_{datetime.now():%Y%m%d_%H%M%S}.log"
    log_file.parent.mkdir(exist_ok=True)
    logger.add(log_file, level="DEBUG")
    
    return log_file


def run_smart_money_pipeline(
    top_n_aum: int = 20,
    top_n_perf: int = 10,
    top_n_holdings: int = 30
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """
    Execute le pipeline Smart Money principal.
    
    Returns:
        Tuple (funds, holdings, universe)
    """
    logger.info("=" * 70)
    logger.info("📊 PHASE 1: SMART MONEY UNIVERSE CONSTRUCTION")
    logger.info("=" * 70)
    
    pipeline = HedgeFollowSmartMoneyPipeline(
        top_n_aum=top_n_aum,
        top_n_perf=top_n_perf,
        top_n_holdings=top_n_holdings
    )
    
    # Exécuter le pipeline
    df_funds, df_holdings, universe = pipeline.run_full_pipeline()
    
    # Stats
    logger.info(f"\n✅ Smart Money Universe built:")
    logger.info(f"  • Elite funds: {len(df_funds)}")
    logger.info(f"  • Total positions: {len(df_holdings)}")
    logger.info(f"  • Unique tickers: {len(universe)}")
    
    return df_funds, df_holdings, universe


def run_insider_tracking(universe: set, min_value_musd: float = 5.0) -> pd.DataFrame:
    """
    Execute le tracking des insiders sur l'univers.
    
    Returns:
        DataFrame des trades insiders filtrés
    """
    logger.info("\n" + "=" * 70)
    logger.info("🕵️ PHASE 2: INSIDER TRADING ANALYSIS")
    logger.info("=" * 70)
    
    tracker = InsiderTradingTracker(min_value_musd=min_value_musd)
    
    # Scraper les trades
    df_all = tracker.scrape_insider_trades(timeframe="1 Week")
    
    if df_all.empty:
        logger.warning("No insider trades found")
        return pd.DataFrame()
    
    # Filtrer sur univers
    df_filtered = tracker.filter_by_universe(universe, df_all)
    
    # Générer signaux
    signals = tracker.get_insider_signals(lookback_days=7)
    
    if not signals.empty:
        save_df(signals, RAW_HF_DIR.parent / "processed" / "insider_buy_signals.csv")
    
    return df_filtered


def run_hedgefund_tracking(universe: set, min_value_musd: float = 5.0) -> Dict[str, pd.DataFrame]:
    """
    Execute le tracking des hedge funds sur l'univers.
    
    Returns:
        Dict avec trades filtrés et analyses
    """
    logger.info("\n" + "=" * 70)
    logger.info("📈 PHASE 3: HEDGE FUND TRADES ANALYSIS")
    logger.info("=" * 70)
    
    tracker = HedgeFundTracker(min_value_musd=min_value_musd)
    
    # Scraper les trades
    df_all = tracker.scrape_hedgefund_trades(filter_type="all")
    
    if df_all.empty:
        logger.warning("No HF trades found")
        return {}
    
    # Filtrer sur univers
    df_filtered = tracker.filter_by_universe(universe, df_all)
    
    # Consensus signals
    consensus = tracker.get_consensus_signals(min_funds=3)
    if not consensus.empty:
        save_df(consensus, RAW_HF_DIR.parent / "processed" / "hf_consensus_signals.csv")
    
    # Flow analysis
    flows = tracker.get_smart_money_flow()
    if flows and not flows['all_flows'].empty:
        save_df(flows['all_flows'], RAW_HF_DIR.parent / "processed" / "smart_money_flows.csv")
    
    return {
        'trades': df_filtered,
        'consensus': consensus,
        'flows': flows.get('all_flows', pd.DataFrame())
    }


def generate_consolidated_signals(
    holdings: pd.DataFrame,
    insiders: pd.DataFrame,
    hf_data: Dict[str, pd.DataFrame]
) -> pd.DataFrame:
    """
    Génère les signaux consolidés Smart Money.
    
    Returns:
        DataFrame des signaux consolidés avec score
    """
    logger.info("\n" + "=" * 70)
    logger.info("🎯 PHASE 4: CONSOLIDATED SIGNALS GENERATION")
    logger.info("=" * 70)
    
    # Créer un DataFrame de base avec tous les tickers
    all_tickers = set()
    
    # Tickers des holdings
    if not holdings.empty:
        all_tickers.update(holdings['ticker'].unique())
    
    # Tickers des insiders
    if not insiders.empty:
        all_tickers.update(insiders['ticker'].unique())
    
    # Tickers des HF trades
    if 'trades' in hf_data and not hf_data['trades'].empty:
        all_tickers.update(hf_data['trades']['ticker'].unique())
    
    # Créer DataFrame de signaux
    signals = pd.DataFrame({'ticker': sorted(list(all_tickers))})
    
    # Score basé sur présence dans holdings (combien de funds détiennent)
    if not holdings.empty:
        holdings_score = holdings.groupby('ticker').agg({
            'fund_id': 'count',
            'portfolio_pct': 'mean',
            'value_millions': 'sum'
        }).rename(columns={
            'fund_id': 'num_funds_holding',
            'portfolio_pct': 'avg_portfolio_pct',
            'value_millions': 'total_value_millions'
        })
        signals = signals.merge(holdings_score, on='ticker', how='left')
    else:
        signals['num_funds_holding'] = 0
        signals['avg_portfolio_pct'] = 0
        signals['total_value_millions'] = 0
    
    # Score basé sur insiders (achats récents)
    if not insiders.empty:
        insider_buys = insiders[insiders['trade_type'].str.contains('Buy', case=False, na=False)]
        if not insider_buys.empty:
            insider_score = insider_buys.groupby('ticker').agg({
                'transaction_value_millions': 'sum',
                'insider_name': 'count'
            }).rename(columns={
                'transaction_value_millions': 'insider_buy_millions',
                'insider_name': 'num_insiders_buying'
            })
            signals = signals.merge(insider_score, on='ticker', how='left')
        else:
            signals['insider_buy_millions'] = 0
            signals['num_insiders_buying'] = 0
    else:
        signals['insider_buy_millions'] = 0
        signals['num_insiders_buying'] = 0
    
    # Score basé sur consensus HF
    if 'consensus' in hf_data and not hf_data['consensus'].empty:
        consensus_score = hf_data['consensus'][['num_funds', 'total_value_millions']].rename(columns={
            'num_funds': 'hf_consensus_funds',
            'total_value_millions': 'hf_buy_millions'
        })
        signals = signals.merge(consensus_score, on='ticker', how='left')
    else:
        signals['hf_consensus_funds'] = 0
        signals['hf_buy_millions'] = 0
    
    # Score basé sur flow net
    if 'flows' in hf_data and not hf_data['flows'].empty:
        flow_score = hf_data['flows'][['net_flow_millions', 'flow_ratio']]
        signals = signals.merge(flow_score, on='ticker', how='left')
    else:
        signals['net_flow_millions'] = 0
        signals['flow_ratio'] = 1
    
    # Remplir les NaN
    signals = signals.fillna(0)
    
    # Calculer un score composite (0-100)
    signals['score_holdings'] = (signals['num_funds_holding'] / 10 * 30).clip(upper=30)  # Max 30 points
    signals['score_portfolio'] = (signals['avg_portfolio_pct'] * 2).clip(upper=20)  # Max 20 points
    signals['score_insiders'] = (signals['num_insiders_buying'] * 5).clip(upper=20)  # Max 20 points
    signals['score_hf_consensus'] = (signals['hf_consensus_funds'] * 3).clip(upper=15)  # Max 15 points
    signals['score_flow'] = ((signals['net_flow_millions'] / 100) * 15).clip(lower=0, upper=15)  # Max 15 points
    
    signals['total_score'] = (
        signals['score_holdings'] +
        signals['score_portfolio'] +
        signals['score_insiders'] +
        signals['score_hf_consensus'] +
        signals['score_flow']
    ).round(1)
    
    # Classification
    def classify_signal(score):
        if score >= 70:
            return 'STRONG BUY'
        elif score >= 50:
            return 'BUY'
        elif score >= 30:
            return 'HOLD'
        else:
            return 'WATCH'
    
    signals['signal'] = signals['total_score'].apply(classify_signal)
    
    # Trier par score
    signals = signals.sort_values('total_score', ascending=False)
    
    # Sauvegarder
    save_df(signals, RAW_HF_DIR.parent / "processed" / "consolidated_smart_signals.csv")
    
    # Afficher top signaux
    logger.info("\n🏆 TOP 10 SMART MONEY SIGNALS:")
    logger.info("-" * 70)
    
    for idx, row in signals.head(10).iterrows():
        logger.info(
            f"{idx+1:2d}. {row['ticker']:6s} | Score: {row['total_score']:5.1f} | "
            f"Signal: {row['signal']:10s} | "
            f"Funds: {row['num_funds_holding']:.0f} | "
            f"Insiders: {row['num_insiders_buying']:.0f} | "
            f"HF Consensus: {row['hf_consensus_funds']:.0f}"
        )
    
    # Stats par signal
    signal_counts = signals['signal'].value_counts()
    logger.info("\n📊 Signal Distribution:")
    for signal, count in signal_counts.items():
        logger.info(f"  • {signal}: {count} tickers")
    
    return signals


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(description="Smart Money Complete Pipeline")
    
    parser.add_argument(
        "--mode",
        choices=["full", "quick", "test"],
        default="full",
        help="Execution mode"
    )
    
    parser.add_argument(
        "--top-aum",
        type=int,
        help="Number of top AUM funds (default: 20)"
    )
    
    parser.add_argument(
        "--top-perf",
        type=int,
        help="Number of top performers to keep (default: 10)"
    )
    
    parser.add_argument(
        "--holdings",
        type=int,
        help="Number of holdings per fund (default: 30)"
    )
    
    parser.add_argument(
        "--min-value",
        type=float,
        default=5.0,
        help="Minimum transaction value in millions USD (default: 5.0)"
    )
    
    parser.add_argument(
        "--skip-insiders",
        action="store_true",
        help="Skip insider trading analysis"
    )
    
    parser.add_argument(
        "--skip-hf",
        action="store_true",
        help="Skip hedge fund tracker analysis"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_file = setup_logging(args.verbose)
    
    logger.info("=" * 70)
    logger.info("🚀 SMART MONEY COMPLETE PIPELINE")
    logger.info("=" * 70)
    logger.info(f"📝 Log file: {log_file}")
    
    # Configuration selon le mode
    if args.mode == "test":
        n_aum = args.top_aum or 10
        n_perf = args.top_perf or 5
        n_holdings = args.holdings or 10
        logger.info("🧪 Mode TEST - Minimal configuration")
    elif args.mode == "quick":
        n_aum = args.top_aum or 15
        n_perf = args.top_perf or 8
        n_holdings = args.holdings or 20
        logger.info("⚡ Mode QUICK - Fast configuration")
    else:  # full
        n_aum = args.top_aum or 20
        n_perf = args.top_perf or 10
        n_holdings = args.holdings or 30
        logger.info("💯 Mode FULL - Complete configuration")
    
    logger.info(f"\n📊 Configuration:")
    logger.info(f"  • Top funds by AUM: {n_aum}")
    logger.info(f"  • Top performers to keep: {n_perf}")
    logger.info(f"  • Holdings per fund: {n_holdings}")
    logger.info(f"  • Min transaction value: ${args.min_value}M")
    logger.info(f"  • Include insiders: {not args.skip_insiders}")
    logger.info(f"  • Include HF tracker: {not args.skip_hf}")
    
    try:
        start_time = datetime.now()
        
        # Phase 1: Smart Money Universe
        df_funds, df_holdings, universe = run_smart_money_pipeline(
            top_n_aum=n_aum,
            top_n_perf=n_perf,
            top_n_holdings=n_holdings
        )
        
        # Convertir universe en set
        universe_set = set(universe.values)
        
        # Phase 2: Insider Trading (optionnel)
        df_insiders = pd.DataFrame()
        if not args.skip_insiders:
            df_insiders = run_insider_tracking(universe_set, args.min_value)
        
        # Phase 3: HF Tracker (optionnel)
        hf_data = {}
        if not args.skip_hf:
            hf_data = run_hedgefund_tracking(universe_set, args.min_value)
        
        # Phase 4: Consolidated Signals
        signals = generate_consolidated_signals(df_holdings, df_insiders, hf_data)
        
        # Durée totale
        duration = (datetime.now() - start_time).total_seconds()
        
        # Résumé final
        logger.info("\n" + "=" * 70)
        logger.info("✅ SMART MONEY PIPELINE COMPLETED!")
        logger.info("=" * 70)
        logger.info(f"⏱️  Total duration: {duration:.1f} seconds")
        logger.info(f"\n📊 Summary:")
        logger.info(f"  • Elite funds analyzed: {len(df_funds)}")
        logger.info(f"  • Holdings collected: {len(df_holdings)}")
        logger.info(f"  • Universe tickers: {len(universe_set)}")
        
        if not df_insiders.empty:
            logger.info(f"  • Insider trades (filtered): {len(df_insiders)}")
        
        if hf_data and 'trades' in hf_data:
            logger.info(f"  • HF trades (filtered): {len(hf_data['trades'])}")
        
        logger.info(f"  • Total signals generated: {len(signals)}")
        
        # Top 3 signaux
        logger.info(f"\n🏆 Top 3 Signals:")
        for idx, row in signals.head(3).iterrows():
            logger.info(
                f"  {idx+1}. {row['ticker']}: {row['signal']} "
                f"(Score: {row['total_score']:.1f})"
            )
        
        logger.info(f"\n💾 Data saved in: {RAW_HF_DIR.parent}")
        logger.info(f"📝 Full logs in: {log_file}")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        logger.exception("Stack trace:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
