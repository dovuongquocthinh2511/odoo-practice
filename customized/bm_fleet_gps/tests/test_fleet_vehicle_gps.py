# -*- coding: utf-8 -*-

from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from odoo.tests import TransactionCase
from odoo import fields


class TestFleetVehicleGPS(TransactionCase):
    """Test suite for fleet.vehicle GPS integration"""

    def setUp(self):
        super(TestFleetVehicleGPS, self).setUp()
        self.vehicle_model = self.env['fleet.vehicle']
        self.route_model = self.env['fleet.gps.route']
        self.location_model = self.env['fleet.gps.location']
        self.token_model = self.env['bm.fleet.adsun.token']

        # Create test vehicle with GPS device
        self.vehicle = self.vehicle_model.create({
            'name': 'Test Vehicle GPS',
            'license_plate': 'GPS-TEST-001',
            'adsun_device_serial_number': '123456789',
            'gps_company_id': 1136
        })

    def test_01_gps_linked_computation(self):
        """Test GPS linked status is computed correctly"""
        # Vehicle with serial should be linked
        self.assertTrue(self.vehicle.gps_linked)

        # Vehicle without serial should not be linked
        vehicle_no_gps = self.vehicle_model.create({
            'name': 'No GPS Vehicle',
            'license_plate': 'NO-GPS-001'
        })
        self.assertFalse(vehicle_no_gps.gps_linked)

    @patch('requests.get')
    def test_02_reverse_geocoding(self, mock_get):
        """Test reverse geocoding from coordinates"""
        # Mock Nominatim API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'display_name': '123 Test Street, Ho Chi Minh City, Vietnam'
        }
        mock_get.return_value = mock_response

        # Update coordinates
        self.vehicle.write({
            'current_latitude': 10.762622,
            'current_longitude': 106.660172
        })

        # Compute address
        self.vehicle._compute_current_address()
        self.assertEqual(self.vehicle.current_address, '123 Test Street, Ho Chi Minh City, Vietnam')

    def test_03_running_time_today_computation(self):
        """Test running time today is computed correctly"""
        today = fields.Date.today()

        # Create today's route with 3 hours running time
        route = self.route_model.create({
            'vehicle_id': self.vehicle.id,
            'route_date': today,
            'total_running_time': 3.0
        })

        # Refresh and check
        self.vehicle.refresh()
        self.assertEqual(self.vehicle.running_time_today, 3.0)

    def test_04_running_time_week_computation(self):
        """Test running time this week is computed correctly"""
        today = fields.Date.today()

        # Create routes for this week
        self.route_model.create({
            'vehicle_id': self.vehicle.id,
            'route_date': today,
            'total_running_time': 2.0
        })

        self.route_model.create({
            'vehicle_id': self.vehicle.id,
            'route_date': today - timedelta(days=1),
            'total_running_time': 3.5
        })

        # Refresh and check (should sum to 5.5)
        self.vehicle.refresh()
        self.assertEqual(self.vehicle.running_time_week, 5.5)

    def test_05_last_stop_time_computation(self):
        """Test last stop time is computed from last engine off location"""
        today = fields.Date.today()
        route = self.route_model.create({
            'vehicle_id': self.vehicle.id,
            'route_date': today
        })

        stop_time = datetime.now() - timedelta(hours=2)

        # Create location with engine OFF
        self.location_model.create({
            'route_id': route.id,
            'latitude': 10.0,
            'longitude': 107.0,
            'timestamp': stop_time,
            'machine_status': False  # Engine OFF
        })

        # Refresh and check
        self.vehicle.refresh()
        self.assertEqual(self.vehicle.last_stop_time, stop_time)

    @patch('requests.get')
    def test_06_call_get_device_trip_api_success(self, mock_get):
        """Test successful GetDeviceTripBySerial API call"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'DeviceTripList': [
                {
                    'Latitude': 10.762622,
                    'Longitude': 106.660172,
                    'Speed': 45,
                    'MachineStatus': True,
                    'GpsStatus': True,
                    'Time': '10:30:00 02/10/2025'
                }
            ],
            'Status': 1
        }
        mock_get.return_value = mock_response

        # Call API
        begin_time = datetime.now() - timedelta(minutes=5)
        end_time = datetime.now()

        with patch.object(self.token_model, 'get_active_token', return_value='test-token'):
            result = self.vehicle._call_get_device_trip_api(1136, '123456789', begin_time, end_time, 'test-token')

        self.assertEqual(result['Status'], 1)
        self.assertTrue(len(result['DeviceTripList']) > 0)

    def test_07_process_trip_waypoints(self):
        """Test GPS trip waypoints processing"""
        api_data = {
            'DeviceTripList': [
                {
                    'Latitude': 10.762622,
                    'Longitude': 106.660172,
                    'Speed': 45,
                    'MachineStatus': True,
                    'GpsStatus': True,
                    'Time': '10:30:00 02/10/2025',
                    'TotalDistance': 150.5
                }
            ],
            'Status': 1
        }

        today = fields.Date.today()
        route = self.route_model.create({
            'vehicle_id': self.vehicle.id,
            'route_date': today
        })

        # Process response
        self.vehicle._process_trip_waypoints(vehicle=self.vehicle, trip_list=api_data['DeviceTripList'])

        # Verify location created
        locations = self.location_model.search([('route_id', '=', route.id)])
        self.assertEqual(len(locations), 1)
        self.assertEqual(locations[0].latitude, 10.762622)
        self.assertEqual(locations[0].longitude, 106.660172)
        self.assertEqual(locations[0].speed, 45)

        # Verify vehicle updated
        self.assertEqual(self.vehicle.current_latitude, 10.762622)
        self.assertEqual(self.vehicle.current_longitude, 106.660172)
        self.assertTrue(self.vehicle.machine_status)

    @patch.object(TransactionCase.env['fleet.vehicle'], '_sync_vehicle_gps_data')
    def test_08_cron_sync_all_vehicles(self, mock_sync):
        """Test cron job syncs all GPS-enabled vehicles"""
        # Create another GPS vehicle
        vehicle2 = self.vehicle_model.create({
            'name': 'Test Vehicle 2',
            'license_plate': 'GPS-TEST-002',
            'adsun_device_serial_number': '987654321'
        })

        with patch.object(self.token_model, 'get_active_token', return_value='test-token'):
            self.vehicle_model.cron_sync_gps_data()

        # Should sync both vehicles
        self.assertEqual(mock_sync.call_count, 2)

    def test_09_action_sync_gps_now(self):
        """Test manual GPS sync action"""
        with patch.object(self.vehicle, '_sync_vehicle_gps_data') as mock_sync:
            with patch.object(self.token_model, 'get_active_token', return_value='test-token'):
                result = self.vehicle.action_sync_gps_now()

        # Should call sync method
        mock_sync.assert_called_once()

        # Should return success notification
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['tag'], 'display_notification')

    def test_10_action_view_routes(self):
        """Test view routes action"""
        # Create some routes
        for i in range(3):
            self.route_model.create({
                'vehicle_id': self.vehicle.id,
                'route_date': fields.Date.today() - timedelta(days=i)
            })

        action = self.vehicle.action_view_routes()

        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'fleet.gps.route')
        self.assertIn(('vehicle_id', '=', self.vehicle.id), action['domain'])
