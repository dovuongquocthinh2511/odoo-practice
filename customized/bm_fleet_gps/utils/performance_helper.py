# -*- coding: utf-8 -*-

"""
Performance optimization utilities for bm_fleet_gps module

This module provides caching and performance monitoring utilities
to optimize database queries and computed field calculations.
"""

import logging
import time
from functools import lru_cache, wraps
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


def performance_monitor(func):
    """Decorator to monitor and log function performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time

            # Log slow operations (> 1 second)
            if execution_time > 1.0:
                _logger.warning(
                    f"Slow operation detected: {func.__name__} took {execution_time:.2f}s"
                )

            return result
        except Exception as e:
            execution_time = time.time() - start_time
            _logger.error(
                f"Error in {func.__name__} after {execution_time:.2f}s: {e}"
            )
            raise
    return wrapper


class GPSDataCache:
    """Cache manager for GPS data to reduce database queries"""

    def __init__(self, env, cache_ttl=300):  # 5 minutes default TTL
        self.env = env
        self.cache_ttl = cache_ttl
        self._cache = {}
        self._cache_timestamps = {}

    def _is_cache_valid(self, key):
        """Check if cached data is still valid"""
        if key not in self._cache_timestamps:
            return False

        age = datetime.now() - self._cache_timestamps[key]
        return age.total_seconds() < self.cache_ttl

    def get_latest_waypoint(self, vehicle_id):
        """Get latest waypoint from cache or database"""
        cache_key = f'latest_waypoint_{vehicle_id}'

        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        # Query database with optimized query
        Journey = self.env['bm.fleet.transportation.journey']
        latest_waypoint = Journey.search_read([
            ('vehicle_id', '=', vehicle_id),
            ('timestamp', '>=', datetime.now() - timedelta(days=1))
        ], fields=['latitude', 'longitude', 'timestamp', 'speed', 'address'],
        order='timestamp desc, id desc', limit=1)

        result = latest_waypoint[0] if latest_waypoint else None

        # Cache the result
        self._cache[cache_key] = result
        self._cache_timestamps[cache_key] = datetime.now()

        return result

    def get_vehicle_status(self, vehicle_id):
        """Get vehicle status from cache or database"""
        cache_key = f'vehicle_status_{vehicle_id}'

        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        # Calculate status from latest waypoint
        latest_wp = self.get_latest_waypoint(vehicle_id)

        if not latest_wp:
            status = 'offline'
        else:
            now = datetime.now()
            time_diff = (now - latest_wp['timestamp']).total_seconds() / 60

            if time_diff > 30:
                status = 'offline'
            elif latest_wp.get('machine_status', False):
                status = 'running'
            else:
                status = 'idle'

        # Cache the result
        self._cache[cache_key] = status
        self._cache_timestamps[cache_key] = datetime.now()

        return status

    def invalidate_cache(self, vehicle_id=None):
        """Invalidate cache for specific vehicle or all vehicles"""
        if vehicle_id:
            keys_to_remove = [
                f'latest_waypoint_{vehicle_id}',
                f'vehicle_status_{vehicle_id}'
            ]
            for key in keys_to_remove:
                self._cache.pop(key, None)
                self._cache_timestamps.pop(key, None)
        else:
            self._cache.clear()
            self._cache_timestamps.clear()

    def cleanup_expired_cache(self):
        """Remove expired cache entries"""
        current_time = datetime.now()
        expired_keys = []

        for key, timestamp in self._cache_timestamps.items():
            age = current_time - timestamp
            if age.total_seconds() > self.cache_ttl:
                expired_keys.append(key)

        for key in expired_keys:
            self._cache.pop(key, None)
            self._cache_timestamps.pop(key, None)

        if expired_keys:
            _logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")


class QueryOptimizer:
    """Utility class for optimizing database queries"""

    @staticmethod
    @performance_monitor
    def batch_get_latest_waypoints(env, vehicle_ids):
        """Get latest waypoints for multiple vehicles in one query"""
        Journey = env['bm.fleet.transportation.journey']

        # Use DISTINCT ON pattern for optimal performance
        latest_waypoints = Journey.search_read([
            ('vehicle_id', 'in', vehicle_ids),
            ('timestamp', '>=', datetime.now() - timedelta(days=7))
        ], fields=['vehicle_id', 'latitude', 'longitude', 'timestamp', 'speed', 'address'],
        order='vehicle_id, timestamp desc, id desc')

        # Group by vehicle_id
        result = {}
        for wp in latest_waypoints:
            vehicle_id = wp['vehicle_id'][0]
            if vehicle_id not in result:  # Keep only the latest per vehicle
                result[vehicle_id] = wp

        return result

    @staticmethod
    @performance_monitor
    def get_journey_history_optimized(env, vehicle_id, start_dt, end_dt, limit=10000):
        """Get journey history with optimized query and field selection"""
        Journey = env['bm.fleet.transportation.journey']

        # Use search_read with specific fields for better performance
        waypoints = Journey.search_read([
            ('vehicle_id', '=', vehicle_id),
            ('timestamp', '>=', start_dt),
            ('timestamp', '<=', end_dt)
        ], fields=['latitude', 'longitude', 'timestamp', 'speed',
                  'machine_status', 'gps_status', 'address', 'distance'],
        order='timestamp asc', limit=limit)

        return waypoints

    @staticmethod
    @performance_monitor
    def get_vehicle_statistics_optimized(env, vehicle_ids, date_start=None, date_end=None):
        """Get vehicle statistics using read_group for aggregation"""
        Journey = env['bm.fleet.transportation.journey']

        domain = [('vehicle_id', 'in', vehicle_ids)]
        if date_start:
            domain.append(('timestamp', '>=', date_start))
        if date_end:
            domain.append(('timestamp', '<=', date_end))

        # Use read_group for efficient aggregation
        stats = Journey.read_group(
            domain=domain,
            fields=['distance:sum', 'machine_status'],
            groupby=['vehicle_id', 'machine_status'],
            lazy=False
        )

        return stats


class PerformanceMetrics:
    """Track and report performance metrics"""

    def __init__(self):
        self.metrics = {}

    def record_query_time(self, query_name, execution_time, record_count=None):
        """Record query execution time"""
        if query_name not in self.metrics:
            self.metrics[query_name] = {
                'total_time': 0,
                'call_count': 0,
                'record_count': 0,
                'max_time': 0,
                'min_time': float('inf')
            }

        metrics = self.metrics[query_name]
        metrics['total_time'] += execution_time
        metrics['call_count'] += 1
        metrics['max_time'] = max(metrics['max_time'], execution_time)
        metrics['min_time'] = min(metrics['min_time'], execution_time)

        if record_count:
            metrics['record_count'] += record_count

    def get_performance_report(self):
        """Generate performance report"""
        report = []
        for query_name, metrics in self.metrics.items():
            if metrics['call_count'] > 0:
                avg_time = metrics['total_time'] / metrics['call_count']
                report.append({
                    'query': query_name,
                    'call_count': metrics['call_count'],
                    'avg_time': round(avg_time, 3),
                    'max_time': round(metrics['max_time'], 3),
                    'min_time': round(metrics['min_time'], 3),
                    'total_time': round(metrics['total_time'], 3),
                    'total_records': metrics['record_count']
                })

        return sorted(report, key=lambda x: x['total_time'], reverse=True)

    def log_slow_queries(self, threshold=1.0):
        """Log queries that exceed threshold"""
        for query_name, metrics in self.metrics.items():
            if metrics['call_count'] > 0:
                avg_time = metrics['total_time'] / metrics['call_count']
                if avg_time > threshold:
                    _logger.warning(
                        f"Slow query alert: {query_name} - "
                        f"Avg: {avg_time:.2f}s, "
                        f"Max: {metrics['max_time']:.2f}s, "
                        f"Calls: {metrics['call_count']}"
                    )


# Global performance metrics instance
performance_metrics = PerformanceMetrics()