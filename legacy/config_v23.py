"""[DEPRECATED] SmartMoney v2.3 Configuration (Legacy)

⚠️  Ce fichier est archivé pour rétrocompatibilité.
    Pour les nouveaux projets, utiliser: config_v30.py

Différences clés v2.3 vs v3.0:
- v2.3: Smart Money 15%, Insider 10%, Momentum 5%
- v3.0: Smart Money 0%, Insider 0%, Momentum 0%

Migration:
    from config_v30 import WEIGHTS_V30, CONSTRAINTS_V30

Date d'archivage: Décembre 2025
"""

# Re-exporter depuis l'ancien fichier pour rétrocompatibilité
import warnings

warnings.warn(
    "config_v23 est déprécié. Utiliser config_v30.",
    DeprecationWarning,
    stacklevel=2
)

try:
    from config_v23 import *
except ImportError:
    pass
