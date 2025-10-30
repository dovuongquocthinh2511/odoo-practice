# -*- coding: utf-8 -*-

from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from odoo.tests import TransactionCase
from odoo import fields


class TestFleetTransportationJourney(TransactionCase):
    """Test suite for fleet.transportation.journey model"""

    def setUp(self):
        super(TestFleetTransportationJourney, self).setUp()
        self.Journey = self.env['bm.fleet.transportation.journey']
        self.Vehicle = self.env['fleet.vehicle']

        # Create test vehicle
        self.vehicle = self.Vehicle.create({
            'name': 'Test Vehicle Journey',
            'license_plate': 'JOURNEY-001',
            'adsun_device_serial_number': '123456789',
            'gps_company_id': 1136
        })

    def test_01_journey_creation(self):
        """Test basic journey waypoint creation"""
        journey = self.Journey.create({
            'vehicle_id': self.vehicle.id,
            'timestamp': fields.Datetime.now(),
            'latitude': 10.762622,
            'longitude': 106.660172,
            'speed': 45,
            'machine_status': True,
            'gps_status': True,
            'total_distance': 15.5
        })

        self.assertTrue(journey)
        self.assertEqual(journey.vehicle_id, self.vehicle)
        self.assertEqual(journey.latitude, 10.762622)
        self.assertEqual(journey.speed, 45)

    def test_02_display_name_computation(self):
        """Test display name is computed correctly"""
        timestamp = fields.Datetime.now()
        journey = self.Journey.create({
            'vehicle_id': self.vehicle.id,
            'timestamp': timestamp,
            'latitude': 10.0,
            'longitude': 107.0
        })

        expected_name = f"{self.vehicle.name} - {timestamp}"
        self.assertEqual(journey.display_name, expected_name)

    def test_03_unique_vehicle_timestamp_constraint(self):
        """Test SQL constraint prevents duplicate waypoints"""
        timestamp = fields.Datetime.now()

        # Create first journey
        self.Journey.create({
            'vehicle_id': self.vehicle.id,
            'timestamp': timestamp,
            'latitude': 10.0,
            'longitude': 107.0
        })

        # Try to create duplicate - should raise constraint error
        with self.assertRaises(Exception):
            self.Journey.create({
                'vehicle_id': self.vehicle.id,
                'timestamp': timestamp,  # Same timestamp
                'latitude': 11.0,
                'longitude': 108.0
            })

    @patch.object(TransactionCase.env['bm.fleet.transportation.journey'], 'geocode_coordinates')
    def test_04_address_geocoding(self, mock_geocode):
        """Test address is geocoded from coordinates"""
        mock_geocode.return_value = '123 Test Street, Ho Chi Minh City'

        journey = self.Journey.create({
            'vehicle_id': self.vehicle.id,
            'timestamp': fields.Datetime.now(),
            'latitude': 10.762622,
            'longitude': 106.660172
        })

        # Trigger geocoding
        journey.fetch_address_from_geocode()

        self.assertEqual(journey.address, '123 Test Street, Ho Chi Minh City')
        mock_geocode.assert_called_once()

    @patch.object(TransactionCase.env['bm.fleet.transportation.journey'], 'geocode_coordinates')
    def test_06_batch_fetch_missing_addresses(self, mock_geocode):
        """Test batch address fetching for waypoints with null addresses"""
        mock_geocode.side_effect = [
            'Address 1',
            'Address 2',
            None,  # Failed geocoding
        ]

        # Create waypoints without addresses
        journey1 = self.Journey.create({
            'vehicle_id': self.vehicle.id,
            'timestamp': fields.Datetime.now(),
            'latitude': 10.0,
            'longitude': 106.0
        })

        journey2 = self.Journey.create({
            'vehicle_id': self.vehicle.id,
            'timestamp': fields.Datetime.now() + timedelta(minutes=1),
            'latitude': 10.1,
            'longitude': 106.1
        })

        journey3 = self.Journey.create({
            'vehicle_id': self.vehicle.id,
            'timestamp': fields.Datetime.now() + timedelta(minutes=2),
            'latitude': 10.2,
            'longitude': 106.2
        })

        # Batch fetch addresses
        result = self.Journey.fetch_missing_addresses(limit=10)

        self.assertEqual(result['processed'], 3)
        self.assertEqual(result['success'], 2)
        self.assertEqual(result['failed'], 1)

        # Verify addresses were set
        journey1.refresh()
        journey2.refresh()
        journey3.refresh()

        self.assertEqual(journey1.address, 'Address 1')
        self.assertEqual(journey2.address, 'Address 2')
        self.assertFalse(journey3.address)

    def test_07_cron_fetch_missing_addresses(self):
        """Test cron job for fetching missing addresses"""
        # Create waypoint without address
        self.Journey.create({
            'vehicle_id': self.vehicle.id,
            'timestamp': fields.Datetime.now(),
            'latitude': 10.0,
            'longitude': 106.0
        })

        with patch.object(self.Journey, 'fetch_missing_addresses') as mock_fetch:
            mock_fetch.return_value = {'processed': 1, 'success': 1, 'failed': 0}

            self.Journey.cron_fetch_missing_addresses()

            mock_fetch.assert_called_once_with(limit=100, use_openstreetmap=True)

    def test_08_action_refresh_address(self):
        """Test manual address refresh action"""
        journey = self.Journey.create({
            'vehicle_id': self.vehicle.id,
            'timestamp': fields.Datetime.now(),
            'latitude': 10.762622,
            'longitude': 106.660172
        })

        with patch.object(journey, 'fetch_address_from_geocode') as mock_fetch:
            result = journey.action_refresh_address()

            self.assertEqual(result['type'], 'ir.actions.client')
            self.assertEqual(result['tag'], 'display_notification')
            mock_fetch.assert_called_once()
