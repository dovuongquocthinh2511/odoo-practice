# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class FleetTransportationJourney(models.Model):
    _name = 'bm.fleet.transportation.journey'
    _inherit = ['bm.fleet.geocoding.mixin']
    _description = 'Transportation Journey - GPS Waypoint (Điểm hành trình GPS)'
    _order = 'timestamp desc, id desc'

    # Basic Waypoint Information
    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Xe',
        required=True,
        index=True,
        help="Vehicle for this waypoint"
    )

    # Location Information (from GPS API)
    longitude = fields.Float(
        string='Kinh độ',
        digits=(10, 7),
        help="Longitude coordinate"
    )

    latitude = fields.Float(
        string='Vĩ độ',
        digits=(10, 7),
        help="Latitude coordinate"
    )

    address = fields.Text(
        string='Địa chỉ',
        help="Address retrieved from geocode API"
    )

    is_address_synced = fields.Boolean(
        string='Đã xử lý địa chỉ',
        default=False,
        index=True,
        help="Marks whether this waypoint has been processed for address geocoding"
    )

    # GPS Status Information
    speed = fields.Float(
        string='Tốc độ (km/h)',
        digits=(8, 2),
        help="Vehicle speed at this waypoint"
    )

    machine_status = fields.Boolean(
        string='Máy nổ',
        help="Engine on/off status"
    )

    gps_status = fields.Boolean(
        string='GPS Active',
        help="GPS signal status"
    )

    # Distance between waypoints (calculated from API TotalDistance)
    distance = fields.Float(
        string='Khoảng cách (km)',
        digits=(16, 2),
        help="Distance traveled between this waypoint and previous waypoint (calculated as: current TotalDistance - previous TotalDistance)"
    )

    # Original API timestamp
    timestamp = fields.Datetime(
        string='Timestamp',
        help="Original TimeUpdate from GPS API",
        index=True
    )

    driver_id = fields.Many2one(
        'res.partner',
        string='Tài xế',
        domain="[('is_company', '=', False)]",
        help="Driver"
    )

    # API Related fields
    api_data = fields.Text(
        string='API Data',
        help="Raw data from ADSUN API (for debugging)"
    )

    _sql_constraints = [
        ('unique_vehicle_timestamp', 'unique(vehicle_id, timestamp)',
         _('Duplicate waypoint detected for same vehicle and timestamp!'))
    ]

    @api.depends('vehicle_id', 'timestamp')
    def _compute_display_name(self):
        """Generate display name for waypoint"""
        for record in self:
            if record.vehicle_id and record.timestamp:
                record.display_name = f"{record.vehicle_id.name} - {record.timestamp}"
            else:
                record.display_name = "New Waypoint"

    @api.onchange('latitude', 'longitude')
    def _onchange_coordinates(self):
        """Fetch address when coordinates change"""
        if self.latitude and self.longitude:
            self.fetch_address_from_geocode()

    def fetch_address_from_geocode(self, use_openstreetmap=True):
        """Fetch address from coordinates using geocoding mixin

        Args:
            use_openstreetmap: If True, try OpenStreetMap if ADSUN fails
        """
        for record in self:
            if not (record.latitude and record.longitude):
                continue

            # Use geocoding mixin
            address = record.geocode_coordinates(
                record.latitude,
                record.longitude,
                use_openstreetmap_fallback=use_openstreetmap
            )

            if address:
                record.address = address
                _logger.info(f"Address fetched for coordinates ({record.latitude}, {record.longitude}): {address[:50]}...")

    @api.model
    def fetch_missing_addresses(self, limit=None, use_openstreetmap=True):
        """Batch fetch addresses for waypoints with null addresses

        Args:
            limit: Maximum number of waypoints to process (to respect rate limits).
                   If None, reads from system parameter 'bm_fleet_gps.geocoding_batch_limit'.
                   Default system parameter value: 100
            use_openstreetmap: Whether to use OpenStreetMap if ADSUN fails

        Returns:
            dict with statistics: {
                'processed': int,
                'success': int,
                'failed': int
            }

        Note:
            Transaction is managed automatically by Odoo. All changes will commit
            on success or rollback entirely on failure.
        """
        if limit is None:
            ICP = self.env['ir.config_parameter'].sudo()
            limit = int(ICP.get_param('bm_fleet_gps.geocoding_batch_limit', '100'))

        waypoints = self.search([
            ('is_address_synced', '!=', True),
            ('latitude', '!=', 0),
            ('longitude', '!=', 0)
        ], limit=limit, order='timestamp desc')

        processed = 0
        success = 0
        failed = 0

        _logger.info(f"Starting batch address fetch for {len(waypoints)} waypoints")

        for waypoint in waypoints:
            try:
                address = waypoint.geocode_coordinates(
                    waypoint.latitude,
                    waypoint.longitude,
                    use_openstreetmap_fallback=use_openstreetmap
                )

                if address:
                    waypoint.address = address
                    success += 1
                    _logger.debug(f"Fetched address for waypoint {waypoint.id}")
                else:
                    failed += 1

                waypoint.is_address_synced = True
                processed += 1

                if processed % 10 == 0:
                    _logger.info(f"Progress: {processed}/{len(waypoints)} waypoints processed")

            except Exception as e:
                _logger.error(f"Failed to fetch address for waypoint {waypoint.id}: {e}")
                # Mark as processed even on exception to avoid infinite retries
                waypoint.is_address_synced = True
                failed += 1
                processed += 1
                continue

        _logger.info(
            f"Batch address fetch completed: "
            f"{processed} processed, {success} success, {failed} failed"
        )

        return {
            'processed': processed,
            'success': success,
            'failed': failed
        }

    @api.model
    def cron_fetch_missing_addresses(self):
        """Cron job to fetch addresses for waypoints with null addresses

        The limit is configurable via system parameter 'bm_fleet_gps.geocoding_batch_limit'.
        Default is 100 waypoints per run to respect rate limits.
        """
        ICP = self.env['ir.config_parameter'].sudo()
        limit = int(ICP.get_param('bm_fleet_gps.geocoding_batch_limit', '100'))

        result = self.fetch_missing_addresses(limit=limit, use_openstreetmap=True)
        _logger.info(
            f"Cron address fetch: {result['success']} addresses fetched, "
            f"{result['failed']} failed from {result['processed']} waypoints"
        )

    def action_refresh_address(self):
        """Manual action to refresh address from coordinates"""
        self.fetch_address_from_geocode()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Address has been updated from geocode service.'),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
