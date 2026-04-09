"""
Redis connection helper that supports both Railway and local development
"""

import os
import redis
import json
from typing import Optional, Dict, Any


def get_redis_url() -> Optional[str]:
    """
    Get Redis URL from environment with fallback for local development
    
    Priority:
    1. REDIS_URL (Railway service)
    2. Local Redis (redis://localhost:6379)
    
    Returns:
        str: Redis URL, or None if neither is available
    """
    # Check if Railway REDIS_URL is set
    redis_url = os.getenv('REDIS_URL')
    
    if redis_url and redis_url.strip():
        return redis_url
    
    # Fallback to local Redis for development
    return 'redis://localhost:6379'


def get_redis_client(decode_responses: bool = True) -> Optional[redis.Redis]:
    """
    Get a Redis client with fallback handling
    
    Args:
        decode_responses: Whether to decode responses as UTF-8
    
    Returns:
        redis.Redis client or None if connection fails
    """
    try:
        redis_url = get_redis_url()
        
        if not redis_url:
            print("⚠️  No Redis URL configured")
            return None
        
        client = redis.from_url(redis_url, decode_responses=decode_responses)
        
        # Test the connection
        client.ping()
        return client
        
    except Exception as e:
        print(f"⚠️  Redis connection failed (non-critical): {e}")
        print("   Real-time updates will be limited. Consider starting Redis:")
        print("   Local: redis-cli or redis-server")
        print("   Docker: docker run -d -p 6379:6379 redis")
        return None


def publish_event(channel: str, event_data: Dict[str, Any]) -> bool:
    """
    Publish an event to a Redis channel
    
    Args:
        channel: Redis channel name (e.g., 'clinic_10', 'doctor_59')
        event_data: Dictionary with event information
    
    Returns:
        bool: True if published successfully, False otherwise
    """
    try:
        client = get_redis_client()
        
        if not client:
            print(f"⚠️  Redis not available - skipping broadcast to {channel}")
            return False
        
        # Publish to the channel
        result = client.publish(channel, json.dumps(event_data))
        
        if result > 0:
            print(f"✅ Event published to '{channel}' ({result} subscribers)")
            return True
        else:
            print(f"⚠️  No subscribers for channel '{channel}'")
            return False
            
    except Exception as e:
        print(f"❌ Error publishing event to {channel}: {e}")
        return False


def subscribe_to_channel(channel: str) -> Optional[Any]:
    """
    Subscribe to a Redis channel
    
    Args:
        channel: Redis channel name
    
    Returns:
        pubsub object or None if connection fails
    """
    try:
        client = get_redis_client()
        
        if not client:
            return None
        
        pubsub = client.pubsub()
        pubsub.subscribe(channel)
        
        return pubsub
        
    except Exception as e:
        print(f"❌ Error subscribing to {channel}: {e}")
        return None
