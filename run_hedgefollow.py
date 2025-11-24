#!/usr/bin/env python
"""
Script principal pour lancer le pipeline HedgeFollow.

Usage:
    python run_hedgefollow.py              # Pipeline complet (par défaut)
    python run_hedgefollow.py --quick      # Top 10 fonds, 10 holdings
    python run_hedgefollow.py --test       # Mode test (5 fonds, 5 holdings)
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime
from loguru import logger

# Ajouter le chemin du projet au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from src.hedgefollow.hedgefollow_pipeline import HedgeFollowScraper
from src.utils.monitoring import metrics, check_scraping_health
from src.config import RAW_HF_DIR


def setup_logging(verbose: bool = False):
    """Configure le logging."""
    logger.remove()
    
    if verbose:
        level = "DEBUG"
    else:
        level = "INFO"
    
    # Console avec couleurs
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level=level,
        colorize=True
    )
    
    # Fichier de log
    log_file = Path("logs") / f"hedgefollow_{datetime.now():%Y%m%d_%H%M%S}.log"
    log_file.parent.mkdir(exist_ok=True)
    logger.add(log_file, level="DEBUG")
    
    return log_file


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(description="HedgeFollow Scraping Pipeline")
    
    parser.add_argument(
        "--mode",
        choices=["full", "quick", "test"],
        default="full",
        help="Mode d'exécution: full (20/10/20), quick (15/10/10), test (5/3/5)"
    )
    
    parser.add_argument(
        "--funds",
        type=int,
        help="Nombre de fonds à scraper (override le mode)"
    )
    
    parser.add_argument(
        "--top",
        type=int,
        help="Nombre de top performers à garder (override le mode)"
    )
    
    parser.add_argument(
        "--holdings",
        type=int,
        help="Nombre de holdings par fond (override le mode)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Mode verbose (debug logs)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test sans scraper (validation config seulement)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_file = setup_logging(args.verbose)
    
    logger.info("=" * 60)
    logger.info("🚀 HEDGEFOLLOW SCRAPING PIPELINE")
    logger.info("=" * 60)
    logger.info(f"📝 Log file: {log_file}")
    
    # Configuration selon le mode
    if args.mode == "test":
        n_funds = args.funds or 5
        n_top = args.top or 3
        n_holdings = args.holdings or 5
        logger.info("🧪 Mode TEST - Configuration minimale")
    elif args.mode == "quick":
        n_funds = args.funds or 15
        n_top = args.top or 10
        n_holdings = args.holdings or 10
        logger.info("⚡ Mode QUICK - Configuration rapide")
    else:  # full
        n_funds = args.funds or 20
        n_top = args.top or 10
        n_holdings = args.holdings or 20
        logger.info("💯 Mode FULL - Configuration complète")
    
    logger.info(f"📊 Configuration:")
    logger.info(f"  • Fonds à scraper: {n_funds}")
    logger.info(f"  • Top performers à garder: {n_top}")
    logger.info(f"  • Holdings par fond: {n_holdings}")
    logger.info("")
    
    # Dry run
    if args.dry_run:
        logger.info("🔍 Dry run - Vérification de la configuration...")
        
        # Vérifier les dossiers
        if not RAW_HF_DIR.exists():
            RAW_HF_DIR.mkdir(parents=True)
            logger.info(f"  ✅ Créé: {RAW_HF_DIR}")
        else:
            logger.info(f"  ✅ Existe: {RAW_HF_DIR}")
        
        # Vérifier la santé du système
        health = check_scraping_health()
        logger.info(f"  🏥 Santé système: {health['status']}")
        
        logger.info("✅ Configuration validée - prêt pour le scraping!")
        return 0
    
    # Créer le scraper
    scraper = HedgeFollowScraper(
        top_n_funds=n_funds,
        top_n_perf=n_top,
        top_n_holdings=n_holdings
    )
    
    try:
        # Lancer le pipeline
        logger.info("🔄 Démarrage du pipeline...")
        start_time = datetime.now()
        
        df_funds, df_holdings = scraper.run_full_pipeline()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        # Résumé des résultats
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ PIPELINE TERMINÉ AVEC SUCCÈS!")
        logger.info("=" * 60)
        logger.info(f"⏱️  Durée totale: {duration:.1f} secondes")
        logger.info(f"📊 Résultats:")
        logger.info(f"  • Fonds traités: {len(df_funds)}")
        logger.info(f"  • Holdings collectées: {len(df_holdings)}")
        
        if not df_holdings.empty:
            logger.info(f"  • Tickers uniques: {df_holdings['ticker'].nunique()}")
            logger.info(f"  • Valeur totale: ${df_holdings['value_millions'].sum():.1f}M")
        
        # Métriques
        logger.info("")
        logger.info("📈 Métriques:")
        summary = metrics.get_summary()
        for metric, stats in summary["metrics_summary"].items():
            if isinstance(stats, dict):
                logger.info(f"  • {metric}: {stats.get('avg', 0):.2f} (avg)")
        
        # Top 3 fonds
        if not df_funds.empty:
            logger.info("")
            logger.info("🏆 Top 3 Hedge Funds:")
            for idx, fund in df_funds.head(3).iterrows():
                logger.info(
                    f"  {idx+1}. {fund['fund_name']}: "
                    f"{fund['perf_3y_annualized']:.1f}% perf, "
                    f"${fund['aum_billions']:.1f}B AUM"
                )
        
        # Holdings populaires
        if not df_holdings.empty:
            logger.info("")
            logger.info("📌 Top 5 Holdings Populaires:")
            top_holdings = df_holdings['ticker'].value_counts().head(5)
            for ticker, count in top_holdings.items():
                logger.info(f"  • {ticker}: {count} fonds")
        
        logger.info("")
        logger.info(f"💾 Données sauvegardées dans: {RAW_HF_DIR}")
        logger.info(f"📝 Logs complets dans: {log_file}")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ ERREUR: {e}")
        logger.exception("Stack trace:")
        
        # Afficher les métriques même en cas d'erreur
        summary = metrics.get_summary()
        if summary["total_errors"] > 0:
            logger.error(f"⚠️ Total erreurs: {summary['total_errors']}")
        
        return 1


if __name__ == "__main__":
    sys.exit(main())
