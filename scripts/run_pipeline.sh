#!/bin/bash

# Script principal pour exécuter tout le pipeline SmartMoney

echo "#############################################"
echo "#     SmartMoney Scraper Full Pipeline     #"
echo "#############################################"
date
echo ""

# Activer l'environnement virtuel si présent
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Vérifier que les dépendances sont installées
echo "Checking dependencies..."
python -c "import requests, bs4, pandas, loguru" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Missing dependencies! Please run: pip install -r requirements.txt"
    exit 1
fi

echo "Dependencies OK"
echo ""

# Phase 1: HedgeFollow
echo "=========== PHASE 1: HedgeFollow ==========="
bash scripts/update_hedgefollow.sh
if [ $? -ne 0 ]; then
    echo "ERROR: HedgeFollow update failed!"
    exit 1
fi

echo ""

# Phase 2: Dataroma
echo "=========== PHASE 2: Dataroma =============="
bash scripts/update_dataroma.sh
if [ $? -ne 0 ]; then
    echo "ERROR: Dataroma update failed!"
    exit 1
fi

echo ""

# Phase 3: Build Universe
echo "========= PHASE 3: Build Universe =========="
echo "Aggregating all data..."
python -m src.pipelines.build_universe
if [ $? -ne 0 ]; then
    echo "ERROR: Universe building failed!"
    exit 1
fi

echo ""
echo "#############################################"
echo "#           Pipeline Complete!              #"
echo "#############################################"
date
echo ""
echo "Output files are in:"
echo "  - data/raw/hedgefollow/"
echo "  - data/raw/dataroma/"
echo "  - data/processed/"
echo ""
echo "Latest universe file:"
ls -lh data/processed/universe_smartmoney_*.csv 2>/dev/null | tail -1