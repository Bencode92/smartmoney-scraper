"""
Système de monitoring et métriques pour le scraper.
"""
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from functools import wraps
from loguru import logger


class MetricsCollector:
    """Collecteur de métriques pour monitoring."""
    
    def __init__(self, metrics_file: Path = None):
        """
        Initialise le collecteur.
        
        Args:
            metrics_file: Fichier pour sauvegarder les métriques
        """
        self.metrics_file = metrics_file or Path("data/metrics.jsonl")
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        self.current_run = {
            "start_time": datetime.now().isoformat(),
            "metrics": {},
            "errors": []
        }
    
    def record_metric(self, name: str, value: Any, tags: Dict[str, str] = None) -> None:
        """
        Enregistre une métrique.
        
        Args:
            name: Nom de la métrique
            value: Valeur
            tags: Tags optionnels
        """
        metric = {
            "timestamp": datetime.now().isoformat(),
            "name": name,
            "value": value,
            "tags": tags or {}
        }
        
        if name not in self.current_run["metrics"]:
            self.current_run["metrics"][name] = []
        
        self.current_run["metrics"][name].append(metric)
        
        # Log en temps réel
        logger.info(f"📊 {name}: {value} {tags or ''}")
        
        # Sauvegarder immédiatement
        self._append_to_file(metric)
    
    def record_error(self, error: Exception, context: str = "") -> None:
        """
        Enregistre une erreur.
        
        Args:
            error: Exception
            context: Contexte de l'erreur
        """
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "error": str(error),
            "type": type(error).__name__,
            "context": context
        }
        
        self.current_run["errors"].append(error_data)
        logger.error(f"❌ {context}: {error}")
        
        # Sauvegarder
        self._append_to_file({"error": error_data})
    
    def _append_to_file(self, data: Dict[str, Any]) -> None:
        """Ajoute une ligne au fichier de métriques."""
        try:
            with open(self.metrics_file, 'a') as f:
                f.write(json.dumps(data) + '\n')
        except Exception as e:
            logger.error(f"Impossible de sauvegarder métrique: {e}")
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Retourne un résumé des métriques.
        
        Returns:
            Dict avec statistiques
        """
        summary = {
            "run_duration": (datetime.now() - datetime.fromisoformat(self.current_run["start_time"])).total_seconds(),
            "total_errors": len(self.current_run["errors"]),
            "metrics_summary": {}
        }
        
        for metric_name, values in self.current_run["metrics"].items():
            numeric_values = [v["value"] for v in values if isinstance(v["value"], (int, float))]
            if numeric_values:
                summary["metrics_summary"][metric_name] = {
                    "count": len(values),
                    "sum": sum(numeric_values),
                    "avg": sum(numeric_values) / len(numeric_values),
                    "min": min(numeric_values),
                    "max": max(numeric_values)
                }
        
        return summary


# Instance globale
metrics = MetricsCollector()


def track_performance(metric_name: str = None):
    """
    Décorateur pour mesurer les performances d'une fonction.
    
    Args:
        metric_name: Nom de la métrique (par défaut: nom de la fonction)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            name = metric_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Enregistrer le succès
                metrics.record_metric(
                    f"{name}.success",
                    1,
                    {"duration": f"{duration:.2f}s"}
                )
                
                metrics.record_metric(
                    f"{name}.duration_seconds",
                    duration
                )
                
                # Si le résultat est un DataFrame, enregistrer le nombre de lignes
                if hasattr(result, 'shape'):
                    metrics.record_metric(
                        f"{name}.rows",
                        len(result),
                        {"columns": result.shape[1]}
                    )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                # Enregistrer l'échec
                metrics.record_metric(
                    f"{name}.failure",
                    1,
                    {"duration": f"{duration:.2f}s", "error": str(e)[:100]}
                )
                
                metrics.record_error(e, name)
                raise
        
        return wrapper
    return decorator


def track_scraping_quality(df, source: str):
    """
    Enregistre des métriques sur la qualité des données scrapées.
    
    Args:
        df: DataFrame scrapé
        source: Source des données (HEDGEFOLLOW, DATAROMA, etc.)
    """
    if df.empty:
        metrics.record_metric(f"{source}.empty_result", 1)
        return
    
    # Métriques de base
    metrics.record_metric(f"{source}.total_rows", len(df))
    metrics.record_metric(f"{source}.total_columns", len(df.columns))
    
    # Taux de remplissage par colonne
    for col in df.columns:
        fill_rate = df[col].notna().sum() / len(df) * 100
        metrics.record_metric(
            f"{source}.fill_rate.{col}",
            fill_rate,
            {"unit": "percent"}
        )
    
    # Détection d'anomalies
    if 'aum_usd' in df.columns:
        valid_aum = df['aum_usd'].dropna()
        if len(valid_aum) > 0:
            metrics.record_metric(f"{source}.aum.mean", valid_aum.mean())
            metrics.record_metric(f"{source}.aum.median", valid_aum.median())
            
            # Détection de valeurs aberrantes
            q1 = valid_aum.quantile(0.25)
            q3 = valid_aum.quantile(0.75)
            iqr = q3 - q1
            outliers = ((valid_aum < q1 - 1.5 * iqr) | (valid_aum > q3 + 1.5 * iqr)).sum()
            if outliers > 0:
                metrics.record_metric(
                    f"{source}.aum.outliers",
                    outliers,
                    {"threshold": "1.5*IQR"}
                )


