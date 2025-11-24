#!/bin/bash

# Script pour mettre à jour toutes les données Dataroma

echo "======================================"
echo "Starting Dataroma data update..."
echo "======================================"
date

# Activer l'environnement virtuel si présent
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Exécuter les scrapers dans l'ordre
echo "\n[1/4] Fetching superinvestors list..."
python -m src.dataroma.managers

echo "\n[2/4] Fetching superinvestor holdings..."
python -m src.dataroma.holdings

echo "\n[3/4] Fetching Grand Portfolio..."
python -m src.dataroma.grand_portfolio

echo "\n[4/4] Fetching real-time insider trades..."
python -m src.dataroma.realtime_insider

echo "\n======================================"
echo "Dataroma update complete!"
date
echo "======================================"