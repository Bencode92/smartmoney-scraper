"""[DEPRECATED] SmartMoney v2.5 Configuration (Legacy)

⚠️  Ce fichier est archivé pour rétrocompatibilité.
    Pour les nouveaux projets, utiliser: config_v30.py

Note: v2.5 était une version intermédiaire qui n'a jamais été 
      déployée. Elle a été remplacée par v3.0 "Buffett-Quant".

Migration:
    from config_v30 import WEIGHTS_V30, CONSTRAINTS_V30

Date d'archivage: Décembre 2025
"""

import warnings

warnings.warn(
    "config_v25 est déprécié. Utiliser config_v30.",
    DeprecationWarning,
    stacklevel=2
)

try:
    from config_v25 import *
except ImportError:
    pass
