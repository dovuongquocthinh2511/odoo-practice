# -*- coding: utf-8 -*-

from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from odoo.tests import TransactionCase


class TestADSUNTokenHelper(TransactionCase):
    """Test suite for bm.fleet.adsun.token AbstractModel"""

    def setUp(self):
        super(TestADSUNTokenHelper, self).setUp()
        self.TokenHelper = self.env['bm.fleet.adsun.token']
        self.ICP = self.env['ir.config_parameter'].sudo()

        # Set up test config parameters
        self.ICP.set_param('bm_fleet_gps.auth_url', 'https://auth.adsun.vn')
        self.ICP.set_param('bm_fleet_gps.api_url', 'https://test-api.com')
        self.ICP.set_param('bm_fleet_gps.api_username', 'test_user')
        self.ICP.set_param('bm_fleet_gps.api_password', 'test_pass')
        self.ICP.set_param('bm_fleet_gps.ssl_verify', 'True')

        # Clear any existing tokens
        self.ICP.set_param('bm_fleet_gps.api_token', False)
        self.ICP.set_param('bm_fleet_gps.token_expires_at', False)

    @patch('requests.post')
    def test_01_get_active_token_no_token(self, mock_post):
        """Test get_active_token when no token exists - should request new token"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'Token': 'new-test-token-123',
            'Status': 1,
            'Description': 'OK'
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        # Get token (should request new one)
        token = self.TokenHelper.get_active_token()

        # Verify API was called
        mock_post.assert_called_once()
        self.assertEqual(token, 'new-test-token-123')

        # Verify token saved to config
        saved_token = self.ICP.get_param('bm_fleet_gps.api_token')
        self.assertEqual(saved_token, 'new-test-token-123')

        # Verify expiration time was saved
        expires_at = self.ICP.get_param('bm_fleet_gps.token_expires_at')
        self.assertTrue(expires_at)

    def test_02_get_active_token_valid_existing(self):
        """Test get_active_token with valid unexpired token - should return existing"""
        # Set up valid unexpired token
        future_expiry = (datetime.now() + timedelta(hours=1)).isoformat()
        self.ICP.set_param('bm_fleet_gps.api_token', 'existing-valid-token')
        self.ICP.set_param('bm_fleet_gps.token_expires_at', future_expiry)

        # Get token (should not request new one)
        with patch('requests.post') as mock_post:
            token = self.TokenHelper.get_active_token()

            # Verify NO API call was made
            mock_post.assert_not_called()

        # Verify returns existing token
        self.assertEqual(token, 'existing-valid-token')

    @patch('requests.post')
    def test_03_get_active_token_expired(self, mock_post):
        """Test get_active_token with expired token - should request new token"""
        # Set up expired token
        past_expiry = (datetime.now() - timedelta(hours=1)).isoformat()
        self.ICP.set_param('bm_fleet_gps.api_token', 'expired-token')
        self.ICP.set_param('bm_fleet_gps.token_expires_at', past_expiry)

        # Mock API response for new token
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'Token': 'refreshed-token-456',
            'Status': 1,
            'Description': 'OK'
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        # Get token (should request new one)
        token = self.TokenHelper.get_active_token()

        # Verify API was called
        mock_post.assert_called_once()

        # Verify new token returned and saved
        self.assertEqual(token, 'refreshed-token-456')
        saved_token = self.ICP.get_param('bm_fleet_gps.api_token')
        self.assertEqual(saved_token, 'refreshed-token-456')

    @patch('requests.post')
    def test_04_get_active_token_force_refresh(self, mock_post):
        """Test get_active_token with force_refresh=True - should always request new"""
        # Set up valid unexpired token
        future_expiry = (datetime.now() + timedelta(hours=1)).isoformat()
        self.ICP.set_param('bm_fleet_gps.api_token', 'old-but-valid-token')
        self.ICP.set_param('bm_fleet_gps.token_expires_at', future_expiry)

        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'Token': 'force-refreshed-token-789',
            'Status': 1,
            'Description': 'OK'
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        # Get token with force refresh
        token = self.TokenHelper.get_active_token(force_refresh=True)

        # Verify API was called even though token was valid
        mock_post.assert_called_once()

        # Verify new token returned
        self.assertEqual(token, 'force-refreshed-token-789')

    @patch('requests.post')
    def test_05_request_new_token_success(self, mock_post):
        """Test successful token request from API"""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'Token': 'api-token-xyz',
            'Status': 1,
            'Description': 'OK'
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        # Request new token
        token = self.TokenHelper._request_new_token()

        # Verify token returned
        self.assertEqual(token, 'api-token-xyz')

        # Verify token saved to config
        saved_token = self.ICP.get_param('bm_fleet_gps.api_token')
        self.assertEqual(saved_token, 'api-token-xyz')

        # Verify expiration time calculated correctly (24 hours = 86400 seconds, within 1 minute tolerance)
        expires_at_str = self.ICP.get_param('bm_fleet_gps.token_expires_at')
        expires_at = datetime.fromisoformat(expires_at_str)
        expected_expiry = datetime.now() + timedelta(seconds=86400)

        # Check expiry is within 1 minute of expected
        time_diff = abs((expires_at - expected_expiry).total_seconds())
        self.assertLess(time_diff, 60)

        # Verify API called with correct credentials
        call_args = mock_post.call_args
        self.assertEqual(call_args[1]['json']['username'], 'test_user')
        self.assertEqual(call_args[1]['json']['pwd'], 'test_pass')

    @patch('requests.post')
    def test_06_request_new_token_api_failure(self, mock_post):
        """Test API failure during token request"""
        # Mock API error response
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("API Error: Invalid credentials")
        mock_post.return_value = mock_response

        # Should raise Exception
        with self.assertRaises(Exception) as context:
            self.TokenHelper._request_new_token()

        # Verify error message contains API error
        self.assertIn('ADSUN API token request failed', str(context.exception))

        # Verify no token saved to config
        saved_token = self.ICP.get_param('bm_fleet_gps.api_token')
        self.assertFalse(saved_token)

    @patch('requests.post')
    def test_07_request_new_token_network_error(self, mock_post):
        """Test network error during token request"""
        # Mock network exception
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError("Network timeout")

        # Should raise Exception
        with self.assertRaises(Exception) as context:
            self.TokenHelper._request_new_token()

        # Verify error message
        self.assertIn('ADSUN API token request failed', str(context.exception))

    @patch('requests.get')
    def test_08_validate_token_valid(self, mock_get):
        """Test token validation with valid token"""
        # Mock successful API test call
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Validate token
        is_valid = self.TokenHelper.validate_token('test-valid-token')

        # Verify returns True
        self.assertTrue(is_valid)

        # Verify API was called with correct authorization
        call_args = mock_get.call_args
        self.assertIn('Authorization', call_args[1]['headers'])
        self.assertEqual(call_args[1]['headers']['Authorization'], 'Bearer test-valid-token')

    @patch('requests.get')
    def test_09_validate_token_invalid(self, mock_get):
        """Test token validation with invalid/expired token"""
        # Mock failed API test call (401 Unauthorized)
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        # Validate token
        is_valid = self.TokenHelper.validate_token('test-invalid-token')

        # Verify returns False
        self.assertFalse(is_valid)

    @patch('requests.get')
    def test_10_get_device_serials_from_api(self, mock_get):
        """Test fetching device serial numbers from API"""
        # Mock successful device list API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'Status': 1,
            'Datas': [
                {'SerialNumber': '123456789', 'DeviceName': 'Vehicle 1'},
                {'SerialNumber': '987654321', 'DeviceName': 'Vehicle 2'},
                {'SerialNumber': '555555555', 'DeviceName': 'Vehicle 3'}
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # Set up valid token
        future_expiry = (datetime.now() + timedelta(hours=1)).isoformat()
        self.ICP.set_param('bm_fleet_gps.api_token', 'valid-token')
        self.ICP.set_param('bm_fleet_gps.token_expires_at', future_expiry)

        # Fetch device serials
        devices = self.TokenHelper.get_device_serials_from_api(company_id=1136)

        # Verify returns list of devices
        self.assertTrue(isinstance(devices, list))
        self.assertEqual(len(devices), 3)
        self.assertEqual(devices[0]['SerialNumber'], '123456789')
        self.assertEqual(devices[1]['SerialNumber'], '987654321')

        # Verify API called with correct parameters
        call_args = mock_get.call_args
        self.assertEqual(call_args[1]['params']['companyId'], 1136)
        self.assertIn('x-access-token', call_args[1]['headers'])
        self.assertEqual(call_args[1]['headers']['x-access-token'], 'valid-token')
