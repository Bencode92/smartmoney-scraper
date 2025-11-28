# SmartMoney Dashboard Frontend

Dashboard interactif pour visualiser le portefeuille SmartMoney avec comparaison multi-benchmarks.

## 🚀 Démarrage rapide

### Option 1 : Serveur local Python (recommandé)

```bash
# Depuis la racine du projet
cd frontend
python -m http.server 8000

# Ouvrir dans le navigateur
open http://localhost:8000/dashboard.html
```

### Option 2 : Extension VS Code Live Server

1. Installer l'extension "Live Server" dans VS Code
2. Clic droit sur `dashboard.html` → "Open with Live Server"

## 📁 Structure des données

Le dashboard charge automatiquement les fichiers depuis `../outputs/latest/` :

```
outputs/
├── latest/                  # Symlink vers le dernier dossier daté
│   ├── portfolio.json       # Données du portefeuille
│   ├── alerts.json          # Alertes actives
│   ├── backtest.json        # Comparaison benchmarks
│   └── memo.md              # Mémo d'investissement
└── 2025-11-28/
    └── ...
```

## ✨ Fonctionnalités

### 1. KPIs en un coup d'œil
- Nombre de positions
- Performance YTD
- Volatilité 30 jours
- Alpha vs S&P 500

### 2. Comparaison multi-benchmarks
| Indice | Description |
|--------|-------------|
| SmartMoney | Votre portefeuille |
| S&P 500 (SPY) | Benchmark US large cap |
| CAC 40 | Benchmark France |

Métriques comparées : Return, Volatilité, Sharpe, Max Drawdown

### 3. Graphique d'évolution
Chart.js avec courbes comparatives sur 90 jours.

### 4. Simulateur d'allocation
- Entrez votre budget (EUR ou USD)
- Calcul automatique du nombre d'actions par position
- Affichage du cash résiduel

### 5. Alertes actives
- Alertes de concentration sectorielle
- Alertes de concentration top positions
- Actions requises

### 6. Tableau détaillé
- Toutes les positions avec métriques
- Scores colorés (vert/jaune/rouge)
- Tri par poids décroissant

## 🎨 Personnalisation

### Modifier les couleurs
Éditez les variables CSS dans `:root` :

```css
:root {
  --accent: #38bdf8;      /* Couleur principale */
  --success: #22c55e;     /* Positif */
  --danger: #ef4444;      /* Négatif */
  --bg: #020617;          /* Fond */
}
```

### Modifier le chemin des données
Dans le JavaScript :

```javascript
const DATA_PATH = "../outputs/latest";  // Modifier si nécessaire
```

## 🔧 Dépendances

- [Chart.js](https://www.chartjs.org/) - Graphiques (chargé via CDN)
- [Inter Font](https://fonts.google.com/specimen/Inter) - Typographie (chargé via Google Fonts)

Aucune installation npm requise.

## 📱 Responsive

Le dashboard s'adapte automatiquement :
- Desktop : grilles 4 et 2 colonnes
- Tablette/Mobile : colonnes empilées

## ⚠️ Limitations connues

1. **CORS** : Le dashboard doit être servi via HTTP (pas `file://`) à cause des requêtes fetch
2. **Données statiques** : Les prix ne se mettent pas à jour en temps réel
3. **Graphique simplifié** : Interpolation linéaire (pas de vraies données historiques jour par jour)

## 🔄 Mise à jour des données

Les données sont régénérées automatiquement chaque semaine via GitHub Actions :
- Workflow : `.github/workflows/portfolio.yml`
- Schedule : Lundi 8h UTC

Pour régénérer manuellement :
```bash
python main.py
```