class AlertManager:
    """Gestionnaire d'alertes pour les erreurs critiques."""
    
    def __init__(self, webhook_url: Optional[str] = None):
        """
        Initialise le gestionnaire d'alertes.
        
        Args:
            webhook_url: URL du webhook (Discord, Slack, etc.)
        """
        self.webhook_url = webhook_url
        self.alert_history = []
    
    def send_alert(self, title: str, message: str, level: str = "ERROR"):
        """
        Envoie une alerte.
        
        Args:
            title: Titre de l'alerte
            message: Message détaillé
            level: Niveau (INFO, WARNING, ERROR, CRITICAL)
        """
        alert = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "title": title,
            "message": message
        }
        
        self.alert_history.append(alert)
        
        # Log local
        if level == "CRITICAL":
            logger.critical(f"🚨 {title}: {message}")
        elif level == "ERROR":
            logger.error(f"❌ {title}: {message}")
        elif level == "WARNING":
            logger.warning(f"⚠️ {title}: {message}")
        else:
            logger.info(f"ℹ️ {title}: {message}")
        
        # Envoyer au webhook si configuré
        if self.webhook_url:
            self._send_webhook(alert)
    
    def _send_webhook(self, alert: Dict[str, Any]):
        """Envoie l'alerte via webhook."""
        try:
            import requests
            
            # Format pour Discord
            if "discord" in self.webhook_url.lower():
                payload = {
                    "embeds": [{
                        "title": f"{alert['level']}: {alert['title']}",
                        "description": alert['message'],
                        "color": self._get_color(alert['level']),
                        "timestamp": alert['timestamp']
                    }]
                }
            # Format générique
            else:
                payload = alert
            
            response = requests.post(self.webhook_url, json=payload, timeout=5)
            response.raise_for_status()
            
        except Exception as e:
            logger.error(f"Impossible d'envoyer alerte webhook: {e}")
    
    def _get_color(self, level: str) -> int:
        """Retourne la couleur pour Discord embed."""
        colors = {
            "CRITICAL": 0xFF0000,  # Rouge
            "ERROR": 0xFF6600,     # Orange
            "WARNING": 0xFFCC00,   # Jaune
            "INFO": 0x0099FF       # Bleu
        }
        return colors.get(level, 0x808080)


# Instance globale d'alertes
alerts = AlertManager()


def check_scraping_health():
    """
    Vérifie la santé globale du système de scraping.
    
    Returns:
        Dict avec status et métriques
    """
    health = {
        "timestamp": datetime.now().isoformat(),
        "status": "HEALTHY",
        "checks": {}
    }
    
    # Vérifier les fichiers de données
    from src.config import RAW_HF_DIR, RAW_DTR_DIR
    
    # Check HedgeFollow
    hf_files = list(RAW_HF_DIR.glob("*.csv"))
    if not hf_files:
        health["checks"]["hedgefollow_data"] = "NO_DATA"
        health["status"] = "DEGRADED"
    else:
        latest = max(hf_files, key=lambda f: f.stat().st_mtime)
        age_hours = (time.time() - latest.stat().st_mtime) / 3600
        health["checks"]["hedgefollow_data"] = {
            "latest_file": latest.name,
            "age_hours": round(age_hours, 2)
        }
        if age_hours > 48:
            health["status"] = "DEGRADED"
            alerts.send_alert(
                "Données HedgeFollow obsolètes",
                f"Dernière mise à jour il y a {age_hours:.0f} heures",
                "WARNING"
            )
    
    # Check Dataroma
    dtr_files = list(RAW_DTR_DIR.glob("*.csv"))
    if not dtr_files:
        health["checks"]["dataroma_data"] = "NO_DATA"
    else:
        latest = max(dtr_files, key=lambda f: f.stat().st_mtime)
        age_hours = (time.time() - latest.stat().st_mtime) / 3600
        health["checks"]["dataroma_data"] = {
            "latest_file": latest.name,
            "age_hours": round(age_hours, 2)
        }
    
    # Résumé des métriques récentes
    summary = metrics.get_summary()
    health["metrics_summary"] = summary
    
    if summary["total_errors"] > 5:
        health["status"] = "UNHEALTHY"
        alerts.send_alert(
            "Trop d'erreurs de scraping",
            f"{summary['total_errors']} erreurs dans la dernière exécution",
            "ERROR"
        )
    
    return health
