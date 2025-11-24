#!/bin/bash
# Script pour lancer le pipeline HedgeFollow facilement

set -e  # Exit on error

echo "🚀 HedgeFollow Pipeline Launcher"
echo "================================"

# Activer l'environnement virtuel si présent
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "📦 Activating virtual environment..."
    source .venv/bin/activate
fi

# Vérifier les dépendances
echo "🔍 Checking dependencies..."
python -c "import pandas; import requests; import loguru" 2>/dev/null || {
    echo "❌ Missing dependencies. Installing..."
    pip install -r requirements.txt
}

# Parser les arguments
MODE="${1:-full}"
VERBOSE="${2:-}"

echo ""
echo "📊 Configuration:"
echo "  • Mode: $MODE"
echo "  • Verbose: $([ "$VERBOSE" = "--verbose" ] && echo "Yes" || echo "No")"
echo ""

case $MODE in
    test)
        echo "🧪 Running in TEST mode (minimal scraping)..."
        python run_hedgefollow.py --mode test $VERBOSE
        ;;
    quick)
        echo "⚡ Running in QUICK mode (15 funds, 10 holdings)..."
        python run_hedgefollow.py --mode quick $VERBOSE
        ;;
    full)
        echo "💯 Running in FULL mode (20 funds, 20 holdings)..."
        python run_hedgefollow.py --mode full $VERBOSE
        ;;
    dry-run)
        echo "🔍 Running DRY-RUN (configuration check only)..."
        python run_hedgefollow.py --dry-run $VERBOSE
        ;;
    custom)
        echo "⚙️ Running with CUSTOM parameters..."
        shift  # Remove 'custom' from args
        python run_hedgefollow.py $@
        ;;
    *)
        echo "❌ Invalid mode: $MODE"
        echo ""
        echo "Usage: $0 [mode] [options]"
        echo ""
        echo "Modes:"
        echo "  test      - Test mode (5 funds, 3 top, 5 holdings)"
        echo "  quick     - Quick mode (15 funds, 10 top, 10 holdings)"
        echo "  full      - Full mode (20 funds, 10 top, 20 holdings) [default]"
        echo "  dry-run   - Check configuration without scraping"
        echo "  custom    - Custom parameters (pass directly to script)"
        echo ""
        echo "Options:"
        echo "  --verbose - Enable debug logging"
        echo ""
        echo "Examples:"
        echo "  $0              # Run full pipeline"
        echo "  $0 test         # Run test mode"
        echo "  $0 quick --verbose  # Quick mode with debug"
        echo "  $0 custom --funds 30 --top 15 --holdings 25"
        exit 1
        ;;
esac

# Afficher les résultats
echo ""
echo "✅ Pipeline completed!"
echo ""
echo "📁 Output files:"
ls -lh data/raw/hedgefollow/*.csv 2>/dev/null | tail -5 || echo "  No files found yet"

echo ""
echo "📊 To analyze results:"
echo "  python -c \"import pandas as pd; df=pd.read_csv('data/raw/hedgefollow/funds_top10_filtered.csv'); print(df[['fund_name','perf_3y_annualized','aum_billions']].to_string())\""
