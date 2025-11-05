# -*- coding: utf-8 -*-
"""
Performance Test for Daily Distance Calculation

This module tests the performance difference between individual calculations
and read_group-based aggregation for daily distance computation.
"""

import logging
import time
from datetime import datetime, timedelta
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)


class DailyDistancePerformanceTest:
    """Test class to compare performance of daily distance calculation methods"""

    def __init__(self, env):
        self.env = env
        self.Journey = env['bm.fleet.transportation.journey']

    def _create_test_data(self, num_days=30, vehicles_per_day=5, waypoints_per_vehicle=20):
        """Create test data for performance testing

        Args:
            num_days (int): Number of days to create data for
            vehicles_per_day (int): Number of vehicles to create per day
            waypoints_per_vehicle (int): Number of waypoints per vehicle per day

        Returns:
            tuple: (vehicle_ids, total_records_created)
        """
        _logger.info(f"Creating test data: {num_days} days, {vehicles_per_day} vehicles/day, {waypoints_per_vehicle} waypoints/vehicle")

        Vehicle = self.env['fleet.vehicle']
        vehicles = []

        # Create test vehicles
        for i in range(vehicles_per_day):
            vehicle = Vehicle.create({
                'name': f'Test Vehicle {i+1}',
                'license_plate': f'TEST{i+1:03d}',
                'adsun_device_serial_number': f'TEST_DEVICE_{i+1:06d}'
            })
            vehicles.append(vehicle)

        # Create waypoints for each day and vehicle
        total_records = 0
        base_date = datetime.now() - timedelta(days=num_days)

        for day_offset in range(num_days):
            current_date = base_date + timedelta(days=day_offset)

            for vehicle in vehicles:
                # Create waypoints for this vehicle on this day
                for waypoint_offset in range(waypoints_per_vehicle):
                    timestamp = current_date.replace(
                        hour=8 + waypoint_offset,
                        minute=waypoint_offset * 3,
                        second=0
                    )

                    # Simulate GPS coordinates (Ho Chi Minh City area)
                    latitude = 10.7769 + (waypoint_offset * 0.001)
                    longitude = 106.7009 + (waypoint_offset * 0.001)

                    # Calculate distance (simulate incremental distance)
                    distance = (waypoint_offset + 1) * 2.5  # 2.5km between waypoints

                    journey = self.Journey.create({
                        'vehicle_id': vehicle.id,
                        'timestamp': timestamp,
                        'latitude': latitude,
                        'longitude': longitude,
                        'distance': distance,
                        'speed': 40.0 + (waypoint_offset * 2),
                        'machine_status': True,
                        'gps_status': True,
                        'address': f'Test Address {waypoint_offset + 1}',
                        'is_address_synced': True,
                        'api_data': f'{{"TotalDistance": {distance * 1000}}}'
                    })
                    total_records += 1

        _logger.info(f"Created {total_records} test waypoints across {len(vehicles)} vehicles")
        return vehicles, total_records

    def test_individual_calculation(self, date_from, date_to):
        """Test individual distance calculation (old method)

        Args:
            date_from (datetime.date): Start date
            date_to (datetime.date): End date

        Returns:
            tuple: (total_distance, execution_time)
        """
        _logger.info("Testing individual calculation method...")
        start_time = time.time()

        total_distance = 0.0
        current_date = date_from

        while current_date <= date_to:
            # Individual calculation for each day
            journeys = self.Journey.search([
                ('timestamp', '>=', current_date),
                ('timestamp', '<', current_date + timedelta(days=1))
            ])

            day_total = sum(journey.distance for journey in journeys)
            total_distance += day_total

            current_date += timedelta(days=1)

        execution_time = time.time() - start_time
        _logger.info(f"Individual method: Total distance = {total_distance:.2f} km, Time = {execution_time:.3f}s")

        return total_distance, execution_time

    def test_read_group_calculation(self, date_from, date_to):
        """Test read_group distance calculation (new optimized method)

        Args:
            date_from (datetime.date): Start date
            date_to (datetime.date): End date

        Returns:
            tuple: (total_distance, execution_time)
        """
        _logger.info("Testing read_group calculation method...")
        start_time = time.time()

        # Use the optimized read_group method
        from datetime import datetime
        date_start = datetime.combine(date_from, datetime.min.time())
        date_end = datetime.combine(date_to, datetime.max.time())

        aggregated_data = self.Journey.read_group(
            domain=[('timestamp', '>=', date_start), ('timestamp', '<=', date_end)],
            fields=['distance:sum'],
            groupby=['timestamp:day'],
            lazy=False
        )

        total_distance = sum(group['distance'] for group in aggregated_data)
        execution_time = time.time() - start_time

        _logger.info(f"Read_group method: Total distance = {total_distance:.2f} km, Time = {execution_time:.3f}s")

        return total_distance, execution_time

    def test_vehicle_specific_methods(self, vehicle_id, date_from, date_to):
        """Test vehicle-specific optimized methods

        Args:
            vehicle_id (int): Vehicle ID to test
            date_from (datetime.date): Start date
            date_to (datetime.date): End date

        Returns:
            dict: Performance results for different vehicle methods
        """
        vehicle = self.env['fleet.vehicle'].browse(vehicle_id)
        _logger.info(f"Testing vehicle-specific methods for {vehicle.name}...")

        results = {}

        # Test daily distance method
        start_time = time.time()
        daily_total = vehicle.get_daily_distance_optimized(date_from)
        daily_time = time.time() - start_time
        results['daily_distance'] = {'value': daily_total, 'time': daily_time}

        # Test weekly summary method
        start_time = time.time()
        weekly_summary = vehicle.get_weekly_distance_summary(date_from)
        weekly_time = time.time() - start_time
        results['weekly_summary'] = {'records': len(weekly_summary), 'time': weekly_time}

        # Test statistics method
        start_time = time.time()
        stats = vehicle.get_distance_statistics(30)
        stats_time = time.time() - start_time
        results['statistics'] = {'stats': stats, 'time': stats_time}

        _logger.info(f"Vehicle methods completed: Daily={daily_time:.3f}s, Weekly={weekly_time:.3f}s, Stats={stats_time:.3f}s")

        return results

    def run_performance_comparison(self, test_days=30):
        """Run comprehensive performance comparison

        Args:
            test_days (int): Number of days to include in test

        Returns:
            dict: Complete performance comparison results
        """
        _logger.info(f"Starting performance comparison for {test_days} days...")

        # Clean up any existing test data
        self._cleanup_test_data()

        # Create test data
        vehicles, total_records = self._create_test_data(
            num_days=test_days,
            vehicles_per_day=3,
            waypoints_per_vehicle=15
        )

        # Define test date range
        date_from = (datetime.now() - timedelta(days=test_days)).date()
        date_to = datetime.now().date()

        # Test individual calculation
        individual_distance, individual_time = self.test_individual_calculation(date_from, date_to)

        # Test read_group calculation
        readgroup_distance, readgroup_time = self.test_read_group_calculation(date_from, date_to)

        # Test vehicle-specific methods
        vehicle_results = {}
        for vehicle in vehicles[:2]:  # Test first 2 vehicles
            vehicle_results[vehicle.id] = self.test_vehicle_specific_methods(
                vehicle.id, date_from, date_to
            )

        # Calculate performance improvements
        improvement_ratio = individual_time / readgroup_time if readgroup_time > 0 else 0

        results = {
            'test_parameters': {
                'days': test_days,
                'vehicles': len(vehicles),
                'total_records': total_records
            },
            'individual_method': {
                'distance': individual_distance,
                'time': individual_time
            },
            'readgroup_method': {
                'distance': readgroup_distance,
                'time': readgroup_time
            },
            'performance_improvement': {
                'speed_ratio': improvement_ratio,
                'time_saved': individual_time - readgroup_time,
                'percentage_improvement': ((individual_time - readgroup_time) / individual_time * 100) if individual_time > 0 else 0
            },
            'vehicle_methods': vehicle_results,
            'accuracy_check': {
                'distances_match': abs(individual_distance - readgroup_distance) < 0.01,
                'difference': abs(individual_distance - readgroup_distance)
            }
        }

        # Log summary
        _logger.info("=== PERFORMANCE COMPARISON SUMMARY ===")
        _logger.info(f"Records processed: {total_records}")
        _logger.info(f"Individual method: {individual_time:.3f}s")
        _logger.info(f"Read_group method: {readgroup_time:.3f}s")
        _logger.info(f"Performance improvement: {improvement_ratio:.1f}x faster")
        _logger.info(f"Time saved: {results['performance_improvement']['time_saved']:.3f}s")
        _logger.info(f"Accuracy check: {'PASSED' if results['accuracy_check']['distances_match'] else 'FAILED'}")

        return results

    def _cleanup_test_data(self):
        """Clean up test data"""
        _logger.info("Cleaning up existing test data...")

        # Remove test vehicles
        test_vehicles = self.env['fleet.vehicle'].search([
            ('name', 'like', 'Test Vehicle %')
        ])
        if test_vehicles:
            # This will also cascade delete journey records
            test_vehicles.unlink()
            _logger.info(f"Removed {len(test_vehicles)} test vehicles")

  def run_performance_test(env, test_days=30):
        """Standalone function to run performance test

        Args:
            env: Odoo environment
            test_days (int): Number of days for test data

        Returns:
            dict: Performance test results
        """
        try:
            test_instance = DailyDistancePerformanceTest(env)
            return test_instance.run_performance_comparison(test_days)
        except Exception as e:
            _logger.error(f"Performance test failed: {e}")
            return {
                'error': str(e),
                'test_parameters': {'days': test_days}
            }


