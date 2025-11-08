# -*- coding: utf-8 -*-

"""
Performance tests for bm_fleet_gps module optimizations

This test module validates the performance improvements made to the GPS tracking system,
including database indexes, query optimization, and caching mechanisms.
"""

import logging
import time
from datetime import datetime, timedelta
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class TestGPSPerformanceOptimization(TransactionCase):
    """Test performance optimizations for GPS module"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vehicle_model = cls.env['fleet.vehicle']
        cls.journey_model = cls.env['bm.fleet.transportation.journey']
        cls.performance_helper = cls.env['bm.fleet.performance.helper']

    def setUp(self):
        super().setUp()
        # Create test vehicle
        self.test_vehicle = self.vehicle_model.create({
            'name': 'Test Performance Vehicle',
            'license_plate': 'TEST-PERF',
            'adsun_device_serial_number': 'TEST-DEVICE-001'
        })

        # Create test journey data (simulate 1000 waypoints over 30 days)
        self._create_test_journey_data()

    def _create_test_journey_data(self):
        """Create test journey data for performance testing"""
        now = datetime.now()
        waypoints = []

        # Create 1000 waypoints over 30 days
        for i in range(1000):
            timestamp = now - timedelta(days=30) + timedelta(minutes=i * 43)
            waypoint = {
                'vehicle_id': self.test_vehicle.id,
                'timestamp': timestamp,
                'latitude': 10.7769 + (i * 0.001),  # Saigon area coordinates
                'longitude': 106.7009 + (i * 0.001),
                'speed': 40.0 + (i % 60),
                'machine_status': i % 3 != 0,  # Vary machine status
                'gps_status': True,
                'distance': 0.5 + (i % 10) * 0.1,
            }
            waypoints.append(waypoint)

        # Create in batches for better performance
        batch_size = 100
        for i in range(0, len(waypoints), batch_size):
            batch = waypoints[i:i + batch_size]
            self.journey_model.create(batch)

    def test_database_indexes_exist(self):
        """Test that performance indexes are properly created"""
        self.cr.execute("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'bm_fleet_transportation_journey'
            AND indexname LIKE 'idx_%';
        """)
        indexes = [row[0] for row in self.cr.fetchall()]

        expected_indexes = [
            'idx_journey_vehicle_timestamp',
            'idx_journey_geocoding_sync',
            'idx_journey_vehicle_latest',
            'idx_journey_vehicle_status_timestamp'
        ]

        for expected_index in expected_indexes:
            self.assertIn(expected_index, indexes,
                         f"Expected index {expected_index} not found")

    def test_journey_history_query_performance(self):
        """Test journey history query performance improvements"""
        from ..utils.performance_helper import QueryOptimizer, performance_metrics

        # Test date range (last 7 days)
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)

        # Measure query performance
        start_query = time.time()
        waypoints = QueryOptimizer.get_journey_history_optimized(
            self.env, self.test_vehicle.id, start_time, end_time
        )
        query_time = time.time() - start_query

        # Performance assertions
        self.assertLess(query_time, 1.0, "Journey history query should complete within 1 second")
        self.assertGreater(len(waypoints), 0, "Should return waypoints")
        self.assertLessEqual(len(waypoints), 1000, "Should not exceed created waypoints")

        # Check that performance metrics are recorded
        metrics = performance_metrics.get_performance_report()
        journey_metrics = [m for m in metrics if m['query'] == 'journey_history_query']
        self.assertTrue(len(journey_metrics) > 0, "Performance metrics should be recorded")

    def test_latest_position_query_performance(self):
        """Test latest position query performance"""
        from ..utils.performance_helper import QueryOptimizer

        start_query = time.time()
        latest_positions = QueryOptimizer.batch_get_latest_waypoints(
            self.env, [self.test_vehicle.id]
        )
        query_time = time.time() - start_query

        # Performance assertions
        self.assertLess(query_time, 0.5, "Latest position query should complete within 0.5 seconds")
        self.assertIn(self.test_vehicle.id, latest_positions, "Should return latest position for test vehicle")

        latest_wp = latest_positions[self.test_vehicle.id]
        self.assertIsNotNone(latest_wp, "Latest waypoint should not be None")
        self.assertIn('latitude', latest_wp, "Should include latitude")
        self.assertIn('longitude', latest_wp, "Should include longitude")

    def test_batch_vehicle_optimization(self):
        """Test batch processing for multiple vehicles"""
        # Create additional test vehicles
        vehicles = [self.test_vehicle]
        for i in range(4):  # Create 4 more vehicles
            vehicle = self.vehicle_model.create({
                'name': f'Test Vehicle {i+2}',
                'license_plate': f'TEST{i+2}',
                'adsun_device_serial_number': f'TEST-DEVICE-{i+2:03d}'
            })
            vehicles.append(vehicle)

        # Test batch query
        start_query = time.time()
        vehicle_ids = [v.id for v in vehicles]
        latest_positions = QueryOptimizer.batch_get_latest_waypoints(self.env, vehicle_ids)
        query_time = time.time() - start_query

        # Performance assertions
        self.assertLess(query_time, 1.0, "Batch query should complete within 1 second")
        self.assertEqual(len(latest_positions), len(vehicles),
                        "Should return positions for all vehicles")

    def test_computed_field_performance(self):
        """Test computed field optimization"""
        # Test current location computation
        start_compute = time.time()
        self.test_vehicle._compute_current_location()
        compute_time = time.time() - start_compute

        self.assertLess(compute_time, 0.5, "Current location computation should be fast")
        self.assertIsNotNone(self.test_vehicle.current_latitude, "Should compute latitude")
        self.assertIsNotNone(self.test_vehicle.current_longitude, "Should compute longitude")

        # Test vehicle status computation
        start_compute = time.time()
        self.test_vehicle._compute_vehicle_status()
        compute_time = time.time() - start_compute

        self.assertLess(compute_time, 0.5, "Vehicle status computation should be fast")
        self.assertIn(self.test_vehicle.vehicle_status, ['offline', 'idle', 'running'],
                     "Should return valid status")

    def test_geocoding_sync_performance(self):
        """Test geocoding synchronization performance"""
        # Mark some waypoints as unsynced
        unsynced_waypoints = self.journey_model.search([
            ('vehicle_id', '=', self.test_vehicle.id),
            ('is_address_synced', '=', False),
            ('latitude', '!=', 0),
            ('longitude', '!=', 0)
        ], limit=50)

        if unsynced_waypoints:
            start_sync = time.time()
            # Test batch address fetching (mock the actual API call)
            result = self.journey_model.fetch_missing_addresses(limit=50, use_openstreetmap=False)
            sync_time = time.time() - start_sync

            self.assertLess(sync_time, 2.0, "Geocoding sync should complete within 2 seconds")
            self.assertIn('processed', result, "Should return processed count")
            self.assertEqual(result['processed'], len(unsynced_waypoints),
                           "Should process all unsynced waypoints")

    def test_caching_mechanism(self):
        """Test caching mechanism performance"""
        from ..utils.performance_helper import GPSDataCache

        cache = GPSDataCache(self.env, cache_ttl=60)

        # First call (cache miss)
        start_time = time.time()
        waypoint1 = cache.get_latest_waypoint(self.test_vehicle.id)
        first_call_time = time.time() - start_time

        # Second call (cache hit)
        start_time = time.time()
        waypoint2 = cache.get_latest_waypoint(self.test_vehicle.id)
        second_call_time = time.time() - start_time

        # Cache hit should be faster
        self.assertLess(second_call_time, first_call_time,
                       "Cache hit should be faster than cache miss")
        self.assertEqual(waypoint1, waypoint2, "Cached result should match original")

        # Test cache invalidation
        cache.invalidate_cache(self.test_vehicle.id)
        start_time = time.time()
        waypoint3 = cache.get_latest_waypoint(self.test_vehicle.id)
        third_call_time = time.time() - start_time

        # After invalidation, should query database again
        self.assertGreater(third_call_time, second_call_time,
                          "After invalidation should query database")

    def test_performance_monitoring(self):
        """Test performance monitoring and reporting"""
        from ..utils.performance_helper import performance_metrics

        # Simulate some queries to generate metrics
        QueryOptimizer.get_journey_history_optimized(
            self.env, self.test_vehicle.id,
            datetime.now() - timedelta(days=1),
            datetime.now()
        )

        # Generate performance report
        report = performance_metrics.get_performance_report()
        self.assertIsInstance(report, list, "Performance report should be a list")

        if report:
            metric = report[0]
            required_fields = ['query', 'call_count', 'avg_time', 'max_time', 'min_time']
            for field in required_fields:
                self.assertIn(field, metric, f"Metric should include {field}")

        # Test slow query logging
        performance_metrics.log_slow_queries(threshold=0.001)  # Low threshold for testing

    def test_query_optimization_strategies(self):
        """Test different query optimization strategies"""
        # Test field selection optimization
        start_time = time.time()
        waypoints_full = self.journey_model.search_read([
            ('vehicle_id', '=', self.test_vehicle.id)
        ], limit=100)
        full_query_time = time.time() - start_time

        start_time = time.time()
        waypoints_optimized = QueryOptimizer.get_journey_history_optimized(
            self.env, self.test_vehicle.id,
            datetime.now() - timedelta(days=30),
            datetime.now(),
            limit=100
        )
        optimized_query_time = time.time() - start_time

        # Optimized query should be comparable or faster
        self.assertLessEqual(optimized_query_time, full_query_time * 2,
                           "Optimized query should not be significantly slower")

        # Both should return same number of results (approximately)
        self.assertEqual(len(waypoints_optimized), 100, "Should return requested limit")
        self.assertLessEqual(len(waypoints_optimized), len(waypoints_full),
                           "Optimized should not return more than full query")

    def test_concurrent_query_performance(self):
        """Test performance under concurrent load"""
        import threading
        import queue

        results = queue.Queue()
        num_threads = 5

        def worker():
            try:
                start_time = time.time()
                waypoints = QueryOptimizer.get_journey_history_optimized(
                    self.env, self.test_vehicle.id,
                    datetime.now() - timedelta(days=7),
                    datetime.now(),
                    limit=200
                )
                query_time = time.time() - start_time
                results.put({'success': True, 'time': query_time, 'count': len(waypoints)})
            except Exception as e:
                results.put({'success': False, 'error': str(e)})

        # Start concurrent queries
        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)

        # Check results
        self.assertEqual(results.qsize(), num_threads, "All threads should complete")

        successful_queries = 0
        total_time = 0
        while not results.empty():
            result = results.get()
            if result['success']:
                successful_queries += 1
                total_time += result['time']
                self.assertLess(result['time'], 2.0, "Each query should complete within 2 seconds")

        self.assertEqual(successful_queries, num_threads, "All queries should succeed")
        avg_time = total_time / successful_queries
        self.assertLess(avg_time, 1.5, "Average query time should be reasonable under load")

    def tearDown(self):
        """Clean up test data"""
        # Clean up test journey data
        self.journey_model.search([
            ('vehicle_id', '=', self.test_vehicle.id)
        ]).unlink()

        # Clean up test vehicle
        self.test_vehicle.unlink()

        super().tearDown()