# -*- coding: utf-8 -*-

from odoo import models


class ApiConfigMixin(models.AbstractModel):
    """Mixin for centralized API configuration management

    Provides a single source of truth for API configuration parameters,
    reducing code duplication and improving maintainability.

    This mixin should be inherited by models that need to access
    GPS API configuration (ADSUN, geocoding services, etc.).
    """
    _name = 'bm.fleet.api.config.mixin'
    _description = 'API Configuration Helper Mixin'

    def _get_adsun_api_config(self):
        """Get ADSUN GPS API configuration from system parameters

        Retrieves ADSUN GPS API configuration from ir.config_parameter.
        This centralizes configuration access and provides a consistent interface.

        Returns:
            dict: Configuration dictionary with keys:
                - api_url (str): ADSUN API base URL
                - company_id (int): Default company ID for GPS API
                - ssl_verify (bool): Whether to verify SSL certificates

        Example:
            >>> config = self._get_adsun_api_config()
            >>> requests.get(config['api_url'], verify=config['ssl_verify'])
        """
        ICP = self.env['ir.config_parameter'].sudo()

        return {
            'api_url': ICP.get_param(
                'bm_fleet_gps.api_url',
                'https://systemroute.adsun.vn/api'
            ),
            'company_id': int(ICP.get_param(
                'bm_fleet_gps.default_company_id',
                '1136'
            )),
            'ssl_verify': ICP.get_param(
                'bm_fleet_gps.ssl_verify',
                'True'
            ) == 'True',
        }

    def _get_ssl_verify(self):
        """Get SSL verification setting

        Convenience method to get just the SSL verification flag.
        Useful for quick access when other config params are not needed.

        Returns:
            bool: Whether to verify SSL certificates

        Example:
            >>> ssl_verify = self._get_ssl_verify()
            >>> requests.get(url, verify=ssl_verify)
        """
        return self._get_adsun_api_config()['ssl_verify']

    def _get_violation_api_config(self):
        """Get traffic violation check API configuration

        Retrieves configuration for third-party violation checking API (iphatnguoi.com).
        Used to check traffic violations based on vehicle license plate.

        Returns:
            dict: Configuration dictionary with keys:
                - api_url (str): Violation check API base URL
                - enabled (bool): Whether violation checking is enabled
                - cache_hours (int): Cache duration in hours to avoid excessive API calls

        Example:
            >>> config = self._get_violation_api_config()
            >>> if config['enabled']:
            >>>     requests.get(f"{config['api_url']}/{plate}_1_true")
        """
        ICP = self.env['ir.config_parameter'].sudo()

        return {
            'api_url': ICP.get_param(
                'bm_fleet_gps.violation_api_url',
                'https://iphatnguoi.com/api/check-violation'
            ),
            'enabled': ICP.get_param(
                'bm_fleet_gps.violation_check_enabled',
                'True'
            ) == 'True',
            'cache_hours': int(ICP.get_param(
                'bm_fleet_gps.violation_cache_hours',
                '24'
            )),
        }
