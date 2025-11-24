#!/usr/bin/env python3
"""
Smart Money Manual Data Analyzer
Analyse les données collectées manuellement via l'interface HTML
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import sys

class SmartMoneyManualAnalyzer:
    """Analyseur pour les données Smart Money collectées manuellement"""
    
    def __init__(self, json_file_path):
        """
        Initialise l'analyseur avec le fichier JSON
        
        Args:
            json_file_path: Chemin vers le fichier JSON généré par l'interface
        """
        self.json_path = Path(json_file_path)
        self.data = self._load_json()
        self.funds_df = None
        self.holdings_df = None
        self.universe = set()
        self.signals = None
        
    def _load_json(self):
        """Charge les données JSON"""
        if not self.json_path.exists():
            raise FileNotFoundError(f"Fichier non trouvé: {self.json_path}")
            
        with open(self.json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    def process_data(self):
        """Traite les données et crée les DataFrames"""
        # DataFrame des fonds
        funds = []
        for fund in self.data['top_funds']:
            funds.append({
                'fund_id': fund['fund_id'],
                'fund_name': fund['fund_name'],
                'manager': fund['portfolio_manager'],
                'perf_3y': fund['performance_3y'],
                'aum_billions': fund['aum_billions'],
                'total_holdings': fund['total_holdings'],
                'scraped_date': fund['scraped_date']
            })
        self.funds_df = pd.DataFrame(funds)
        
        # DataFrame des holdings
        holdings = []
        for fund in self.data['top_funds']:
            for holding in fund.get('top_holdings', []):
                holdings.append({
                    'fund_id': fund['fund_id'],
                    'fund_name': fund['fund_name'],
                    'position': holding['position'],
                    'ticker': holding['ticker'],
                    'company_name': holding['company_name'],
                    'portfolio_pct': holding['portfolio_pct'],
                    'shares_millions': holding['shares_owned_millions'],
                    'value_millions': holding['value_millions'],
                    'activity_pct': holding['latest_activity_pct'],
                    'avg_price': holding['avg_buy_price'],
                    'price_change_pct': holding['price_change_pct']
                })
        self.holdings_df = pd.DataFrame(holdings)
        
        # Univers unique
        self.universe = set(self.holdings_df['ticker'].unique())
        
        return self.funds_df, self.holdings_df
        
    def calculate_signals(self):
        """Calcule les signaux Smart Money pour chaque ticker"""
        if self.holdings_df is None:
            self.process_data()
            
        # Grouper par ticker
        signals = []
        for ticker in self.universe:
            ticker_data = self.holdings_df[self.holdings_df['ticker'] == ticker]
            
            # Métriques
            num_funds = len(ticker_data['fund_id'].unique())
            avg_portfolio_pct = ticker_data['portfolio_pct'].mean()
            total_value = ticker_data['value_millions'].sum()
            avg_activity = ticker_data['activity_pct'].mean()
            avg_price_change = ticker_data['price_change_pct'].mean()
            
            # Calcul du score composite (0-100)
            score_funds = min((num_funds / 10) * 30, 30)  # Max 30 points
            score_portfolio = min(avg_portfolio_pct * 10, 25)  # Max 25 points
            score_value = min((total_value / 1000) * 15, 15)  # Max 15 points
            score_momentum = min(max((avg_price_change / 100) * 15, -5), 15)  # -5 à 15 points
            score_activity = min(max((avg_activity / 50) * 15, 0), 15)  # Max 15 points
            
            total_score = score_funds + score_portfolio + score_value + score_momentum + score_activity
            
            # Signal
            if total_score >= 70:
                signal = 'STRONG BUY'
            elif total_score >= 50:
                signal = 'BUY'
            elif total_score >= 30:
                signal = 'HOLD'
            else:
                signal = 'WATCH'
                
            signals.append({
                'ticker': ticker,
                'num_funds': num_funds,
                'avg_portfolio_pct': round(avg_portfolio_pct, 2),
                'total_value_millions': round(total_value, 2),
                'avg_activity_pct': round(avg_activity, 2),
                'avg_price_change_pct': round(avg_price_change, 2),
                'smart_score': round(total_score, 1),
                'signal': signal
            })
            
        self.signals = pd.DataFrame(signals).sort_values('smart_score', ascending=False)
        return self.signals
        
    def get_top_signals(self, n=20):
        """Retourne les top N signaux"""
        if self.signals is None:
            self.calculate_signals()
        return self.signals.head(n)
        
    def get_consensus_picks(self, min_funds=3):
        """Retourne les tickers détenus par au moins min_funds fonds"""
        if self.signals is None:
            self.calculate_signals()
        return self.signals[self.signals['num_funds'] >= min_funds]
        
    def export_universe(self, output_file='smart_universe.csv'):
        """Exporte l'univers Smart Money en CSV"""
        if self.signals is None:
            self.calculate_signals()
            
        self.signals.to_csv(output_file, index=False)
        print(f"✅ Univers exporté vers {output_file}")
        return output_file
        
    def print_analysis(self):
        """Affiche l'analyse complète"""
        if self.signals is None:
            self.calculate_signals()
            
        print("\n" + "="*80)
        print("📊 ANALYSE SMART MONEY - DONNÉES MANUELLES")
        print("="*80)
        
        # Stats générales
        print(f"\n📈 STATISTIQUES GÉNÉRALES:")
        print(f"  • Nombre de fonds: {len(self.funds_df)}")
        print(f"  • Nombre total de holdings: {len(self.holdings_df)}")
        print(f"  • Tickers uniques: {len(self.universe)}")
        print(f"  • Performance moyenne 3Y: {self.funds_df['perf_3y'].mean():.2f}%")
        print(f"  • AUM total: ${self.funds_df['aum_billions'].sum():.1f}B")
        
        # Top fonds
        print(f"\n🏦 TOP FONDS PAR PERFORMANCE:")
        top_funds = self.funds_df.nlargest(5, 'perf_3y')[['fund_name', 'manager', 'perf_3y', 'aum_billions']]
        for i, (_, fund) in enumerate(top_funds.iterrows(), 1):
            print(f"  {i}. {fund['fund_name']} ({fund['manager']})")
            print(f"     Performance 3Y: {fund['perf_3y']}% | AUM: ${fund['aum_billions']}B")
        
        # Top signaux
        print(f"\n🎯 TOP 10 SIGNAUX SMART MONEY:")
        top_signals = self.get_top_signals(10)
        for i, (_, signal) in enumerate(top_signals.iterrows(), 1):
            print(f"  {i}. {signal['ticker']} - {signal['signal']} (Score: {signal['smart_score']})")
            print(f"     Fonds: {signal['num_funds']} | Portfolio: {signal['avg_portfolio_pct']}% | ")
            print(f"     Valeur: ${signal['total_value_millions']}M | Momentum: {signal['avg_price_change_pct']:.1f}%")
        
        # Consensus picks
        print(f"\n🤝 CONSENSUS PICKS (≥3 fonds):")
        consensus = self.get_consensus_picks(3)
        tickers = ', '.join(consensus['ticker'].tolist()[:15])
        print(f"  {tickers}")
        if len(consensus) > 15:
            print(f"  ... et {len(consensus) - 15} autres")
            
        print("\n" + "="*80)


def main():
    """Fonction principale"""
    import sys
    
    # Fichier JSON par défaut ou passé en argument
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        # Chercher le dernier fichier généré
        today = datetime.now().strftime('%Y-%m-%d')
        json_file = f'smart_money_data_{today}.json'
        
    try:
        print(f"📂 Chargement du fichier: {json_file}")
        analyzer = SmartMoneyManualAnalyzer(json_file)
        
        print("⚙️ Traitement des données...")
        analyzer.process_data()
        
        print("📊 Calcul des signaux...")
        analyzer.calculate_signals()
        
        # Afficher l'analyse
        analyzer.print_analysis()
        
        # Exporter les résultats
        print("\n💾 Export des résultats...")
        analyzer.export_universe('smart_universe.csv')
        
        # Top picks séparés
        top_picks = analyzer.get_top_signals(20)
        top_picks.to_csv('smart_money_top_picks.csv', index=False)
        print(f"✅ Top 20 picks exportés vers smart_money_top_picks.csv")
        
    except FileNotFoundError:
        print(f"❌ Erreur: Fichier '{json_file}' introuvable")
        print("💡 Assurez-vous d'avoir généré le JSON via l'interface HTML d'abord")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
