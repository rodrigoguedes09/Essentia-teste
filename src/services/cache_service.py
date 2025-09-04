"""
Cache Service for Medical Automation API
Handles Redis caching for schedules and availability
"""
import redis
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CacheService:
    """Redis cache service for medical appointment system"""
    
    def __init__(self, redis_host='localhost', redis_port=6379, redis_db=0):
        try:
            self.redis_client = redis.Redis(
                host=redis_host, 
                port=redis_port, 
                db=redis_db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info("✅ Redis connection established successfully")
        except redis.ConnectionError:
            logger.warning("⚠️ Redis not available, using fallback mode")
            self.redis_client = None
        except Exception as e:
            logger.error(f"❌ Redis connection error: {e}")
            self.redis_client = None
    
    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """Generate consistent cache key"""
        # Sort kwargs for consistent key generation
        sorted_kwargs = sorted(kwargs.items())
        key_data = f"{prefix}:" + ":".join([f"{k}={v}" for k, v in sorted_kwargs])
        
        # For very long keys, use hash
        if len(key_data) > 200:
            hash_suffix = hashlib.md5(key_data.encode()).hexdigest()[:8]
            return f"{prefix}:hash:{hash_suffix}"
        
        return key_data
    
    def get_available_schedules(self, date: str = None, doctor_id: int = None) -> Optional[List[Dict]]:
        """Get cached available schedules"""
        if not self.redis_client:
            return None
        
        try:
            cache_key = self._generate_cache_key(
                "schedules", 
                date=date or "all", 
                doctor_id=doctor_id or "all"
            )
            
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                schedules = json.loads(cached_data)
                logger.info(f"📋 Cache HIT for schedules: {cache_key}")
                return schedules
            
            logger.info(f"💨 Cache MISS for schedules: {cache_key}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Cache get error: {e}")
            return None
    
    def set_available_schedules(self, schedules: List[Dict], date: str = None, doctor_id: int = None, ttl: int = 300):
        """Cache available schedules with TTL (default 5 minutes)"""
        if not self.redis_client:
            return False
        
        try:
            cache_key = self._generate_cache_key(
                "schedules", 
                date=date or "all", 
                doctor_id=doctor_id or "all"
            )
            
            # Add timestamp to cached data for debugging
            cache_data = {
                "schedules": schedules,
                "cached_at": datetime.now().isoformat(),
                "total_count": len(schedules)
            }
            
            self.redis_client.setex(
                cache_key, 
                ttl, 
                json.dumps(cache_data, default=str)
            )
            
            logger.info(f"💾 Cached {len(schedules)} schedules with key: {cache_key} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Cache set error: {e}")
            return False
    
    def invalidate_schedule_cache(self, doctor_id: int = None, date: str = None):
        """Invalidate schedule cache when appointments are booked/cancelled"""
        if not self.redis_client:
            return
        
        try:
            # Patterns to delete
            patterns = [
                "schedules:*",  # All schedules
            ]
            
            if doctor_id:
                patterns.append(f"schedules:*doctor_id={doctor_id}*")
            
            if date:
                patterns.append(f"schedules:*date={date}*")
            
            deleted_count = 0
            for pattern in patterns:
                keys = self.redis_client.keys(pattern)
                if keys:
                    deleted_count += self.redis_client.delete(*keys)
            
            logger.info(f"🗑️ Invalidated {deleted_count} schedule cache entries")
            
        except Exception as e:
            logger.error(f"❌ Cache invalidation error: {e}")
    
    def get_patient_cache(self, patient_id: int) -> Optional[Dict]:
        """Get cached patient data"""
        if not self.redis_client:
            return None
        
        try:
            cache_key = f"patient:{patient_id}"
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                logger.info(f"👤 Cache HIT for patient: {patient_id}")
                return json.loads(cached_data)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Patient cache get error: {e}")
            return None
    
    def set_patient_cache(self, patient_id: int, patient_data: Dict, ttl: int = 3600):
        """Cache patient data (1 hour TTL)"""
        if not self.redis_client:
            return False
        
        try:
            cache_key = f"patient:{patient_id}"
            
            cache_data = {
                "patient": patient_data,
                "cached_at": datetime.now().isoformat()
            }
            
            self.redis_client.setex(
                cache_key, 
                ttl, 
                json.dumps(cache_data, default=str)
            )
            
            logger.info(f"👤 Cached patient {patient_id} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Patient cache set error: {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring"""
        if not self.redis_client:
            return {"status": "disabled", "reason": "Redis not available"}
        
        try:
            info = self.redis_client.info()
            
            # Get keys count by pattern
            schedule_keys = len(self.redis_client.keys("schedules:*"))
            patient_keys = len(self.redis_client.keys("patient:*"))
            
            stats = {
                "status": "active",
                "total_keys": info.get("db0", {}).get("keys", 0),
                "schedule_cache_entries": schedule_keys,
                "patient_cache_entries": patient_keys,
                "memory_usage": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "cache_hits": info.get("keyspace_hits", 0),
                "cache_misses": info.get("keyspace_misses", 0),
                "uptime": info.get("uptime_in_seconds", 0)
            }
            
            # Calculate hit rate
            total_requests = stats["cache_hits"] + stats["cache_misses"]
            if total_requests > 0:
                stats["hit_rate"] = round((stats["cache_hits"] / total_requests) * 100, 2)
            else:
                stats["hit_rate"] = 0
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Cache stats error: {e}")
            return {"status": "error", "error": str(e)}
    
    def clear_all_cache(self):
        """Clear all cache (use with caution)"""
        if not self.redis_client:
            return False
        
        try:
            self.redis_client.flushdb()
            logger.info("🧹 All cache cleared")
            return True
            
        except Exception as e:
            logger.error(f"❌ Cache clear error: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for cache service"""
        if not self.redis_client:
            return {
                "status": "unhealthy",
                "message": "Redis not available",
                "timestamp": datetime.now().isoformat()
            }
        
        try:
            # Test Redis with a simple operation
            test_key = "health_check"
            test_value = "ok"
            
            self.redis_client.setex(test_key, 10, test_value)
            retrieved_value = self.redis_client.get(test_key)
            self.redis_client.delete(test_key)
            
            if retrieved_value == test_value:
                return {
                    "status": "healthy",
                    "message": "Redis connection working",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": "Redis read/write test failed",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Redis health check failed: {e}",
                "timestamp": datetime.now().isoformat()
            }

# Global cache service instance
cache_service = CacheService()
