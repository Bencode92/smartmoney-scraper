"""
Utilitaires pour les requêtes HTTP avec retry et throttling.
"""
import time
from typing import Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from loguru import logger

from src.config import (
    HTTP_USER_AGENT,
    REQUESTS_SLEEP_SECONDS,
    MAX_RETRIES,
    TIMEOUT_SECONDS
)

# Configuration de la session avec retry strategy
session = requests.Session()

# Stratégie de retry (compatible avec urllib3 moderne)
retry_strategy = Retry(
    total=MAX_RETRIES,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS"],  # Changé de method_whitelist à allowed_methods
    backoff_factor=1
)

adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

# Headers par défaut
session.headers.update({
    "User-Agent": HTTP_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
})


def fetch_html(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    max_retries: int = MAX_RETRIES
) -> str:
    """
    Récupère le contenu HTML d'une URL avec retry et throttling.
    
    Args:
        url: URL à récupérer
        params: Paramètres GET optionnels
        headers: Headers supplémentaires optionnels
        max_retries: Nombre max de tentatives
        
    Returns:
        Le contenu HTML de la page
        
    Raises:
        RuntimeError: Si impossible de récupérer la page après tous les essais
    """
    if headers:
        session.headers.update(headers)
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.debug(f"Fetching {url} (attempt {attempt}/{max_retries})")
            
            response = session.get(
                url,
                params=params,
                timeout=TIMEOUT_SECONDS,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully fetched {url}")
                
                # Attendre avant la prochaine requête
                time.sleep(REQUESTS_SLEEP_SECONDS)
                
                return response.text
            
            elif response.status_code == 404:
                logger.error(f"Page not found (404): {url}")
                raise ValueError(f"Page not found: {url}")
                
            else:
                logger.warning(
                    f"HTTP {response.status_code} for {url} (attempt {attempt}/{max_retries})"
                )
                
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Request error for {url} (attempt {attempt}/{max_retries}): {e}"
            )
            
        # Attendre plus longtemps entre les tentatives en cas d'erreur
        if attempt < max_retries:
            sleep_time = REQUESTS_SLEEP_SECONDS * attempt
            logger.debug(f"Sleeping {sleep_time}s before retry...")
            time.sleep(sleep_time)
    
    raise RuntimeError(f"Failed to fetch {url} after {max_retries} attempts")


def fetch_json(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Récupère du JSON depuis une URL.
    
    Args:
        url: URL de l'API
        params: Paramètres GET optionnels
        headers: Headers supplémentaires optionnels
        
    Returns:
        Les données JSON parsées
    """
    if headers:
        session.headers.update(headers)
    
    try:
        logger.debug(f"Fetching JSON from {url}")
        
        response = session.get(
            url,
            params=params,
            timeout=TIMEOUT_SECONDS,
            allow_redirects=True
        )
        
        response.raise_for_status()
        
        # Attendre avant la prochaine requête
        time.sleep(REQUESTS_SLEEP_SECONDS)
        
        return response.json()
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch JSON from {url}: {e}")
        raise
