import logging
from typing import Callable, Any, Tuple
from django.core.cache import cache

logger = logging.getLogger(__name__)

class CacheManager:
    """
    Optimized Cache Manager for Hydrocore Redis operations.
    Provides methods to safely get, set, and invalidate cache keys efficiently.
    """

    @staticmethod
    def get_or_set(key: str, fetch_func: Callable[[], Any], timeout: int = 3600) -> Tuple[Any, str]:
        """
        Retrieves data from the Redis cache if it exists.
        If it doesn't exist, executes fetch_func() to get data from the DB,
        saves it to the cache, and returns it.
        
        Args:
            key (str): The unique Redis cache key.
            fetch_func (Callable): A lambda or function that fetches data from the DB.
            timeout (int): Cache expiry time in seconds (default: 1 hour).
            
        Returns:
            Tuple[Any, str]: A tuple containing the data and a string indicating the source ('cache' or 'database').
        """
        # Attempt to retrieve the data from Redis
        cached_data = cache.get(key)
        
        if cached_data is not None:
            # Data found in cache
            logger.info(f"[CACHE HIT] 🚀 Successfully retrieved data for key '{key}' from Redis.")
            return cached_data, "cache"
            
        # Data not found; fetch from DB
        logger.info(f"[CACHE MISS] 🐌 Fetching data for key '{key}' from the Database.")
        db_data = fetch_func()
        
        # Save the freshly fetched data to Redis
        cache.set(key, db_data, timeout=timeout)
        
        return db_data, "database"
        
    @staticmethod
    def invalidate_basin_cache(basin_id: int) -> bool:
        """
        Invalidates all cache entries for a given basin using Redis pattern matching.
        This ensures stale data is wiped when new observations or events are added.
        
        Args:
            basin_id (int): The ID of the basin whose cache needs invalidation.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        pattern = f"basin:{basin_id}:*"
        try:
            # delete_pattern is highly optimized and specific to django-redis
            deleted_count = cache.delete_pattern(pattern)
            logger.info(f"[CACHE INVALIDATED] 🧹 Cleared {deleted_count} cache keys for basin {basin_id}.")
            return True
        except AttributeError:
            # Fallback warning if django-redis is not configured properly
            logger.warning("[CACHE WARNING] ⚠️ delete_pattern not supported. Ensure 'django-redis' is set as the backend.")
            return False
