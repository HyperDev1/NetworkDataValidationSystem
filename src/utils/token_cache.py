"""
File-based token caching utility for Network Data Validation System.
Provides persistent token storage with TTL-based expiry.
"""
import json
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class TokenCache:
    """
    File-based token caching utility.
    
    Stores authentication tokens with expiry information for reuse across
    service restarts. Supports multiple networks with individual token files.
    
    Usage:
        cache = TokenCache()
        
        # Check for existing valid token
        token_data = cache.get_token('moloco')
        if token_data:
            token = token_data['token']
        else:
            # Fetch new token from API
            token = fetch_token_from_api()
            cache.save_token('moloco', token, expires_in=3600)
    """
    
    DEFAULT_CACHE_DIR = "credentials"
    TOKEN_FILE_SUFFIX = "_token.json"
    EXPIRY_BUFFER_SECONDS = 60  # Refresh token 60s before actual expiry
    
    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize TokenCache.
        
        Args:
            cache_dir: Directory for token files. Defaults to 'credentials/'
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path(self.DEFAULT_CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_file(self, network: str) -> Path:
        """Get the cache file path for a network."""
        return self.cache_dir / f"{network}{self.TOKEN_FILE_SUFFIX}"
    
    def get_token(self, network: str) -> Optional[Dict[str, Any]]:
        """
        Load cached token if valid (not expired).
        
        Args:
            network: Network identifier (e.g., 'moloco', 'inmobi', 'dt_exchange')
            
        Returns:
            Token data dict with 'token' key if valid, None otherwise
        """
        cache_file = self._get_cache_file(network)
        
        if not cache_file.exists():
            logger.debug(f"No cached token found for {network}")
            return None
        
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            
            # Check expiry
            expires_at = data.get('expires_at', 0)
            if expires_at <= time.time():
                logger.info(f"Cached token for {network} has expired")
                self.delete_token(network)
                return None
            
            remaining = int(expires_at - time.time())
            logger.debug(f"Using cached token for {network} (expires in {remaining}s)")
            return data
            
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error reading cached token for {network}: {e}")
            self.delete_token(network)
            return None
    
    def save_token(
        self,
        network: str,
        token: str,
        expires_in: int = 3600,
        token_type: str = "Bearer",
        **extra_data
    ) -> bool:
        """
        Save token with expiry information.
        
        Args:
            network: Network identifier
            token: The authentication token string
            expires_in: Token lifetime in seconds (default: 3600)
            token_type: Token type (default: 'Bearer')
            **extra_data: Additional data to store (e.g., refresh_token, scope)
            
        Returns:
            True if saved successfully, False otherwise
        """
        cache_file = self._get_cache_file(network)
        
        # Calculate expiry with buffer
        effective_expires_in = max(expires_in - self.EXPIRY_BUFFER_SECONDS, 60)
        
        data = {
            'token': token,
            'token_type': token_type,
            'expires_at': time.time() + effective_expires_in,
            'expires_in_original': expires_in,
            'created_at': time.time(),
            'created_at_human': datetime.utcnow().isoformat() + 'Z',
            'network': network,
            **extra_data
        }
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Cached token for {network} (expires in {effective_expires_in}s)")
            return True
            
        except IOError as e:
            logger.error(f"Error saving token for {network}: {e}")
            return False
    
    def delete_token(self, network: str) -> bool:
        """
        Delete cached token for a network.
        
        Args:
            network: Network identifier
            
        Returns:
            True if deleted or didn't exist, False on error
        """
        cache_file = self._get_cache_file(network)
        
        try:
            if cache_file.exists():
                cache_file.unlink()
                logger.debug(f"Deleted cached token for {network}")
            return True
        except IOError as e:
            logger.error(f"Error deleting token for {network}: {e}")
            return False
    
    def clear_all(self) -> int:
        """
        Clear all cached tokens.
        
        Returns:
            Number of tokens deleted
        """
        count = 0
        for token_file in self.cache_dir.glob(f"*{self.TOKEN_FILE_SUFFIX}"):
            try:
                token_file.unlink()
                count += 1
            except IOError:
                pass
        
        logger.info(f"Cleared {count} cached tokens")
        return count
    
    def get_token_info(self, network: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata about a cached token without returning the token itself.
        
        Args:
            network: Network identifier
            
        Returns:
            Dict with token metadata (no actual token), or None
        """
        data = self.get_token(network)
        if not data:
            return None
        
        return {
            'network': data.get('network', network),
            'token_type': data.get('token_type', 'unknown'),
            'created_at': data.get('created_at_human', 'unknown'),
            'expires_in': int(data.get('expires_at', 0) - time.time()),
            'is_valid': data.get('expires_at', 0) > time.time(),
        }
    
    def list_cached_tokens(self) -> list:
        """
        List all networks with cached tokens.
        
        Returns:
            List of network names with cached tokens
        """
        networks = []
        for token_file in self.cache_dir.glob(f"*{self.TOKEN_FILE_SUFFIX}"):
            network = token_file.stem.replace(self.TOKEN_FILE_SUFFIX.replace('.json', ''), '')
            networks.append(network)
        return networks
