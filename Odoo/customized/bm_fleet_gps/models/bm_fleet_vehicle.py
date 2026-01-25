# -*- coding: utf-8 -*-

import requests
import logging
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ..utils.tz import adsun_time_to_utc
from ..utils.exceptions import AdsunRequestTokenException
from ..utils.performance_helper import GPSDataCache, QueryOptimizer, performance_monitor, performance_metrics

_logger = logging.getLogger(__name__)


class FleetVehicle(models.Model):
    _name = 'fleet.vehicle'
    _inherit = ['fleet.vehicle', 'bm.fleet.geocoding.mixin', 'bm.fleet.api.config.mixin']

    # ========== GPS Device Info ==========
    adsun_device_serial_number = fields.Char(
        'ADSUN Device Serial Number',
        help="ADSUN GPS device serial number for API calls"
    )
    gps_company_id = fields.Integer(
        'GPS Company ID',
        default=1136,
        help="ADSUN company ID"
    )

    # ========== Current Location ==========
    current_latitude = fields.Float(
        'Current Latitude',
        compute='_compute_current_location',
        store=False,
        digits=(10, 7),
        help="Current GPS latitude from latest waypoint"
    )
    current_longitude = fields.Float(
        'Current Longitude',
        compute='_compute_current_location',
        store=False,
        digits=(10, 7),
        help="Current GPS longitude from latest waypoint"
    )
    current_address = fields.Char(
        'Current Address',
        compute='_compute_current_address',
        help="Geocoded address from coordinates"
    )
    vehicle_status = fields.Selection([
        ('offline', 'GPS Offline'),
        ('idle', 'Idle/Parked'),
        ('running', 'In Use')
    ], compute='_compute_vehicle_status', store=False, string=_('Vehicle Status'),
       help="Vehicle usage status based on GPS connection and engine state")
    last_update = fields.Datetime(
        'Last GPS Update',
        help="Last GPS data synchronization timestamp"
    )

    # ========== Fuel Consumption ==========
    fuel_consumption = fields.Float(
        'Mức tiêu thụ nhiên liệu (l/100km)',
        digits=(8, 3),
        help="Fuel consumption rate in liters per 100 kilometers (manually entered)"
    )

    total_fuel_used = fields.Float(
        'Tổng nhiên liệu tiêu thụ (lít)',
        digits=(16, 2),
        compute='_compute_total_fuel_used',
        store=False,
        help="Total fuel consumed today = distance × fuel_consumption / 100"
    )

    # ========== Traffic Violation Checking (iphatnguoi.com API) ==========
    # STORED FIELDS (Database) - Optimized for queries and caching
    violation_status = fields.Selection([
        ('none', 'Không có vi phạm'),
        ('pending', 'Có vi phạm chưa xử lý'),
        ('paid', 'Đã xử lý'),
    ], string='Trạng thái phạt nguội', readonly=True, default='none',
       index=True, store=True,
       help="Traffic violation status for filtering and searching")

    violation_count = fields.Integer(
        'Số lần vi phạm chưa xử lý',
        readonly=True,
        default=0,
        index=True,
        store=True,
        help="Number of pending violations (for sorting and grouping)"
    )

    violation_checked_time = fields.Datetime(
        'Lần kiểm tra cuối',
        readonly=True,
        store=True,
        help="Last time violation check was performed (for cache logic)"
    )

    violation_api_response = fields.Json(
        'Violation API Response Data',
        readonly=True,
        store=True,
        help="Full API response from iphatnguoi.com - source for computed fields"
    )

    # COMPUTED FIELDS (Display Only) - Not stored in database
    violation_time = fields.Datetime(
        'Thời gian vi phạm gần nhất',
        compute='_compute_violation_details',
        store=False,
        readonly=True,
        help="Latest violation timestamp (computed from API response)"
    )

    violation_location = fields.Char(
        'Địa điểm vi phạm',
        compute='_compute_violation_details',
        store=False,
        readonly=True,
        help="Violation location (computed from API response)"
    )

    violation_behavior = fields.Text(
        'Hành vi vi phạm',
        compute='_compute_violation_details',
        store=False,
        readonly=True,
        help="Violation behavior description (computed from API response)"
    )

    violation_detecting_unit = fields.Char(
        'Đơn vị phát hiện',
        compute='_compute_violation_details',
        store=False,
        readonly=True,
        help="Police unit that detected violation (computed from API response)"
    )

    # ========== Statistics (Computed) ==========
    running_time_today = fields.Float(
        'Running Time Today (hours)',
        compute='_compute_running_stats',
        help="Total running hours today"
    )
    running_time_week = fields.Float(
        'Running Time This Week (hours)',
        compute='_compute_running_stats',
        help="Total running hours this week"
    )
    last_stop_time = fields.Datetime(
        'Last Stop Time',
        compute='_compute_last_stop_time',
        help="Last time engine was turned off"
    )

    # ========== Branch Info ==========
    branch_id = fields.Many2one(
        'res.branch',
        'Branch',
        help="Branch this vehicle belongs to"
    )

    # ========== Relations ==========
    # Transportation Journey relation (GPS Waypoints)
    transportation_journey_ids = fields.One2many(
        'bm.fleet.transportation.journey',
        'vehicle_id',
        string=_('Transportation Journeys')
    )

    transportation_journey_count = fields.Integer(
        _('Journey Count'),
        compute='_compute_transportation_journey_count'
    )

    @api.depends('transportation_journey_ids.latitude', 'transportation_journey_ids.longitude', 'transportation_journey_ids.timestamp')
    def _compute_current_location(self):
        """Compute current GPS coordinates from latest waypoint with batch optimization"""
        if not self.ids:
            return

        # Batch process vehicles to reduce database queries
        Journey = self.env['bm.fleet.transportation.journey']

        # Get all latest waypoints in one query using DISTINCT ON
        latest_waypoints = Journey.search_read([
            ('vehicle_id', 'in', self.ids),
            ('timestamp', '>=', fields.Datetime.now() - timedelta(days=7))  # Only recent data
        ], fields=['vehicle_id', 'latitude', 'longitude'],
        order='vehicle_id, timestamp desc, id desc', limit=len(self.ids))

        # Create mapping of vehicle_id -> latest waypoint
        waypoint_map = {}
        for wp in latest_waypoints:
            vehicle_id = wp['vehicle_id'][0]
            if vehicle_id not in waypoint_map:  # Keep only the first (latest) per vehicle
                waypoint_map[vehicle_id] = wp

        # Update vehicles with their latest location
        for vehicle in self:
            latest_wp = waypoint_map.get(vehicle.id)
            if latest_wp:
                vehicle.current_latitude = latest_wp.get('latitude', 0.0)
                vehicle.current_longitude = latest_wp.get('longitude', 0.0)
            else:
                # Fallback to already-loaded journeys if available
                if vehicle.transportation_journey_ids:
                    latest_waypoint = vehicle.transportation_journey_ids.sorted('timestamp', reverse=True)[:1]
                    vehicle.current_latitude = latest_waypoint.latitude
                    vehicle.current_longitude = latest_waypoint.longitude
                else:
                    vehicle.current_latitude = 0.0
                    vehicle.current_longitude = 0.0

    @api.depends('current_latitude', 'current_longitude')
    def _compute_current_address(self):
        """Reverse geocode coordinates to address"""
        for vehicle in self:
            if vehicle.current_latitude and vehicle.current_longitude:
                vehicle.current_address = self._reverse_geocode(
                    vehicle.current_latitude,
                    vehicle.current_longitude
                )
            else:
                vehicle.current_address = False

    @api.depends('transportation_journey_ids.timestamp', 'transportation_journey_ids.machine_status')
    def _compute_vehicle_status(self):
        """Compute vehicle status from latest waypoint (no DB storage)

        Status logic:
        - offline: No waypoint or GPS data stale (>30 minutes)
        - running: Recent waypoint with machine_status=True (engine on)
        - idle: Recent waypoint with machine_status=False (engine off, parked)
        """
        for vehicle in self:
            # Use already-loaded transportation_journey_ids instead of searching
            if vehicle.transportation_journey_ids:
                latest = vehicle.transportation_journey_ids.sorted('timestamp', reverse=True)[:1]

                now = fields.Datetime.now()
                time_diff = (now - latest.timestamp).total_seconds() / 60

                if time_diff > 30:
                    vehicle.vehicle_status = 'offline'
                elif latest.machine_status:
                    vehicle.vehicle_status = 'running'
                else:
                    vehicle.vehicle_status = 'idle'
            else:
                vehicle.vehicle_status = 'offline'

    def _calculate_running_time_for_period(self, start_datetime, end_datetime):
        """Calculate running time between two datetime points

        Computes total running hours by finding the time difference between
        the first and last waypoint with engine on (machine_status=True)
        within the specified period.

        Optimized to load only 2 timestamps instead of all matching records.

        Args:
            start_datetime (datetime): Period start time
            end_datetime (datetime): Period end time

        Returns:
            float: Running hours in the period (0.0 if no running waypoints found)

        Example:
            >>> today_start, today_end = get_day_range()
            >>> hours = vehicle._calculate_running_time_for_period(today_start, today_end)
        """
        Journey = self.env['bm.fleet.transportation.journey']

        domain = [
            ('vehicle_id', '=', self.id),
            ('timestamp', '>=', start_datetime),
            ('timestamp', '<=', end_datetime),
            ('machine_status', '=', True)
        ]

        # Get first timestamp (earliest) - only load timestamp field
        first = Journey.search_read(
            domain=domain,
            fields=['timestamp'],
            order='timestamp asc',
            limit=1
        )

        # Get last timestamp (latest) - only load timestamp field
        last = Journey.search_read(
            domain=domain,
            fields=['timestamp'],
            order='timestamp desc',
            limit=1
        )

        if first and last:
            # Calculate time difference
            time_diff = last[0]['timestamp'] - first[0]['timestamp']
            return time_diff.total_seconds() / 3600

        return 0.0

    @api.depends('transportation_journey_ids.machine_status')
    def _compute_running_stats(self):
        """Calculate running time from journey waypoints using date utilities and helper method"""
        from ..utils.date_helper import get_day_range, get_week_range

        for vehicle in self:
            # Today's running time
            today_start, today_end = get_day_range()
            vehicle.running_time_today = vehicle._calculate_running_time_for_period(
                today_start, today_end
            )

            # This week's running time (Monday to today)
            week_start, week_end = get_week_range()
            vehicle.running_time_week = vehicle._calculate_running_time_for_period(
                week_start, week_end
            )

    @api.depends('transportation_journey_ids.machine_status', 'transportation_journey_ids.timestamp')
    def _compute_last_stop_time(self):
        """Find last stop time (machine_status = False) with optimized query"""
        for vehicle in self:
            # Use already-loaded transportation_journey_ids with filtering
            stopped_journeys = vehicle.transportation_journey_ids.filtered(lambda j: not j.machine_status)            

            if stopped_journeys:
                last_stop = stopped_journeys.sorted('timestamp', reverse=True)[:1]
                vehicle.last_stop_time = last_stop.timestamp
            else:
                vehicle.last_stop_time = False

    @api.depends('transportation_journey_ids', 'transportation_journey_ids.timestamp')
    def _compute_transportation_journey_count(self):
        """Count GPS transportation journeys for TODAY only

        Uses optimized read_group query to count waypoints within today's date range.
        Follows the same pattern as _compute_total_fuel_used() for consistency.
        """
        from ..utils.date_helper import get_day_range
        today_start, today_end = get_day_range()

        Journey = self.env['bm.fleet.transportation.journey']
        aggregated_data = Journey.read_group(
            domain=[
                ('vehicle_id', 'in', self.ids),
                ('timestamp', '>=', today_start),
                ('timestamp', '<=', today_end)
            ],
            fields=[],
            groupby=['vehicle_id'],
            lazy=False
        )

        count_map = {
            item['vehicle_id'][0]: item['__count']
            for item in aggregated_data
        }

        for vehicle in self:
            vehicle.transportation_journey_count = count_map.get(vehicle.id, 0)

    @api.depends('transportation_journey_ids.distance', 'fuel_consumption')
    def _compute_total_fuel_used(self):
        """Calculate total fuel consumed based on sum of all waypoint distances today

        Uses read_group for optimized batch query instead of individual searches per vehicle.
        """
        # Calculate today's date range using centralized date helper
        from ..utils.date_helper import get_day_range
        today_start, today_end = get_day_range()

        # Use read_group to aggregate distance sums per vehicle in single query
        Journey = self.env['bm.fleet.transportation.journey']
        aggregated_data = Journey.read_group(
            domain=[
                ('vehicle_id', 'in', self.ids),
                ('timestamp', '>=', today_start),
                ('timestamp', '<=', today_end)
            ],
            fields=['vehicle_id', 'distance:sum'],
            groupby=['vehicle_id'],
            lazy=False
        )

        # Build mapping: vehicle_id -> total_distance
        distance_map = {
            item['vehicle_id'][0]: item['distance']
            for item in aggregated_data
        }

        # Calculate fuel consumption for each vehicle
        for vehicle in self:
            total_distance_today = distance_map.get(vehicle.id, 0.0)

            if vehicle.fuel_consumption and total_distance_today:
                vehicle.total_fuel_used = total_distance_today * vehicle.fuel_consumption / 100
            else:
                vehicle.total_fuel_used = 0.0

    # ========== Traffic Violation API Methods ==========

    @api.depends('violation_api_response')
    def _compute_violation_details(self):
        """Compute display fields from stored JSON API response

        Extracts violation details from the stored API response JSON field.
        This approach minimizes database storage by only storing the raw JSON
        and computing display fields on-the-fly.

        Computed fields:
            - violation_time: Latest violation timestamp
            - violation_location: Violation location
            - violation_behavior: Violation behavior description
            - violation_detecting_unit: Police unit that detected violation
        """
        for vehicle in self:
            response = vehicle.violation_api_response

            if not response or not response.get('violations'):
                # No violation data - clear all computed fields
                vehicle.violation_time = False
                vehicle.violation_location = False
                vehicle.violation_behavior = False
                vehicle.violation_detecting_unit = False
                continue

            # Get latest violation (first in violations array)
            latest = response['violations'][0]

            # Parse violation time: "12:27, 23/09/2024" → UTC datetime
            try:
                time_str = latest.get('violationTime', '')
                if time_str:
                    # Format: "12:27, 23/09/2024" (Vietnam time)
                    time_part, date_part = time_str.split(', ')
                    hour, minute = time_part.split(':')
                    day, month, year = date_part.split('/')

                    # Create naive datetime (Vietnam time)
                    dt_vn = datetime(
                        int(year), int(month), int(day),
                        int(hour), int(minute)
                    )

                    # Convert Vietnam time to UTC for Odoo storage
                    from ..utils.tz import VIETNAM_TZ
                    import pytz

                    dt_vn_aware = VIETNAM_TZ.localize(dt_vn)
                    dt_utc_aware = dt_vn_aware.astimezone(pytz.UTC)
                    vehicle.violation_time = dt_utc_aware.replace(tzinfo=None)  # UTC naive datetime
                else:
                    vehicle.violation_time = False
            except Exception as e:
                _logger.warning(f"Failed to parse violation time '{time_str}': {e}")
                vehicle.violation_time = False

            # Extract other display fields from API response
            vehicle.violation_location = latest.get('violationLocation', '')
            vehicle.violation_behavior = latest.get('violationBehavior', '')
            vehicle.violation_detecting_unit = latest.get('detectingUnit', '')

    def _call_violation_api(self, license_plate, vehicle_type=1):
        """Call iphatnguoi.com traffic violation check API

        Pattern: Same as _call_get_device_trip_api() for consistency

        Args:
            license_plate (str): Vehicle license plate number
            vehicle_type (int): 1=Car, 2=Motorcycle, 3=Electric bike (default: 1)

        Returns:
            dict: API response with structure:
                {
                    'isSuccess': bool,
                    'updatedAt': timestamp,
                    'violations': [
                        {
                            'licensePlate': str,
                            'violationTime': str,
                            'violationLocation': str,
                            'violationBehavior': str,
                            'status': str,
                            'detectingUnit': str,
                            ...
                        }
                    ]
                }

        Raises:
            UserError: If API call fails or network error occurs
        """
        config = self._get_violation_api_config()

        if not config['enabled']:
            _logger.info("Violation check disabled in configuration")
            return {'isSuccess': True, 'violations': []}

        # Format license plate: remove dashes, dots, spaces (30G-887.50 → 30G88750)
        formatted_plate = license_plate.replace('-', '').replace('.', '').replace(' ', '')

        # Build API endpoint URL
        url = f"{config['api_url']}/{formatted_plate}_{vehicle_type}_true"

        headers = {
            'User-Agent': 'Odoo Fleet GPS Module/1.0'
        }

        try:
            ssl_verify = self._get_ssl_verify()

            response = requests.get(
                url,
                headers=headers,
                verify=ssl_verify
            )

            # Check HTTP status codes
            if response.status_code == 404:
                raise UserError(_("Violation API endpoint not found. Check configuration."))
            elif response.status_code == 429:
                raise UserError(_("Too many requests to violation API. Please try again later."))
            elif response.status_code >= 500:
                raise UserError(_("Violation API server error. Please try again later."))

            response.raise_for_status()

            data = response.json()

            # Validate response structure
            if not isinstance(data, dict) or 'isSuccess' not in data:
                raise UserError(_("Invalid response format from violation API"))

            return data

        except requests.Timeout:
            _logger.error(f"Violation API timeout for plate {license_plate} - should not happen with timeout disabled")
            raise UserError(_("Violation API timeout - API server taking too long to respond."))
        except requests.ConnectionError:
            _logger.error(f"Cannot connect to violation API for plate {license_plate}")
            raise UserError(_("Cannot connect to violation API. Check network."))
        except ValueError as e:
            _logger.error(f"Invalid JSON from violation API: {e}")
            raise UserError(_("Invalid JSON response from violation API"))
        except requests.RequestException as e:
            _logger.error(f"Violation API call failed for {license_plate}: {e}")
            raise UserError(_("Failed to check violations: %s") % str(e))

    def _process_violation_response(self, api_response):
        """Process API response and update stored fields

        Updates the minimal set of stored fields based on API response.
        Display fields are automatically updated via computed field dependencies.

        Args:
            api_response (dict): JSON response from iphatnguoi.com API
        """
        # Always update checked time
        self.violation_checked_time = fields.Datetime.now()

        if not api_response.get('isSuccess'):
            _logger.warning(f"API returned isSuccess=False for vehicle {self.license_plate}")
            return

        violations = api_response.get('violations', [])

        # Store full API response (source of truth for computed fields)
        self.violation_api_response = api_response

        # Count pending violations only (status contains "chưa")
        self.violation_count = len([
            v for v in violations
            if 'chưa' in v.get('status', '').lower()
        ])

        # Determine violation status
        if violations:
            status_text = violations[0].get('status', '').lower()
            if 'đã' in status_text:
                self.violation_status = 'paid'
            elif 'chưa' in status_text:
                self.violation_status = 'pending'
            else:
                self.violation_status = 'pending'  # Default to pending
        else:
            self.violation_status = 'none'

        # Computed fields will automatically update via @api.depends('violation_api_response')

    @api.onchange('license_plate')
    def _onchange_license_plate_check_violation(self):
        """Auto-check violations when license plate changes

        Implements caching logic to avoid excessive API calls.
        Only checks if cache has expired (default: 24 hours).
        """
        if not self.license_plate or len(self.license_plate) < 6:
            return

        # Check if cached data is still valid
        config = self._get_violation_api_config()

        if self.violation_checked_time:
            hours_since_check = (
                fields.Datetime.now() - self.violation_checked_time
            ).total_seconds() / 3600

            if hours_since_check < config['cache_hours']:
                _logger.info(
                    f"Using cached violation data for {self.license_plate} "
                    f"(checked {hours_since_check:.1f}h ago)"
                )
                return  # Use cached data

        # Cache expired or first check - call API
        try:
            result = self._call_violation_api(self.license_plate)
            self._process_violation_response(result)
        except UserError as e:
            # Don't block form - just show warning
            return {
                'warning': {
                    'title': _('Violation Check Warning'),
                    'message': str(e)
                }
            }

    def action_manual_check_violation(self):
        """Manual violation check button action

        Allows user to manually trigger violation check regardless of cache.

        Returns:
            dict: Client action to display notification
        """
        self.ensure_one()

        if not self.license_plate:
            raise UserError(_("Please enter license plate first"))

        try:
            result = self._call_violation_api(self.license_plate)
            self._process_violation_response(result)

            # Build notification message
            if self.violation_count > 0:
                msg = _('Tìm thấy %d vi phạm chưa xử lý') % self.violation_count
                msg_type = 'warning'
            else:
                msg = _('Không có vi phạm')
                msg_type = 'success'

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Kiểm tra hoàn tất'),
                    'message': msg,
                    'type': msg_type,
                    'sticky': False,
                }
            }
        except UserError:
            # Re-raise to show error dialog
            raise

    def write(self, vals):
        """Override write to handle GPS serial number changes

        When adsun_device_serial_number is changed, delete all old GPS waypoint records.
        This ensures clean data when a vehicle gets a new GPS device.
        """
        # Check if serial is being changed
        if 'adsun_device_serial_number' in vals:
            for vehicle in self:
                old_serial = vehicle.adsun_device_serial_number
                new_serial = vals.get('adsun_device_serial_number')

                # Only cleanup if serial actually changed and old serial exists
                if old_serial and new_serial and str(old_serial) != str(new_serial):
                    # Delete all GPS waypoints
                    waypoint_count = len(vehicle.transportation_journey_ids)

                    if waypoint_count > 0:
                        vehicle.transportation_journey_ids.unlink()
                        _logger.info(f"Deleted {waypoint_count} old GPS waypoints for {vehicle.name} (serial changed from {old_serial} to {new_serial})")
                    else:
                        _logger.info(f"GPS serial changed for {vehicle.name} from {old_serial} to {new_serial} (no old waypoints to clean)")

        return super(FleetVehicle, self).write(vals)

    def _reverse_geocode(self, lat, lng):
        """Convert coordinates to address using geocoding mixin"""
        return self.geocode_coordinates(lat, lng, use_openstreetmap_fallback=True)

    # ========== API Integration Methods ==========

    def _get_device_status(self, serial_number):
        """Get device status from GetDeviceStatusByCompanyId API

        Uses centralized API configuration via _get_adsun_api_config() mixin method.

        Args:
            serial_number: GPS device serial number

        Returns:
            dict: Device status data with KmNgay, Location, etc.
                  Returns None if not found or error
        """
        try:
            # Get configuration from centralized helper
            config = self._get_adsun_api_config()

            # Build full URL from base URL
            url = f"{config['api_url']}/Device/GetDeviceStatusByCompanyId"

            # Use vehicle's company ID or fall back to default
            company_id = self.gps_company_id or config['company_id']

            token = self.env['bm.fleet.adsun.token'].get_active_token()
            params = {'companyId': company_id}
            headers = {
                'x-access-token': token,
                'token': token,
                'User-Agent': 'Odoo Fleet GPS Module/1.0'
            }

            response = requests.get(url, params=params, headers=headers, verify=config['ssl_verify'])
            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict) and data.get('Status') == 1:
                devices = data.get('Datas', [])

                # Find device by serial number
                for device in devices:
                    if str(device.get('Serial')) == str(serial_number):
                        return device

            return None

        except Exception as e:
            _logger.warning(f"Failed to get device status for serial {serial_number}: {e}")
            return None

    @api.model
    def cron_sync_gps_waypoints(self):
        """Cron job: Sync GPS waypoints (trip history) for all vehicles

        Runs every 5 minutes to sync today's waypoints (00:00 to now).
        More frequent than before (was 30 min) for better real-time tracking.
        """
        vehicles = self.search([('adsun_device_serial_number', '!=', False)])

        _logger.info(f"Starting GPS waypoints sync for {len(vehicles)} vehicles")

        success_count = 0
        error_count = 0
        total_created = 0
        total_skipped = 0

        for vehicle in vehicles:
            try:
                result = vehicle.sync_gps_waypoints_today()

                if result['success']:
                    total_created += result['created']
                    total_skipped += result['skipped']
                    success_count += 1
                else:
                    error_count += 1

            except Exception as e:
                error_count += 1
                _logger.error(f"GPS waypoints sync failed for {vehicle.name}: {e}")
                continue

        _logger.info(
            f"GPS waypoints sync completed: {success_count} success, {error_count} errors, "
            f"{total_created} waypoints created, {total_skipped} duplicates skipped"
        )

    @api.model
    def cron_sync_vehicle_status(self):
        """Cron job: Sync real-time vehicle status for ALL vehicles (every 1 minute)

        Calls GetDeviceStatusByCompanyId API ONCE to get statuses for all vehicles.
        Much more efficient than calling API per vehicle (was N calls, now 1 call).
        
        Updates:
        - gps_status (on/off from GpsState)
        - last_gps_location_latitude (from Vi_do)
        - last_gps_location_longitude (from Kinh_do)
        - last_gps_speed (from Toc_do)
        - last_gps_sync_time (from Thoi_gian)
        """
        try:
            # Get configuration from centralized helper
            config = self.env['fleet.vehicle']._get_adsun_api_config()

            # Build full URL
            url = f"{config['api_url']}/Device/GetDeviceStatusByCompanyId"
            
            token = self.env['bm.fleet.adsun.token'].get_active_token()
            params = {'companyId': config['company_id']}
            headers = {
                'x-access-token': token,
                'token': token,
                'User-Agent': 'Odoo Fleet GPS Module/1.0'
            }
            
            _logger.info("Calling GetDeviceStatusByCompanyId API for all vehicles status sync")
            
            # Single API call for ALL vehicles
            response = requests.get(url, params=params, headers=headers, verify=config['ssl_verify'])
            response.raise_for_status()
            data = response.json()
            
            if not isinstance(data, dict) or data.get('Status') != 1:
                _logger.warning(f"API returned unsuccessful status: {data}")
                return
            
            devices = data.get('Datas', [])
            _logger.info(f"Received status for {len(devices)} devices from API")
            
            # Map devices by serial number for quick lookup
            device_map = {str(device.get('Serial')): device for device in devices}
            
            # Get all vehicles with GPS configured
            vehicles = self.search([('adsun_device_serial_number', '!=', False)])
            
            success_count = 0
            error_count = 0
            not_found_count = 0
            
            for vehicle in vehicles:
                try:
                    serial = str(vehicle.adsun_device_serial_number)
                    device_data = device_map.get(serial)
                    
                    if not device_data:
                        not_found_count += 1
                        _logger.debug(f"No status data for vehicle {vehicle.name} (serial: {serial})")
                        continue
                    
                    # Update vehicle status fields
                    update_vals = {}
                    
                    # GPS status (on/off)
                    gps_state = device_data.get('GpsState')
                    if gps_state in [0, 1]:
                        update_vals['gps_status'] = 'on' if gps_state == 1 else 'off'
                    
                    # Location coordinates
                    if device_data.get('Vi_do'):
                        update_vals['last_gps_location_latitude'] = device_data['Vi_do']
                    if device_data.get('Kinh_do'):
                        update_vals['last_gps_location_longitude'] = device_data['Kinh_do']
                    
                    # Speed
                    if device_data.get('Toc_do') is not None:
                        update_vals['last_gps_speed'] = device_data['Toc_do']
                    
                    # Sync time
                    if device_data.get('Thoi_gian'):
                        try:
                            # Parse time string (format: "DD/MM/YYYY HH:MM:SS", Vietnam time)
                            time_str = device_data['Thoi_gian']
                            dt_vn = datetime.strptime(time_str, '%d/%m/%Y %H:%M:%S')

                            # Convert Vietnam time to UTC for Odoo storage
                            from ..utils.tz import VIETNAM_TZ
                            import pytz

                            dt_vn_aware = VIETNAM_TZ.localize(dt_vn)
                            dt_utc_aware = dt_vn_aware.astimezone(pytz.UTC)
                            update_vals['last_gps_sync_time'] = dt_utc_aware.replace(tzinfo=None)  # UTC
                        except Exception as e:
                            _logger.warning(f"Failed to parse time for {vehicle.name}: {e}")
                    
                    # Write updates if any
                    if update_vals:
                        vehicle.write(update_vals)
                        success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    _logger.error(f"Failed to update status for {vehicle.name}: {e}")
                    continue
            
            _logger.info(
                f"Vehicle status sync completed: {success_count} updated, "
                f"{not_found_count} not found in API, {error_count} errors"
            )
            
        except Exception as e:
            _logger.error(f"Vehicle status sync failed: {e}")

    def sync_gps_waypoints_by_date(self, date=None, batch_size=None):
        """Sync GPS waypoints for a specific date (00:00:00 to 23:59:59 Vietnam time)

        Uses ADSUN API's beginTime and endTime parameters to fetch only waypoints
        within the specified date range, limiting data to one day.

        IMPORTANT: ADSUN API expects datetime in Vietnam timezone (UTC+7).
        This method converts UTC datetime to Vietnam time before sending API request.

        Args:
            date: Date to sync (default: today). Can be:
                  - datetime.date object
                  - datetime.datetime object (time part will be ignored)
                  - String in 'YYYY-MM-DD' format
            batch_size: Number of records to process per batch (None = use config)

        Returns:
            dict with sync statistics: {
                'success': bool,
                'created': int,
                'skipped': int,
                'total': int
            }
        """
        self.ensure_one()

        if not self.adsun_device_serial_number:
            _logger.warning(f"Vehicle {self.name} has no GPS device serial")
            return {'success': False, 'created': 0, 'skipped': 0, 'total': 0}

        # Parse date parameter
        if date is None:
            target_date = fields.Date.today()
        elif isinstance(date, str):
            target_date = fields.Date.from_string(date)
        elif isinstance(date, datetime):
            target_date = date.date()
        else:
            target_date = date

        # Create datetime range for the full day in UTC (Odoo internal format)
        # These are naive datetime objects representing UTC time
        begin_time_utc = datetime.combine(target_date, datetime.min.time())
        end_time_utc = datetime.combine(target_date, datetime.max.time())

        # Convert UTC to Vietnam time for ADSUN API
        # ADSUN API expects datetime in Vietnam timezone (UTC+7)
        from ..utils.tz import utc_to_vietnam_time
        begin_time = utc_to_vietnam_time(begin_time_utc)
        end_time = utc_to_vietnam_time(end_time_utc)

        try:
            token = self.env['bm.fleet.adsun.token'].get_active_token()

            _logger.info(
                f"Syncing GPS for {self.name} on {target_date} "
                f"(Vietnam time: {begin_time} to {end_time})"
            )

            response = self._call_get_device_trip_api(
                self.gps_company_id,
                self.adsun_device_serial_number,
                begin_time,
                end_time,
                token
            )

            if response.get('Status') == 1:
                trip_list = response.get('DeviceTripList', [])
                total_points = len(trip_list)

                if trip_list:
                    _logger.info(f"Fetched {total_points} waypoints for {self.name} on {target_date}")

                    # Process trip waypoints with batch processing
                    result = self._process_trip_waypoints(vehicle=self, trip_list=trip_list, batch_size=batch_size)

                    return {
                        'success': True,
                        'created': result.get('created', 0),
                        'skipped': result.get('skipped', 0),
                        'total': total_points
                    }
                else:
                    _logger.info(f"No GPS waypoints found for {self.name} on {target_date}")
                    return {'success': True, 'created': 0, 'skipped': 0, 'total': 0}
            else:
                error_msg = response.get('Description', 'Unknown error')
                _logger.error(f"API error syncing {self.name} on {target_date}: {error_msg}")
                return {'success': False, 'created': 0, 'skipped': 0, 'total': 0}

        except Exception as e:
            _logger.error(f"Failed to sync GPS for {self.name} on {target_date}: {e}")
            return {'success': False, 'created': 0, 'skipped': 0, 'total': 0}

    def sync_gps_waypoints_today(self, batch_size=None):
        """Convenience method: Sync GPS waypoints for today

        Returns:
            dict with sync statistics
        """
        return self.sync_gps_waypoints_by_date(date=None, batch_size=batch_size)

    def get_journey_history_from_api(self, start_time, end_time):
        """Get journey history directly from ADSUN API for specified time range

        This method is used for historical data retrieval without storing to database.
        Used by the hybrid system to display historical journey data on the map.

        Args:
            start_time (datetime): Start time in Vietnam timezone
            end_time (datetime): End time in Vietnam timezone

        Returns:
            dict: API response with journey waypoints ready for map display
                {
                    'success': bool,
                    'waypoints': list of waypoint dicts,
                    'message': str (error message if failed),
                    'total_points': int
                }
        """
        self.ensure_one()

        if not self.adsun_device_serial_number:
            return {
                'success': False,
                'waypoints': [],
                'message': 'Vehicle has no GPS device serial configured',
                'total_points': 0
            }

        try:
            # Get active token
            token = self.env['bm.fleet.adsun.token'].get_active_token()

            _logger.info(
                f"Fetching journey history for {self.name} from API "
                f"(Vietnam time: {start_time} to {end_time})"
            )

            # Call ADSUN API directly
            response = self._call_get_device_trip_api(
                self.gps_company_id,
                self.adsun_device_serial_number,
                start_time,
                end_time,
                token,
                retry_on_401=True
            )

            if response.get('Status') == 1:
                trip_list = response.get('DeviceTripList', [])
                total_points = len(trip_list)

                if trip_list:
                    # Convert trip data to waypoint format for map display
                    waypoints = []
                    previous_total_distance = None

                    for trip in trip_list:
                        waypoint_data, previous_total_distance = self._prepare_waypoint_data(
                            self, trip, previous_total_distance
                        )

                        if waypoint_data:
                            waypoints.append(waypoint_data)

                    _logger.info(f"Retrieved {len(waypoints)} waypoints from API for {self.name}")

                    return {
                        'success': True,
                        'waypoints': waypoints,
                        'message': f'Successfully retrieved {len(waypoints)} waypoints',
                        'total_points': total_points
                    }
                else:
                    return {
                        'success': True,
                        'waypoints': [],
                        'message': 'No journey data found for the specified time range',
                        'total_points': 0
                    }
            else:
                error_msg = response.get('Description', 'Unknown API error')
                _logger.error(f"API error for {self.name}: {error_msg}")
                return {
                    'success': False,
                    'waypoints': [],
                    'message': f'API error: {error_msg}',
                    'total_points': 0
                }

        except UserError as e:
            # Handle authentication and other user errors
            error_msg = str(e)
            _logger.error(f"User error fetching journey history for {self.name}: {error_msg}")
            return {
                'success': False,
                'waypoints': [],
                'message': error_msg,
                'total_points': 0
            }
        except Exception as e:
            # Handle unexpected errors
            error_msg = f"Failed to fetch journey history: {str(e)}"
            _logger.error(f"Unexpected error for {self.name}: {e}")
            return {
                'success': False,
                'waypoints': [],
                'message': error_msg,
                'total_points': 0
            }

    def _call_get_device_trip_api(self, company_id, serial, begin_time, end_time, token, retry_on_401=True):
        """Call ADSUN GetDeviceTripBySerial API with automatic token refresh on 401 error

        Fetches GPS trip waypoints (DeviceTripList) for specified device and date range.

        IMPORTANT: ADSUN API expects datetime parameters in Vietnam timezone (UTC+7).
        The begin_time and end_time should already be converted from UTC to Vietnam time
        before calling this method (use utc_to_vietnam_time() from utils.tz).

        Args:
            company_id: ADSUN company ID
            serial: GPS device serial number
            begin_time: Start datetime (MUST be in Vietnam timezone, not UTC)
            end_time: End datetime (MUST be in Vietnam timezone, not UTC)
            token: Current API token
            retry_on_401: If True, automatically refresh token and retry on 401 error

        Returns:
            API response as dict with DeviceTripList containing waypoint data
        """
        url = "https://systemroute.adsun.vn/api/Device/GetDeviceTripBySerial"

        params = {
            'companyId': company_id,
            'serial': serial,
            'beginTime': begin_time.strftime('%H:%M:%S %m/%d/%Y'),  # MM/DD/YYYY format required by ADSUN API
            'endTime': end_time.strftime('%H:%M:%S %m/%d/%Y')
        }

        headers = {
            'x-access-token': token,
            'token': token,
            'User-Agent': 'Odoo Fleet GPS Module/1.0'
        }

        try:
            # Get SSL verification setting from centralized config helper
            ssl_verify = self._get_ssl_verify()

            response = requests.get(url, params=params, headers=headers, verify=ssl_verify)

            # Check for 401 before raising exception
            if response.status_code == 401 and retry_on_401:
                _logger.warning(f"Token expired (401), requesting new token...")

                try:
                    # Get fresh token (force refresh to ensure new token)
                    # This will retry up to 3 times internally via @retry decorator
                    new_token = self.env['bm.fleet.adsun.token'].get_active_token(force_refresh=True)
                    _logger.info(f"Got new token, retrying API call...")

                    # Update headers with new token
                    headers['x-access-token'] = new_token
                    headers['token'] = new_token

                    # Retry API call with new token (NO RECURSION)
                    response = requests.get(url, params=params, headers=headers, verify=ssl_verify)
                    response.raise_for_status()
                    return response.json()

                except AdsunRequestTokenException as e:
                    _logger.error(f"Failed to obtain new token: {e}")
                    raise UserError(_("Authentication failed: %s") % str(e))

            # Raise for other HTTP errors
            response.raise_for_status()
            return response.json()

        except AdsunRequestTokenException as e:
            # Handle token errors that occur outside of 401 retry logic
            _logger.error(f"Token authentication error: {e}")
            raise UserError(_("Authentication failed: %s") % str(e))
        except requests.RequestException as e:
            _logger.error(f"ADSUN API call failed: {e}")
            raise UserError(_("Failed to connect to GPS API: %s") % str(e))

    def _calculate_incremental_distance(self, current_total_distance, previous_total_distance):
        """Calculate distance traveled between consecutive waypoints

        ADSUN API returns cumulative TotalDistance (in meters) which may reset to 0
        when engine restarts or GPS device resets. This method handles both normal
        incremental calculation and reset detection.

        Args:
            current_total_distance: Current total distance from API (meters)
            previous_total_distance: Previous total distance (meters), or None for first waypoint

        Returns:
            float: Incremental distance in kilometers

        Examples:
            Normal increment (consecutive waypoints):
            >>> _calculate_incremental_distance(1500, 1000)
            0.5  # (1500 - 1000) / 1000 = 0.5 km

            First waypoint (no previous reference in database):
            >>> _calculate_incremental_distance(11504324, None)
            0.0  # No previous reference, cannot calculate incremental distance
                 # Accept loss of distance traveled before first waypoint

            Reset detected (engine restart, device reset):
            >>> _calculate_incremental_distance(100, 5000)
            0.1  # Reset detected (100 < 5000), use current value: 100 / 1000 = 0.1 km
        """
        if previous_total_distance is not None:
            # Calculate incremental distance
            incremental = current_total_distance - previous_total_distance

            # Detect TotalDistance reset (engine restart, device reset)
            # If current < previous, TotalDistance has been reset to 0
            if incremental < 0:
                # Reset detected: treat current as start of new trip
                # Use current TotalDistance directly (converted to km)
                return current_total_distance / 1000
            else:
                # Normal case: incremental distance between waypoints
                return incremental / 1000
        else:
            # First waypoint in database: no previous reference to calculate incremental distance
            # Cannot determine distance traveled before first waypoint was recorded
            # Accept loss of this unknown distance and start from 0
            return 0.0

    def _prepare_waypoint_data(self, vehicle, trip, previous_total_distance):
        """Parse single trip data into waypoint record format
        
        Args:
            vehicle: fleet.vehicle record
            trip: Single trip data from API
            previous_total_distance: Previous waypoint's total distance for calculation
            
        Returns:
            tuple: (waypoint_data dict, new_previous_total_distance) or (None, previous_total_distance) if skip
        """
        try:
            # Extract and convert timestamp
            timestamp_str = trip.get('TimeUpdate')
            if not timestamp_str:
                return None, previous_total_distance
            
            timestamp = adsun_time_to_utc(timestamp_str)
            if not timestamp:
                return None, previous_total_distance
            
            # Extract location data
            location = trip.get('Location', {})
            lat = location.get('Lat', 0)
            lng = location.get('Lng', 0)
            address = location.get('Address')
            
            # Calculate incremental distance
            current_total_distance = trip.get('TotalDistance', 0)
            incremental_distance = self._calculate_incremental_distance(
                current_total_distance, 
                previous_total_distance
            )
            
            # Prepare waypoint data
            waypoint_data = {
                'vehicle_id': vehicle.id,
                'timestamp': timestamp,
                'latitude': lat,
                'longitude': lng,
                'address': address,
                'speed': trip.get('Speed', 0),
                'machine_status': trip.get('MachineStatus', False),
                'gps_status': trip.get('GpsStatus', False),
                'distance': incremental_distance,
                'api_data': str(trip)
            }
            
            return waypoint_data, current_total_distance
            
        except Exception as e:
            _logger.warning(f"Failed to prepare waypoint: {e}")
            return None, previous_total_distance

    def _bulk_create_waypoints(self, Journey, waypoints_to_create):
        """Bulk create waypoints using SQL INSERT with ON CONFLICT

        Optimized approach using PostgreSQL's INSERT ... ON CONFLICT DO NOTHING
        to handle duplicates atomically at database level, eliminating need for
        pre-checking duplicates via SELECT queries.

        Args:
            Journey: Journey model reference
            waypoints_to_create: List of waypoint data dicts

        Returns:
            int: Number of waypoints successfully created (excluding duplicates)
        """
        if not waypoints_to_create:
            return 0

        # Prepare SQL INSERT with ON CONFLICT
        cr = self.env.cr

        # Build column list and value placeholders
        columns = [
            'vehicle_id', 'longitude', 'latitude', 'speed',
            'machine_status', 'gps_status', 'distance', 'timestamp',
            'api_data', 'create_uid', 'create_date', 'write_uid', 'write_date'
        ]

        values = []
        for waypoint_data in waypoints_to_create:
            # Prepare row values in correct order
            row = (
                waypoint_data['vehicle_id'],
                waypoint_data.get('longitude', 0.0),
                waypoint_data.get('latitude', 0.0),
                waypoint_data.get('speed', 0.0),
                waypoint_data.get('machine_status', False),
                waypoint_data.get('gps_status', False),
                waypoint_data.get('distance', 0.0),
                waypoint_data['timestamp'],
                waypoint_data.get('api_data', ''),
                self.env.uid,  # create_uid
                'NOW()',  # create_date
                self.env.uid,  # write_uid
                'NOW()',  # write_date
            )
            values.append(row)

        # Build INSERT statement with ON CONFLICT
        query = f"""
            INSERT INTO bm_fleet_transportation_journey
            ({', '.join(columns)})
            VALUES ({', '.join(['%s'] * len(columns))})
            ON CONFLICT (vehicle_id, timestamp) DO NOTHING
        """

        # Execute bulk insert
        created_count = 0
        for row_values in values:
            cr.execute(query, row_values)
            created_count += cr.rowcount

        _logger.info(f"SQL bulk insert: {created_count} created, {len(values) - created_count} duplicates skipped")

        return created_count

    def _update_vehicle_last_sync(self, vehicle, trip_list):
        """Update vehicle's last_update timestamp from latest waypoint
        
        Args:
            vehicle: fleet.vehicle record
            trip_list: List of trip data (must have at least one element)
        """
        if not trip_list:
            return
        
        try:
            # Get last waypoint data
            latest = trip_list[-1]
            
            # Convert timestamp from VN time to UTC
            last_update_value = adsun_time_to_utc(latest.get('TimeUpdate'))
            
            # Update vehicle record
            vehicle.write({'last_update': last_update_value})
            
            _logger.info(f"Updated vehicle last_update for {vehicle.name}")
            
        except Exception as e:
            _logger.error(f"Failed to update vehicle last_update for {vehicle.name}: {e}")
            # Continue anyway - waypoints are already created successfully
            pass

    def _get_last_total_distance(self, vehicle):
        """Get TotalDistance from the last waypoint of this vehicle

        Retrieves the most recent waypoint's TotalDistance (in meters) from the database
        to use as reference for calculating incremental distance in the next sync.

        This ensures that each sync operation continues from where the previous sync left off,
        rather than treating every sync as a fresh start (which would cause the first waypoint
        of each sync to store the full lifetime TotalDistance).

        Args:
            vehicle: fleet.vehicle record

        Returns:
            int: TotalDistance in meters from last waypoint, or None if no previous waypoint exists

        Example:
            >>> # Last waypoint has TotalDistance = 11,513,367 meters
            >>> _get_last_total_distance(vehicle)
            11513367

            >>> # Vehicle has no waypoints yet
            >>> _get_last_total_distance(new_vehicle)
            None
        """
        Journey = self.env['bm.fleet.transportation.journey']

        # Find the most recent waypoint for this vehicle (optimized: only fetch api_data field)
        result = Journey.search_read(
            domain=[('vehicle_id', '=', vehicle.id)],
            fields=['api_data'],
            order='timestamp DESC',
            limit=1
        )

        if not result:
            return None

        # Parse api_data to extract TotalDistance
        try:
            import ast
            api_data = ast.literal_eval(result[0]['api_data'])
            total_distance = api_data.get('TotalDistance')

            if total_distance is not None:
                _logger.info(
                    f"Resume sync for {vehicle.name}: "
                    f"Last TotalDistance = {total_distance} m ({total_distance / 1000:.2f} km)"
                )
                return total_distance
            else:
                _logger.warning(
                    f"Last waypoint for {vehicle.name} has no TotalDistance in api_data"
                )
                return None

        except (ValueError, SyntaxError, AttributeError) as e:
            _logger.warning(
                f"Failed to parse api_data for {vehicle.name}: {e}"
            )
            return None

    def _process_trip_waypoints(self, vehicle, trip_list, batch_size=None):
        """Process GPS trip waypoints with batch processing

        Creates waypoint records in bm.fleet.transportation.journey from API trip data.
        Uses batch processing for efficiency and prevents duplicates.

        IMPORTANT: Maintains continuous distance calculation across sync sessions.
        Retrieves the last waypoint's TotalDistance from the database to ensure
        incremental distance calculation continues from where the previous sync left off,
        rather than treating each sync as a fresh start (which would store full lifetime
        TotalDistance for the first waypoint of each sync).

        Args:
            vehicle: fleet.vehicle record
            trip_list: List of trip data from ADSUN GetDeviceTripBySerial API
            batch_size: Number of records to process per batch (None = use config)

        Returns:
            dict: Statistics with keys 'created', 'skipped', 'total'
        """
        if not trip_list:
            _logger.info(f"No trip data to process for {vehicle.name}")
            return {'created': 0, 'skipped': 0, 'total': 0}
        
        # Get batch size from config if not provided
        if batch_size is None:
            batch_size = int(self.env['ir.config_parameter'].sudo().get_param(
                'bm_fleet_gps.sync_batch_size', default=100
            ))
        
        Journey = self.env['bm.fleet.transportation.journey']
        total_created = 0
        total_skipped = 0
        total_trips = len(trip_list)
        
        _logger.info(f"Starting GPS sync for {vehicle.name}: {total_trips} waypoints (batch: {batch_size})")

        # Initialize with last known TotalDistance to ensure continuous incremental calculation
        # across multiple sync sessions (each cron run doesn't start from zero)
        previous_total_distance = self._get_last_total_distance(vehicle)
        
        # Process in batches
        for offset in range(0, total_trips, batch_size):
            batch = trip_list[offset:offset + batch_size]
            waypoints_to_create = []

            _logger.info(f"Processing batch {offset // batch_size + 1}: records {offset + 1}-{min(offset + batch_size, total_trips)}")

            # Prepare waypoint data for each trip in batch
            # No need to pre-check duplicates - SQL INSERT ON CONFLICT handles it
            for trip in batch:
                waypoint_data, previous_total_distance = self._prepare_waypoint_data(
                    vehicle, trip, previous_total_distance
                )

                if waypoint_data:
                    waypoints_to_create.append(waypoint_data)

            # Bulk create waypoints - SQL handles duplicates automatically
            batch_created = self._bulk_create_waypoints(Journey, waypoints_to_create)
            batch_skipped = len(waypoints_to_create) - batch_created

            total_created += batch_created
            total_skipped += batch_skipped

        _logger.info(f"GPS sync completed for {vehicle.name}: {total_created} created, {total_skipped} skipped")
        
        # Update vehicle last sync timestamp
        self._update_vehicle_last_sync(vehicle, trip_list)
        
        return {
            'created': total_created,
            'skipped': total_skipped,
            'total': total_trips
        }

    # ========== Action Methods ==========

    def action_sync_today_waypoints(self):
        """Manual action: Sync today's GPS waypoints (00:00:00 to 23:59:59)"""
        self.ensure_one()

        if not self.adsun_device_serial_number:
            raise UserError(_("Please configure GPS device serial number first!"))

        try:
            # Sync today's GPS waypoints
            result = self.sync_gps_waypoints_today()

            if result['success']:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('GPS Sync Completed'),
                        'message': _(
                            'Successfully synced today\'s GPS data:\n'
                            '• Created: %d waypoints\n'
                            '• Skipped: %d duplicates\n'
                            '• Total: %d points'
                        ) % (result['created'], result['skipped'], result['total']),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                raise UserError(_("Failed to sync GPS data. Check logs for details."))

        except Exception as e:
            _logger.error(f"GPS sync failed for {self.name}: {e}")
            raise UserError(_("GPS sync failed: %s") % str(e))

    def action_view_transportation_journeys(self):
        """Open transportation journeys (GPS waypoints) for this vehicle

        Shows all GPS waypoints/journeys for the selected vehicle.
        """
        self.ensure_one()

        return {
            'name': _('Hành trình - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'bm.fleet.transportation.journey',
            'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {
                'default_vehicle_id': self.id,
                'search_default_vehicle_id': self.id,
            }
        }

    def action_open_service_booking_wizard(self):
        """Override default service_count button action

        Instead of opening list/kanban of bookings, open booking wizard directly.
        This provides better UX for creating new bookings from vehicle form.
        """
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Đăng ký đặt xe'),
            'res_model': 'bm.fleet.service.booking.wizard',
            'view_mode': 'form',
            'target': 'new',
            'views': [(self.env.ref('bm_fleet_gps.view_fleet_service_booking_wizard_form').id, 'form')],
            'context': {
                'default_vehicle_id': self.id,
            }
        }