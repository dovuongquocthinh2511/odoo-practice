# -*- coding: utf-8 -*-

from unittest.mock import patch, MagicMock
from odoo.tests import TransactionCase
from odoo import fields
from psycopg2 import IntegrityError


class TestFleetAddressHistory(TransactionCase):
    """Test suite for bm.fleet.address.history model"""

    def setUp(self):
        super(TestFleetAddressHistory, self).setUp()
        self.AddressHistory = self.env['bm.fleet.address.history']
        self.Company = self.env['res.company']

        # Create test company
        self.test_company = self.Company.create({
            'name': 'Test Company for Addresses'
        })

        # Clear any existing address history
        self.AddressHistory.search([]).unlink()

    def test_01_address_creation(self):
        """Test basic address record creation with usage_count"""
        address = self.AddressHistory.create({
            'name': '123 Nguyen Hue, District 1, HCMC',
            'latitude': 10.762622,
            'longitude': 106.660172,
            'usage_count': 1,
            'company_id': self.env.company.id
        })

        self.assertTrue(address)
        self.assertEqual(address.name, '123 Nguyen Hue, District 1, HCMC')
        self.assertEqual(address.latitude, 10.762622)
        self.assertEqual(address.longitude, 106.660172)
        self.assertEqual(address.usage_count, 1)
        self.assertTrue(address.last_used_date)
        self.assertTrue(address.active)

    def test_02_record_address_usage_new(self):
        """Test record_address_usage() creates new record"""
        address_data = {
            'name': 'Tan Son Nhat Airport, HCMC',
            'latitude': 10.818,
            'longitude': 106.659
        }

        result = self.AddressHistory.record_address_usage(address_data)

        self.assertTrue(result)
        self.assertEqual(result.name, 'Tan Son Nhat Airport, HCMC')
        self.assertEqual(result.usage_count, 1)
        self.assertEqual(result.latitude, 10.818)
        self.assertEqual(result.longitude, 106.659)

    def test_03_record_address_usage_existing(self):
        """Test record_address_usage() increments usage_count for existing address"""
        # Create initial address
        address_data = {
            'name': 'Ben Thanh Market, HCMC',
            'latitude': 10.772,
            'longitude': 106.698
        }

        # First usage
        first_result = self.AddressHistory.record_address_usage(address_data)
        self.assertEqual(first_result.usage_count, 1)

        # Second usage - should increment count
        second_result = self.AddressHistory.record_address_usage(address_data)

        # Should return same record
        self.assertEqual(first_result.id, second_result.id)
        self.assertEqual(second_result.usage_count, 2)

        # Third usage
        third_result = self.AddressHistory.record_address_usage(address_data)
        self.assertEqual(third_result.usage_count, 3)

    def test_04_record_address_usage_updates_coordinates(self):
        """Test that record_address_usage() updates coordinates if changed"""
        address_data = {
            'name': 'Landmark 81, HCMC',
            'latitude': 10.794,
            'longitude': 106.721
        }

        # First usage
        first = self.AddressHistory.record_address_usage(address_data)
        self.assertEqual(first.latitude, 10.794)
        self.assertEqual(first.longitude, 106.721)

        # Second usage with updated coordinates
        address_data['latitude'] = 10.795  # Updated
        address_data['longitude'] = 106.722  # Updated

        second = self.AddressHistory.record_address_usage(address_data)

        # Same record, updated coordinates
        self.assertEqual(first.id, second.id)
        self.assertEqual(second.latitude, 10.795)
        self.assertEqual(second.longitude, 106.722)
        self.assertEqual(second.usage_count, 2)

    def test_05_sql_constraint_unique_address_per_company(self):
        """Test SQL constraint prevents duplicate addresses per company"""
        # Create address for company
        self.AddressHistory.create({
            'name': 'Notre Dame Cathedral, HCMC',
            'company_id': self.env.company.id
        })

        # Try to create duplicate - should fail
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self.AddressHistory.create({
                    'name': 'Notre Dame Cathedral, HCMC',
                    'company_id': self.env.company.id
                })

    def test_06_search_address_suggestions(self):
        """Test search_address_suggestions with usage-based sorting"""
        # Create test addresses with different usage counts
        self.AddressHistory.create({
            'name': 'Ho Chi Minh City Hall',
            'usage_count': 5,
            'company_id': self.env.company.id
        })

        self.AddressHistory.create({
            'name': 'Ho Chi Minh City Museum',
            'usage_count': 10,
            'company_id': self.env.company.id
        })

        self.AddressHistory.create({
            'name': 'Ho Chi Minh City Opera House',
            'usage_count': 3,
            'company_id': self.env.company.id
        })

        # Search for "Ho Chi Minh"
        results = self.AddressHistory.search_address_suggestions('Ho Chi Minh', limit=10)

        # Should return 3 results
        self.assertEqual(len(results), 3)

        # Should be sorted by usage_count desc
        self.assertEqual(results[0]['name'], 'Ho Chi Minh City Museum')  # usage_count=10
        self.assertEqual(results[0]['usage_count'], 10)
        self.assertEqual(results[1]['name'], 'Ho Chi Minh City Hall')  # usage_count=5
        self.assertEqual(results[2]['name'], 'Ho Chi Minh City Opera House')  # usage_count=3

    def test_07_search_address_suggestions_query_validation(self):
        """Test search_address_suggestions query validation"""
        # Create test address
        self.AddressHistory.create({
            'name': 'District 1, HCMC',
            'company_id': self.env.company.id
        })

        # Empty query should return empty list
        self.assertEqual(self.AddressHistory.search_address_suggestions(''), [])

        # Query too short (< 2 chars) should return empty list
        self.assertEqual(self.AddressHistory.search_address_suggestions('D'), [])

        # Valid query should return results
        results = self.AddressHistory.search_address_suggestions('District')
        self.assertTrue(len(results) > 0)

    def test_08_company_isolation(self):
        """Test that addresses are isolated per company"""
        # Create address for default company
        address1 = self.AddressHistory.create({
            'name': 'Company A Office',
            'company_id': self.env.company.id
        })

        # Create address for test company
        address2 = self.AddressHistory.with_company(self.test_company).create({
            'name': 'Company B Office',
            'company_id': self.test_company.id
        })

        # Search from default company should not see test company addresses
        results = self.AddressHistory.search_address_suggestions('Company')
        company_a_found = any(r['name'] == 'Company A Office' for r in results)
        company_b_found = any(r['name'] == 'Company B Office' for r in results)

        self.assertTrue(company_a_found)
        self.assertFalse(company_b_found)

        # Search from test company should not see default company addresses
        results_test = self.AddressHistory.with_company(self.test_company).search_address_suggestions('Company')
        company_a_found_test = any(r['name'] == 'Company A Office' for r in results_test)
        company_b_found_test = any(r['name'] == 'Company B Office' for r in results_test)

        self.assertFalse(company_a_found_test)
        self.assertTrue(company_b_found_test)

    def test_09_record_address_usage_empty_name(self):
        """Test record_address_usage returns empty recordset for empty name"""
        result = self.AddressHistory.record_address_usage({'name': ''})
        self.assertFalse(result)

        result = self.AddressHistory.record_address_usage({})
        self.assertFalse(result)

    def test_10_search_suggestions_respects_active_flag(self):
        """Test search suggestions only returns active addresses"""
        # Create active address
        self.AddressHistory.create({
            'name': 'Active Location HCMC',
            'active': True,
            'company_id': self.env.company.id
        })

        # Create inactive address
        self.AddressHistory.create({
            'name': 'Inactive Location HCMC',
            'active': False,
            'company_id': self.env.company.id
        })

        # Search should only return active
        results = self.AddressHistory.search_address_suggestions('Location HCMC')

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], 'Active Location HCMC')

    @patch('requests.get')
    def test_11_search_openmap_autocomplete_success(self, mock_get):
        """Test OpenMap autocomplete API integration"""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'features': [
                {
                    'properties': {
                        'id': 'place_123',
                        'name': 'Ben Thanh Market',
                        'label': 'Ben Thanh Market, District 1, HCMC'
                    }
                },
                {
                    'properties': {
                        'id': 'place_456',
                        'name': 'Notre Dame',
                        'label': 'Notre Dame Cathedral, District 1, HCMC'
                    }
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # Set up API key
        self.env['ir.config_parameter'].sudo().set_param('openmap.api.key', 'test-api-key')

        # Call autocomplete
        results = self.AddressHistory.search_openmap_autocomplete('Ben Thanh', limit=5)

        # Verify results
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['id'], 'place_123')
        self.assertEqual(results[0]['display_name'], 'Ben Thanh Market, District 1, HCMC')
        self.assertEqual(results[0]['source'], 'openmap')

        # Verify API was called with correct params
        call_args = mock_get.call_args
        self.assertEqual(call_args[1]['params']['apikey'], 'test-api-key')
        self.assertEqual(call_args[1]['params']['text'], 'Ben Thanh')
        self.assertEqual(call_args[1]['params']['limit'], 5)

    @patch('requests.get')
    def test_12_search_openmap_autocomplete_no_api_key(self, mock_get):
        """Test OpenMap autocomplete returns empty when API key missing"""
        # Clear API key
        self.env['ir.config_parameter'].sudo().set_param('openmap.api.key', False)

        results = self.AddressHistory.search_openmap_autocomplete('Test Query')

        # Should return empty list
        self.assertEqual(results, [])

        # Should not call API
        mock_get.assert_not_called()

    @patch('requests.get')
    def test_13_get_openmap_place_detail_success(self, mock_get):
        """Test fetching place details from OpenMap"""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'result': {
                'formatted_address': 'Ben Thanh Market, District 1, HCMC',
                'geometry': {
                    'location': {
                        'lat': 10.772461,
                        'lng': 106.698055
                    }
                }
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # Set up API key
        self.env['ir.config_parameter'].sudo().set_param('openmap.api.key', 'test-api-key')

        # Get place detail
        result = self.AddressHistory.get_openmap_place_detail('place_123')

        # Verify result
        self.assertTrue(result)
        self.assertEqual(result['display_name'], 'Ben Thanh Market, District 1, HCMC')
        self.assertEqual(result['latitude'], 10.772461)
        self.assertEqual(result['longitude'], 106.698055)
        self.assertEqual(result['source'], 'openmap')

        # Verify API was called correctly
        call_args = mock_get.call_args
        self.assertEqual(call_args[1]['params']['apikey'], 'test-api-key')
        self.assertEqual(call_args[1]['params']['ids'], 'place_123')

    @patch('requests.get')
    def test_14_openmap_api_error_handling(self, mock_get):
        """Test OpenMap API error handling"""
        # Mock API error
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

        # Set up API key
        self.env['ir.config_parameter'].sudo().set_param('openmap.api.key', 'test-api-key')

        # Autocomplete should return empty list on error
        results = self.AddressHistory.search_openmap_autocomplete('Test')
        self.assertEqual(results, [])

        # Place detail should return False on error
        result = self.AddressHistory.get_openmap_place_detail('place_123')
        self.assertFalse(result)
