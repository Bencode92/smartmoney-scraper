#!/bin/bash
# Script pour lancer le pipeline Smart Money facilement

set -e  # Exit on error

echo "🎯 Smart Money Complete Pipeline Launcher"
echo "=========================================="

# Couleurs pour output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Activer l'environnement virtuel si présent
if [ -d "venv" ]; then
    echo -e "${BLUE}📦 Activating virtual environment...${NC}"
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo -e "${BLUE}📦 Activating virtual environment...${NC}"
    source .venv/bin/activate
fi

# Vérifier les dépendances
echo -e "${BLUE}🔍 Checking dependencies...${NC}"
python -c "import pandas; import requests; import loguru" 2>/dev/null || {
    echo -e "${RED}❌ Missing dependencies. Installing...${NC}"
    pip install -r requirements.txt
}

# Parser les arguments
MODE="${1:-full}"
VERBOSE="${2:-}"

echo ""
echo -e "${YELLOW}📊 Configuration:${NC}"
echo "  • Mode: $MODE"
echo "  • Verbose: $([ "$VERBOSE" = "--verbose" ] && echo "Yes" || echo "No")"
echo ""

# Fonction pour afficher le temps écoulé
show_elapsed_time() {
    local start=$1
    local end=$(date +%s)
    local elapsed=$((end - start))
    echo -e "${GREEN}⏱️  Elapsed time: ${elapsed} seconds${NC}"
}

# Créer les dossiers nécessaires
mkdir -p data/raw/hedgefollow
mkdir -p data/processed
mkdir -p logs

case $MODE in
    test)
        echo -e "${YELLOW}🧪 Running TEST mode (minimal scraping)...${NC}"
        echo "  • 10 funds by AUM"
        echo "  • 5 top performers"
        echo "  • 10 holdings each"
        echo ""
        START=$(date +%s)
        python run_smart_money.py --mode test $VERBOSE
        show_elapsed_time $START
        ;;
    
    quick)
        echo -e "${YELLOW}⚡ Running QUICK mode...${NC}"
        echo "  • 15 funds by AUM"
        echo "  • 8 top performers"
        echo "  • 20 holdings each"
        echo ""
        START=$(date +%s)
        python run_smart_money.py --mode quick $VERBOSE
        show_elapsed_time $START
        ;;
    
    full)
        echo -e "${GREEN}💯 Running FULL mode (recommended)...${NC}"
        echo "  • 20 funds by AUM"
        echo "  • 10 top performers"
        echo "  • 30 holdings each"
        echo ""
        START=$(date +%s)
        python run_smart_money.py --mode full $VERBOSE
        show_elapsed_time $START
        ;;
    
    custom)
        echo -e "${BLUE}⚙️ Running with CUSTOM parameters...${NC}"
        shift  # Remove 'custom' from args
        python run_smart_money.py $@
        ;;
    
    analyze)
        echo -e "${BLUE}📈 Analyzing existing signals...${NC}"
        python -c "
import pandas as pd
from pathlib import Path

signals_file = Path('data/processed/consolidated_smart_signals.csv')
if signals_file.exists():
    signals = pd.read_csv(signals_file)
    
    print('\n🎯 TOP 10 SMART MONEY SIGNALS:')
    print('=' * 70)
    
    top10 = signals.head(10)
    for idx, row in top10.iterrows():
        print(f\"{idx+1:2d}. {row['ticker']:6s} | Score: {row['total_score']:5.1f} | Signal: {row['signal']:10s}\")
    
    print('\n📊 Signal Distribution:')
    print(signals['signal'].value_counts())
    
    print('\n💰 Average Metrics:')
    print(f\"  • Avg funds holding: {signals['num_funds_holding'].mean():.1f}\")
    print(f\"  • Avg portfolio %: {signals['avg_portfolio_pct'].mean():.2f}%\")
    print(f\"  • Avg insider buys: {signals['num_insiders_buying'].mean():.1f}\")
    
    strong_buys = signals[signals['signal'] == 'STRONG BUY']
    if not strong_buys.empty:
        print(f\"\n🚀 STRONG BUY tickers: {', '.join(strong_buys['ticker'].tolist())}\")
else:
    print('❌ No signals file found. Run the pipeline first!')
"
        ;;
    
    clean)
        echo -e "${YELLOW}🧹 Cleaning old data files...${NC}"
        read -p "Are you sure you want to delete all data files? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]
        then
            rm -f data/raw/hedgefollow/*.csv
            rm -f data/processed/*.csv
            echo -e "${GREEN}✅ Data files cleaned${NC}"
        else
            echo "Cancelled"
        fi
        ;;
    
    *)
        echo -e "${RED}❌ Invalid mode: $MODE${NC}"
        echo ""
        echo "Usage: $0 [mode] [options]"
        echo ""
        echo "Modes:"
        echo "  test      - Test mode (10→5→10)"
        echo "  quick     - Quick mode (15→8→20)"
        echo "  full      - Full mode (20→10→30) [default]"
        echo "  custom    - Custom parameters"
        echo "  analyze   - Analyze existing signals"
        echo "  clean     - Clean data files"
        echo ""
        echo "Options:"
        echo "  --verbose          - Enable debug logging"
        echo "  --skip-insiders   - Skip insider trading"
        echo "  --skip-hf         - Skip HF tracker"
        echo ""
        echo "Examples:"
        echo "  $0                  # Run full pipeline"
        echo "  $0 test            # Run test mode"
        echo "  $0 quick --verbose # Quick mode with debug"
        echo "  $0 analyze         # Analyze results"
        echo "  $0 custom --top-aum 25 --top-perf 12"
        exit 1
        ;;
esac

# Afficher résumé des fichiers générés
echo ""
echo -e "${BLUE}📁 Generated files:${NC}"

# Vérifier les fichiers principaux
check_file() {
    if [ -f "$1" ]; then
        SIZE=$(ls -lh "$1" | awk '{print $5}')
        LINES=$(wc -l < "$1")
        echo -e "  ${GREEN}✓${NC} $(basename $1) (${SIZE}, ${LINES} lines)"
    else
        echo -e "  ${RED}✗${NC} $(basename $1) not found"
    fi
}

echo -e "\n${YELLOW}Raw Data:${NC}"
check_file "data/raw/hedgefollow/funds_top10_aum_and_perf.csv"
check_file "data/raw/hedgefollow/holdings_top10funds_30each_*.csv"

echo -e "\n${YELLOW}Processed Data:${NC}"
check_file "data/processed/smart_universe_tickers.csv"
check_file "data/processed/consolidated_smart_signals.csv"

# Afficher les top 3 signaux si disponibles
if [ -f "data/processed/consolidated_smart_signals.csv" ]; then
    echo ""
    echo -e "${GREEN}🏆 Top 3 Signals:${NC}"
    python -c "
import pandas as pd
signals = pd.read_csv('data/processed/consolidated_smart_signals.csv')
for idx, row in signals.head(3).iterrows():
    print(f\"  {idx+1}. {row['ticker']}: {row['signal']} (Score: {row['total_score']:.1f})\")
"
fi

echo ""
echo -e "${GREEN}✅ Pipeline completed!${NC}"
echo ""
echo "Next steps:"
echo "  1. Review signals: cat data/processed/consolidated_smart_signals.csv"
echo "  2. Analyze in detail: $0 analyze"
echo "  3. Export to Excel: python -c \"import pandas as pd; pd.read_csv('data/processed/consolidated_smart_signals.csv').to_excel('smart_signals.xlsx', index=False)\""
