"""
Utilitaires pour les requêtes HTTP avec retry, throttling et anti-détection.
"""
import time
import random
from typing import Optional, Dict, Any, List
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

# Liste de User-Agents réalistes et récents
USER_AGENTS = [
    # Chrome sur Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    
    # Chrome sur Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    
    # Firefox sur Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    
    # Safari sur Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    
    # Edge sur Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    
    # Chrome sur Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    
    # Mobile Chrome
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
]

# Liste de langues pour varier Accept-Language
ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "fr-FR,fr;q=0.9,en;q=0.8",
    "en-GB,en;q=0.9",
    "es-ES,es;q=0.9,en;q=0.8",
    "de-DE,de;q=0.9,en;q=0.8",
    "it-IT,it;q=0.9,en;q=0.8",
    "pt-BR,pt;q=0.9,en;q=0.8",
]

# Liste de referers communs
REFERERS = [
    "https://www.google.com/",
    "https://www.bing.com/",
    "https://duckduckgo.com/",
    "",  # Pas de referer
]


class SmartSession:
    """Session HTTP intelligente avec rotation de headers et anti-détection."""
    
    def __init__(self, use_rotating_headers: bool = True, proxies: List[str] = None):
        """
        Initialise une session intelligente.
        
        Args:
            use_rotating_headers: Si True, utilise des headers rotatifs
            proxies: Liste de proxies à utiliser (format: http://ip:port)
        """
        self.use_rotating_headers = use_rotating_headers
        self.proxies = proxies or []
        self.proxy_index = 0
        self.request_count = 0
        self.last_request_time = 0
        
        self._init_session()
    
    def _init_session(self):
        """Initialise la session requests avec retry strategy."""
        self.session = requests.Session()
        
        # Stratégie de retry
        retry_strategy = Retry(
            total=MAX_RETRIES,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
            backoff_factor=1.5,  # Backoff exponentiel
            raise_on_status=False
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Headers de base
        self._set_default_headers()
    
    def _set_default_headers(self):
        """Configure les headers par défaut."""
        self.session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
        })
    
    def _rotate_headers(self):
        """Fait tourner les headers pour éviter la détection."""
        if not self.use_rotating_headers:
            self.session.headers["User-Agent"] = HTTP_USER_AGENT
            return
        
        # User-Agent aléatoire
        self.session.headers["User-Agent"] = random.choice(USER_AGENTS)
        
        # Accept-Language aléatoire
        self.session.headers["Accept-Language"] = random.choice(ACCEPT_LANGUAGES)
        
        # Referer aléatoire (parfois)
        if random.random() > 0.5:
            referer = random.choice(REFERERS)
            if referer:
                self.session.headers["Referer"] = referer
            elif "Referer" in self.session.headers:
                del self.session.headers["Referer"]
        
        # Varier l'ordre des headers (certains sites le vérifient)
        headers = dict(self.session.headers)
        self.session.headers.clear()
        items = list(headers.items())
        random.shuffle(items)
        self.session.headers.update(dict(items))
    
    def _get_proxy(self) -> Optional[Dict[str, str]]:
        """Retourne le prochain proxy de la liste."""
        if not self.proxies:
            return None
        
        proxy = self.proxies[self.proxy_index]
        self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        
        return {
            "http": proxy,
            "https": proxy
        }
    
    def _smart_throttle(self):
        """Throttling intelligent basé sur le comportement."""
        # Calculer le temps depuis la dernière requête
        time_since_last = time.time() - self.last_request_time
        
        # Ajuster le délai selon le nombre de requêtes
        if self.request_count > 0:
            # Délai de base avec variation aléatoire
            base_delay = REQUESTS_SLEEP_SECONDS
            
            # Ajouter de la variation (±30%)
            variation = base_delay * 0.3
            delay = base_delay + random.uniform(-variation, variation)
            
            # Augmenter le délai tous les 10 requêtes
            if self.request_count % 10 == 0:
                delay += random.uniform(2, 5)
                logger.debug(f"Pause longue après {self.request_count} requêtes")
            
            # Attendre si nécessaire
            if time_since_last < delay:
                sleep_time = delay - time_since_last
                logger.debug(f"Throttling: sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> requests.Response:
        """
        Effectue une requête GET avec anti-détection.
        
        Args:
            url: URL à récupérer
            params: Paramètres GET
            headers: Headers supplémentaires
            **kwargs: Arguments supplémentaires pour requests
            
        Returns:
            Response object
        """
        # Rotation des headers
        self._rotate_headers()
        
        # Headers supplémentaires
        if headers:
            self.session.headers.update(headers)
        
        # Proxy si disponible
        proxies = self._get_proxy()
        if proxies:
            kwargs["proxies"] = proxies
        
        # Timeout par défaut
        if "timeout" not in kwargs:
            kwargs["timeout"] = TIMEOUT_SECONDS
        
        # Throttling intelligent
        self._smart_throttle()
        
        # Log de debug
        logger.debug(f"GET {url} (UA: {self.session.headers['User-Agent'][:50]}...)")
        
        try:
            response = self.session.get(url, params=params, **kwargs)
            
            # Log du statut
            if response.status_code == 200:
                logger.info(f"✅ {url} - {response.status_code}")
            else:
                logger.warning(f"⚠️ {url} - {response.status_code}")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Request failed for {url}: {e}")
            raise


# Instance globale de session intelligente
smart_session = SmartSession()


def fetch_html(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    max_retries: int = MAX_RETRIES,
    use_smart_session: bool = True
) -> str:
    """
    Récupère le contenu HTML d'une URL avec retry et anti-détection.
    
    Args:
        url: URL à récupérer
        params: Paramètres GET optionnels
        headers: Headers supplémentaires optionnels
        max_retries: Nombre max de tentatives
        use_smart_session: Si True, utilise la session avec anti-détection
        
    Returns:
        Le contenu HTML de la page
        
    Raises:
        RuntimeError: Si impossible de récupérer la page après tous les essais
    """
    for attempt in range(1, max_retries + 1):
        try:
            if use_smart_session:
                response = smart_session.get(url, params=params, headers=headers)
            else:
                # Fallback sur une session simple
                response = requests.get(
                    url,
                    params=params,
                    headers=headers or {"User-Agent": HTTP_USER_AGENT},
                    timeout=TIMEOUT_SECONDS
                )
            
            if response.status_code == 200:
                return response.text
            
            elif response.status_code == 404:
                raise ValueError(f"Page not found: {url}")
            
            elif response.status_code == 403:
                logger.error(f"Access forbidden (403): {url} - Possible bot detection")
                # Essayer avec un délai plus long au prochain essai
                if attempt < max_retries:
                    time.sleep(random.uniform(5, 10))
            
            elif response.status_code == 429:
                logger.warning(f"Rate limited (429): {url} - Waiting longer...")
                if attempt < max_retries:
                    time.sleep(random.uniform(10, 20))
            
            else:
                logger.warning(
                    f"HTTP {response.status_code} for {url} (attempt {attempt}/{max_retries})"
                )
                
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Request error for {url} (attempt {attempt}/{max_retries}): {e}"
            )
            
        # Backoff exponentiel avec jitter
        if attempt < max_retries:
            sleep_time = (2 ** attempt) + random.uniform(0, 3)
            logger.debug(f"Retry {attempt}/{max_retries} in {sleep_time:.1f}s...")
            time.sleep(sleep_time)
    
    raise RuntimeError(f"Failed to fetch {url} after {max_retries} attempts")


def fetch_json(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    use_smart_session: bool = True
) -> Dict[str, Any]:
    """
    Récupère du JSON depuis une URL.
    
    Args:
        url: URL de l'API
        params: Paramètres GET optionnels
        headers: Headers supplémentaires optionnels
        use_smart_session: Si True, utilise la session avec anti-détection
        
    Returns:
        Les données JSON parsées
    """
    try:
        if use_smart_session:
            response = smart_session.get(url, params=params, headers=headers)
        else:
            response = requests.get(
                url,
                params=params,
                headers=headers or {"User-Agent": HTTP_USER_AGENT},
                timeout=TIMEOUT_SECONDS
            )
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch JSON from {url}: {e}")
        raise


def test_connectivity(test_url: str = "https://httpbin.org/user-agent") -> bool:
    """
    Teste la connectivité et l'anti-détection.
    
    Args:
        test_url: URL de test
        
    Returns:
        True si le test réussit
    """
    try:
        response = smart_session.get(test_url)
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Connectivity test OK - User-Agent: {data.get('user-agent', 'Unknown')}")
            return True
    except Exception as e:
        logger.error(f"Connectivity test failed: {e}")
    
    return False
