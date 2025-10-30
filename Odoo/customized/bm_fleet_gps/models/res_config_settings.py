# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Settings configuration for BM Fleet GPS module

    Extends Odoo's settings to add GPS tracking and violation checking configuration.
    All settings are stored in ir.config_parameter for persistence.
    """
    _inherit = 'res.config.settings'

    # ========== GPS API Configuration ==========
    gps_api_url = fields.Char(
        'GPS API URL',
        config_parameter='bm_fleet_gps.api_url',
        help="Base URL for ADSUN GPS API (e.g., https://systemroute.adsun.vn/api)"
    )

    gps_api_username = fields.Char(
        'GPS API Username',
        config_parameter='bm_fleet_gps.api_username',
        help="Username for ADSUN GPS API authentication"
    )

    gps_api_password = fields.Char(
        'GPS API Password',
        config_parameter='bm_fleet_gps.api_password',
        help="Password for ADSUN GPS API authentication"
    )

    gps_default_company_id = fields.Integer(
        'Default GPS Company ID',
        config_parameter='bm_fleet_gps.default_company_id',
        help="Default company ID for GPS API requests"
    )

    gps_ssl_verify = fields.Boolean(
        'Verify SSL Certificates',
        config_parameter='bm_fleet_gps.ssl_verify',
        default=True,
        help="Enable SSL certificate verification for GPS API requests"
    )

    # ========== Traffic Violation Check Configuration ==========
    violation_check_enabled = fields.Boolean(
        'Enable Violation Checking',
        config_parameter='bm_fleet_gps.violation_check_enabled',
        default=True,
        help="Enable automatic traffic violation checking via iphatnguoi.com API"
    )

    violation_api_url = fields.Char(
        'Violation API URL',
        config_parameter='bm_fleet_gps.violation_api_url',
        default='https://iphatnguoi.com/api/check-violation',
        help="Base URL for traffic violation check API (iphatnguoi.com)"
    )

    violation_cache_hours = fields.Integer(
        'Violation Cache Duration (hours)',
        config_parameter='bm_fleet_gps.violation_cache_hours',
        default=24,
        help="How long to cache violation check results before re-checking (in hours)"
    )

    # ========== Data Management ==========
    gps_retention_days = fields.Integer(
        'Data Retention (days)',
        config_parameter='bm_fleet_gps.retention_days',
        default=90,
        help="Number of days to keep GPS journey data before automatic cleanup"
    )

    gps_sync_batch_size = fields.Integer(
        'Sync Batch Size',
        config_parameter='bm_fleet_gps.sync_batch_size',
        default=100,
        help="Number of vehicles to sync per batch during scheduled sync"
    )

    gps_delete_batch_size = fields.Integer(
        'Delete Batch Size',
        config_parameter='bm_fleet_gps.delete_batch_size',
        default=500,
        help="Number of records to delete per batch during cleanup"
    )

    geocoding_batch_limit = fields.Integer(
        'Geocoding Batch Limit',
        config_parameter='bm_fleet_gps.geocoding_batch_limit',
        default=100,
        help="Maximum number of addresses to geocode per cron job run"
    )