class TestDailyDistancePerformance(TransactionCase):
    """Odoo test case for daily distance calculation performance"""

    def test_daily_distance_performance_comparison(self):
        """Test performance difference between individual and read_group methods"""
        _logger.info("Running daily distance performance test...")

        # Create test instance
        test_instance = DailyDistancePerformanceTest(self.env)

        # Run performance comparison with smaller dataset for testing
        results = test_instance.run_performance_comparison(test_days=7)

        # Verify results
        self.assertIsNotNone(results, "Performance test should return results")
        self.assertIn('performance_improvement', results, "Should contain performance metrics")
        self.assertIn('accuracy_check', results, "Should contain accuracy verification")

        # Verify accuracy
        self.assertTrue(
            results['accuracy_check']['distances_match'],
            f"Distance calculations should match. Difference: {results['accuracy_check']['difference']}"
        )

        # Verify performance improvement
        improvement = results['performance_improvement']['speed_ratio']
        self.assertGreater(
            improvement, 1.0,
            f"Read_group method should be faster. Speed ratio: {improvement:.1f}x"
        )

        _logger.info(f"Performance test completed successfully. Improvement: {improvement:.1f}x faster")

    def test_vehicle_daily_distance_methods(self):
        """Test vehicle-specific daily distance methods"""
        _logger.info("Testing vehicle-specific methods...")

        # Create a test vehicle
        test_vehicle = self.env['fleet.vehicle'].create({
            'name': 'Performance Test Vehicle',
            'license_plate': 'PERF001',
            'adsun_device_serial_number': 'PERF_DEVICE_001'
        })

        # Create some test journey data
        Journey = self.env['bm.fleet.transportation.journey']
        test_date = datetime.now().date()

        for i in range(10):
            Journey.create({
                'vehicle_id': test_vehicle.id,
                'timestamp': datetime.combine(test_date, datetime.min.time()).replace(hour=8+i),
                'latitude': 10.7769 + (i * 0.001),
                'longitude': 106.7009 + (i * 0.001),
                'distance': (i + 1) * 2.5,
                'speed': 40.0,
                'machine_status': True,
                'gps_status': True,
                'address': f'Test Address {i+1}',
                'is_address_synced': True,
                'api_data': f'{{"TotalDistance": {(i+1) * 2500}}}'
            })

        # Test daily distance method
        daily_distance = test_vehicle.get_daily_distance_optimized(test_date)
        self.assertIsInstance(daily_distance, float, "Daily distance should be a float")
        self.assertGreater(daily_distance, 0, "Daily distance should be greater than 0")

        # Test statistics method
        stats = test_vehicle.get_distance_statistics(7)
        self.assertIsInstance(stats, dict, "Statistics should be a dictionary")
        self.assertIn('total_distance', stats, "Stats should contain total distance")
        self.assertIn('daily_average', stats, "Stats should contain daily average")

        _logger.info(f"Vehicle methods test passed. Daily distance: {daily_distance:.2f} km")

    def test_group_by_aggregation_methods(self):
        """Test the group by aggregation methods at model level"""
        _logger.info("Testing group by aggregation methods...")

        Journey = self.env['bm.fleet.transportation.journey']

        # Test the model-level methods
        test_date = datetime.now().date()

        # Create test data for multiple vehicles
        vehicles = []
        for i in range(3):
            vehicle = self.env['fleet.vehicle'].create({
                'name': f'Test Vehicle {i+1}',
                'license_plate': f'TEST{i+1:03d}',
                'adsun_device_serial_number': f'TEST_DEVICE_{i+1:06d}'
            })
            vehicles.append(vehicle)

        # Create journey records
        for vehicle in vehicles:
            for i in range(5):
                Journey.create({
                    'vehicle_id': vehicle.id,
                    'timestamp': datetime.combine(test_date, datetime.min.time()).replace(hour=10+i),
                    'latitude': 10.7769 + (i * 0.001),
                    'longitude': 106.7009 + (i * 0.001),
                    'distance': (i + 1) * 1.5,
                    'speed': 35.0,
                    'machine_status': True,
                    'gps_status': True,
                    'address': f'Test Address {i+1}',
                    'is_address_synced': True,
                    'api_data': f'{{"TotalDistance": {(i+1) * 1500}}}'
                })

        # Test daily distance by date
        daily_total = Journey.get_daily_distance_by_date(test_date)
        self.assertIsInstance(daily_total, float, "Daily total should be a float")
        self.assertGreater(daily_total, 0, "Daily total should be greater than 0")

        # Test daily distance by vehicle and date
        vehicle_distances = Journey.get_daily_distance_by_vehicle_date(test_date)
        self.assertIsInstance(vehicle_distances, dict, "Vehicle distances should be a dictionary")
        self.assertEqual(len(vehicle_distances), 3, "Should have distances for 3 vehicles")

        # Test daily summary
        summary = Journey.get_daily_distance_summary(test_date, test_date)
        self.assertIsInstance(summary, list, "Summary should be a list")
        self.assertEqual(len(summary), 1, "Should have 1 day in summary")

        _logger.info(f"Group by aggregation test passed. Daily total: {daily_total:.2f} km")