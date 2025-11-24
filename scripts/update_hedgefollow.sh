#!/bin/bash

# Script pour mettre à jour toutes les données HedgeFollow

echo "======================================"
echo "Starting HedgeFollow data update..."
echo "======================================"
date

# Activer l'environnement virtuel si présent
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Exécuter les scrapers dans l'ordre
echo "\n[1/4] Fetching top hedge funds..."
python -m src.hedgefollow.funds

echo "\n[2/4] Fetching hedge fund holdings..."
python -m src.hedgefollow.holdings

echo "\n[3/4] Fetching insider trades..."
python -m src.hedgefollow.insiders

echo "\n[4/4] Running stock screener..."
python -m src.hedgefollow.screener

echo "\n======================================"
echo "HedgeFollow update complete!"
date
echo "======================================"