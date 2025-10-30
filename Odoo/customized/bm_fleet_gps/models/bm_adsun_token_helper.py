# -*- coding: utf-8 -*-

from odoo import api, models
from datetime import datetime, timedelta
import requests
import logging

from ..utils.decorators import retry
from ..utils.exceptions import AdsunRequestTokenException

_logger = logging.getLogger(__name__)


class ADSUNTokenHelper(models.AbstractModel):
    """Helper for ADSUN API token management using ir.config_parameter"""
    _name = 'bm.fleet.adsun.token'
    _description = 'ADSUN API Token Helper'

    @api.model
    def get_active_token(self, force_refresh=False):
        """
        Get active token, refresh if expired

        Args:
            force_refresh (bool): Force refresh token even if not expired

        Returns:
            str: Active API token
        """
        ICP = self.env['ir.config_parameter'].sudo()
        token = ICP.get_param('bm_fleet_gps.api_token')
        expires_at = ICP.get_param('bm_fleet_gps.token_expires_at')

        if force_refresh or not token or self._is_expired(expires_at):
            _logger.info("Token expired or refresh requested, requesting new token...")
            return self._request_new_token()

        return token

    @api.model
    def _is_expired(self, expires_at_str):
        """
        Check if token is expired

        Args:
            expires_at_str (str): ISO format datetime string

        Returns:
            bool: True if expired, False otherwise
        """
        if not expires_at_str:
            return True

        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            # Add 5 minute buffer to avoid edge cases
            return datetime.now() >= (expires_at - timedelta(minutes=5))
        except Exception as e:
            _logger.warning(f"Failed to parse token expiry date: {e}")
            return True

    @api.model
    @retry(
        max_attempts=3,
        delay=1,
        backoff=2,
        exceptions=(requests.exceptions.RequestException,),
        exclude_exceptions=(AdsunRequestTokenException,)
    )
    def _request_new_token(self):
        """Request new token from ADSUN API with automatic retry

        Automatically retries up to 3 times with exponential backoff (1s, 2s, 4s)
        if request fails due to network/connection errors.

        Returns:
            str: New API token

        Raises:
            AdsunRequestTokenException: If token request fails after 3 retries,
                or if configuration is missing, or if API response is invalid
        """
        ICP = self.env['ir.config_parameter'].sudo()
        auth_url = ICP.get_param('bm_fleet_gps.auth_url')
        username = ICP.get_param('bm_fleet_gps.api_username')
        password = ICP.get_param('bm_fleet_gps.api_password')
        ssl_verify = ICP.get_param('bm_fleet_gps.ssl_verify', 'True') == 'True'

        if not auth_url or not username or not password:
            raise AdsunRequestTokenException(
                "Missing ADSUN API configuration. Check ir.config_parameter settings."
            )

        try:
            _logger.info(f"Requesting new ADSUN token from {auth_url}/Auth/LoginV4")
            response = requests.post(
                f"{auth_url}/Auth/LoginV4",
                json={'username': username, 'pwd': password},
                verify=ssl_verify,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            token = data.get('Token')
            expires_in = 86400  # Default 24 hours (API doesn't return expires_in)

            if not token:
                raise AdsunRequestTokenException("No Token in API response")

            self._save_token(token, expires_in)
            _logger.info(f"✓ New token obtained, expires in {expires_in} seconds (24 hours)")
            return token

        except requests.exceptions.RequestException as e:
            _logger.error(f"✗ Failed to request ADSUN token: {e}")
            # Let retry decorator handle this - will retry up to 3 times
            raise
        except AdsunRequestTokenException:
            # Don't wrap this, let it propagate without retry
            raise
        except Exception as e:
            _logger.error(f"✗ Unexpected error requesting token: {e}")
            raise AdsunRequestTokenException(f"Unexpected error: {str(e)}")

    @api.model
    def _save_token(self, token, expires_in):
        """
        Save token to config parameters

        Args:
            token (str): API token
            expires_in (int): Seconds until expiration
        """
        ICP = self.env['ir.config_parameter'].sudo()
        expires_at = datetime.now() + timedelta(seconds=expires_in)

        ICP.set_param('bm_fleet_gps.api_token', token)
        ICP.set_param('bm_fleet_gps.token_expires_at', expires_at.isoformat())

        _logger.debug(f"Token saved, expires at {expires_at.isoformat()}")

    @api.model
    def validate_token(self, token):
        """
        Validate token by making a test API call

        Args:
            token (str): Token to validate

        Returns:
            bool: True if valid, False otherwise
        """
        try:
            ICP = self.env['ir.config_parameter'].sudo()
            url = ICP.get_param('bm_fleet_gps.api_url')
            ssl_verify = ICP.get_param('bm_fleet_gps.ssl_verify', 'True') == 'True'

            # Test with a simple API call
            response = requests.get(
                f"{url}/Device/GetDeviceStatusByCompanyId",
                params={'companyId': 1},
                headers={'Authorization': f'Bearer {token}'},
                verify=ssl_verify,
                timeout=5
            )

            return response.status_code == 200
        except Exception as e:
            _logger.warning(f"Token validation failed: {e}")
            return False

    @api.model
    def get_device_serials_from_api(self, company_id=1136):
        """
        Fetch all device serial numbers from ADSUN API

        Args:
            company_id (int): Company ID to fetch devices for (default: 1136)

        Returns:
            list: List of dict with device information including serial numbers
        """
        ICP = self.env['ir.config_parameter'].sudo()
        url = ICP.get_param('bm_fleet_gps.api_url')
        ssl_verify = ICP.get_param('bm_fleet_gps.ssl_verify', 'True') == 'True'

        token = self.get_active_token()

        params = {'companyId': company_id}
        headers = {
            'x-access-token': token,
            'token': token,
            'User-Agent': 'Odoo Fleet GPS Module/1.0'
        }

        try:
            _logger.info(f"Fetching device serials for company {company_id}")
            response = requests.get(
                f"{url}/Device/GetDeviceStatusByCompanyId",
                params=params,
                headers=headers,
                timeout=30,
                verify=ssl_verify
            )
            response.raise_for_status()

            data = response.json()

            if isinstance(data, dict) and data.get('Status') == 1:
                devices = data.get('Datas', [])
                _logger.info(f"Successfully fetched {len(devices)} devices from API")
                return devices
            else:
                error_msg = data.get('Description', 'Unknown error')
                _logger.error(f"API error fetching device serials: {error_msg}")
                return []

        except requests.RequestException as e:
            _logger.error(f"Failed to fetch device serials from API: {e}")
            return []
        except Exception as e:
            _logger.error(f"Unexpected error fetching device serials: {e}")
            return []
