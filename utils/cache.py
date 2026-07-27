import logging
from typing import Callable, Any, Tuple
from django.core.cache import cache

logger = logging.getLogger(__name__)

class CacheManager:
    
    @staticmethod
    def get_or_set(key: str, fetch_func: Callable[[], Any], timeout: int = 3600) -> Tuple[Any, str]:
        
        cached_data = cache.get(key)
        
        if cached_data is not None:
            logger.info(f"[CACHE HIT] 🚀 Successfully retrieved data for key '{key}' from Redis.")
            return cached_data, "cache"
            
        logger.info(f"[CACHE MISS] 🐌 Fetching data for key '{key}' from the Database.")
        db_data = fetch_func()
        
        cache.set(key, db_data, timeout=timeout)
        
        return db_data, "database"
        
    @staticmethod
    def invalidate_basin_cache(basin_id: int) -> bool:
        
        pattern = f"basin:{basin_id}:*"
        try:
            deleted_count = cache.delete_pattern(pattern)
            logger.info(f"[CACHE INVALIDATED]  Cleared {deleted_count} cache keys for basin {basin_id}.")
            return True
        except AttributeError:
            logger.warning("[CACHE WARNING] delete_pattern not supported. Ensure 'django-redis' is set as the backend.")
            return False
