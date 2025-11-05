# -*- coding: utf-8 -*-

import logging
import json
import requests
from datetime import datetime
from odoo import http
from odoo.http import request
from ..utils.exceptions import AdsunRequestTokenException
from urllib.parse import urlencode

_logger = logging.getLogger(__name__)


class AdsunJourneyController(http.Controller):
    """RPC Controller for ADSUN Journey History API Integration"""

    def _get_headers(self):
        """Get headers for ADSUN API requests"""
        try:
            token_helper = request.env['bm.fleet.adsun.token'].sudo()
            token = token_helper.get_active_token()

            if not token:
                raise AdsunRequestTokenException("No active ADSUN token available")

            return {
                'x-access-token': token,
                'token': token,
                'User-Agent': 'Odoo Fleet GPS Module/1.0',
                'Content-Type': 'application/json'
            }
        except Exception as e:
            _logger.error(f"Failed to get ADSUN headers: {e}")
            raise AdsunRequestTokenException(f"Authentication failed: {str(e)}")

    def _get_adsun_api_config(self):
        """Get ADSUN API configuration using the centralized mixin

        This method bridges the controller to the existing mixin configuration
        system used throughout the module.

        Returns:
            dict: API configuration with url, ssl_verify, timeout
        """
        try:
            # Use the token helper which already has all the configuration
            token_helper = request.env['bm.fleet.adsun.token'].sudo()
            return {
                'url': token_helper.get_api_url(),
                'ssl_verify': token_helper.get_ssl_verify(),
                'timeout': token_helper.get_timeout()
            }
        except Exception as e:
            _logger.error(f"Failed to get ADSUN API config: {e}")
            # Fallback to environment variables if available
            return {
                'url': 'https://systemroute.adsun.vn/api',
                'ssl_verify': True,
                'timeout': 30
            }

    def _transform_waypoint_data(self, api_data):
        """
        Transform ADSUN API response to standardized waypoint format

        Args:
            api_data (dict/list): Raw response from ADSUN API

        Returns:
            list: List of standardized waypoint dictionaries
        """
        waypoints = []

        try:
            if not api_data:
                return waypoints

            # Handle different response formats
            if isinstance(api_data, dict):
                data_list = api_data.get('Data', api_data.get('data', []))
            elif isinstance(api_data, list):
                data_list = api_data
            else:
                _logger.warning(f"Unexpected API response format: {type(api_data)}")
                return waypoints

            _logger.info(f"Processing {len(data_list)} waypoints from ADSUN API")

            for item in data_list:
                if not isinstance(item, dict):
                    continue

                try:
                    # Extract timestamp with multiple field name support
                    timestamp_fields = ['GpsTime', 'GPSTime', 'Timestamp', 'DeviceTime', 'timestamp']
                    timestamp = None
                    for field in timestamp_fields:
                        if field in item and item[field]:
                            timestamp = item[field]
                            break

                    # Extract coordinates with multiple field name support
                    lat_fields = ['Lat', 'Latitude', 'latitude']
                    lng_fields = ['Lng', 'Longitude', 'longitude', 'Long']

                    latitude = None
                    longitude = None

                    for field in lat_fields:
                        if field in item and item[field] is not None:
                            latitude = float(item[field])
                            break

                    for field in lng_fields:
                        if field in item and item[field] is not None:
                            longitude = float(item[field])
                            break

                    if latitude is None or longitude is None:
                        continue

                    # Skip invalid coordinates
                    if abs(latitude) > 90 or abs(longitude) > 180:
                        continue

                    # Create standardized waypoint
                    waypoint = {
                        'latitude': latitude,
                        'longitude': longitude,
                        'timestamp': timestamp or datetime.now().isoformat(),
                        'speed': float(item.get('Speed', 0)),
                        'machine_status': item.get('AccOn', False),
                        'address': item.get('Address', ''),
                        'direction': float(item.get('Direction', 0)),
                        'altitude': float(item.get('Alt', 0)),
                    }
                    if waypoint['latitude'] != 0 and waypoint['longitude'] != 0:
                        waypoints.append(waypoint)

                except (ValueError, TypeError) as e:
                    _logger.warning(f"Skipping invalid waypoint: {e}")
                    continue
                except Exception as e:
                    _logger.error(f"Error processing waypoint: {e}")
                    continue

        except Exception as e:
            _logger.error(f"Error transforming waypoint data: {e}")

        # Sort by timestamp
        waypoints.sort(key=lambda x: x.get('timestamp', ''))

        return waypoints

    @http.route('/fleet/gps/journey/history', type='json', auth='user', methods=['POST'], csrf=False)
    def get_journey_history(self, vehicle_id=None, device_serial=None, start_time=None, end_time=None, **kwargs):
        """
        Get journey history using hybrid approach (database for today, API for historical)

        Args:
            vehicle_id (int): Vehicle ID
            device_serial (str): Device serial number
            start_time (str): Start time in format 'YYYY-MM-DD HH:MM:SS' (Vietnam time)
            end_time (str): End time in format 'YYYY-MM-DD HH:MM:SS' (Vietnam time)

        Returns:
            dict: Response with waypoints from appropriate source
        """
        try:
            _logger.info(f"🔍 Fetching journey history - Vehicle: {vehicle_id}, Device: {device_serial}")
            _logger.info(f"⏰ Time range: {start_time} to {end_time}")

            if not vehicle_id:
                return {
                    'success': False,
                    'error': 'Vehicle ID is required',
                    'waypoints': []
                }

            if not start_time or not end_time:
                return {
                    'success': False,
                    'error': 'Start time and end time are required',
                    'waypoints': []
                }

            # Parse times and check if requesting today's data
            from datetime import datetime, date
            today = date.today()
            is_today_request = start_time.startswith(str(today)) or end_time.startswith(str(today))

            # Get vehicle record
            vehicle_model = request.env['fleet.vehicle'].sudo()
            vehicle = vehicle_model.browse(vehicle_id)

            if not vehicle.exists():
                return {
                    'success': False,
                    'error': f'Vehicle with ID {vehicle_id} not found',
                    'waypoints': []
                }

            if vehicle.adsun_device_serial_number != device_serial:
                _logger.warning(f"Device serial mismatch - Vehicle: {vehicle.adsun_device_serial_number}, Request: {device_serial}")

            # HYBRID LOGIC: Check if today's data exists in database
            if is_today_request:
                try:
                    journey_model = request.env['bm.fleet.transportation.journey'].sudo()

                    # Convert to datetime for database query
                    start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
                    end_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')

                    # Search for waypoints within time range
                    waypoints_db = journey_model.search([
                        ('vehicle_id', '=', vehicle_id),
                        ('timestamp', '>=', start_dt),
                        ('timestamp', '<=', end_dt)
                    ], order='timestamp asc')

                    if waypoints_db:
                        # Convert database waypoints to API format
                        waypoints_data = []
                        for wp in waypoints_db:
                            waypoints_data.append({
                                'latitude': wp.latitude,
                                'longitude': wp.longitude,
                                'timestamp': wp.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                                'speed': wp.speed or 0,
                                'machine_status': wp.machine_status or False,
                                'gps_status': wp.gps_status or False,
                                'address': wp.address or '',
                                'distance': wp.distance or 0,
                                'source': 'database'
                            })

                        _logger.info(f"✅ Retrieved {len(waypoints_data)} waypoints from database for today")
                        return {
                            'success': True,
                            'waypoints': waypoints_data,
                            'source': 'database',
                            'vehicle_id': vehicle_id,
                            'device_serial': device_serial,
                            'time_range': f"{start_time} to {end_time}",
                            'message': f'Loaded {len(waypoints_data)} waypoints from database'
                        }

                except Exception as e:
                    _logger.warning(f"Database query failed, falling back to API: {e}")

            # API CALL: Get data directly from ADSUN API for historical data or as fallback
            try:
                # Convert time strings to datetime objects (Vietnam timezone)
                # The time strings from frontend are already in Vietnam time, no conversion needed
                start_dt_vn = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
                end_dt_vn = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')

                _logger.info(f"🌐 Calling ADSUN API for vehicle {vehicle.name}")

                # Use vehicle model's new method for API calls
                result = vehicle.get_journey_history_from_api(start_dt_vn, end_dt_vn)

                if result['success']:
                    # Add metadata to response
                    result.update({
                        'vehicle_id': vehicle_id,
                        'device_serial': device_serial,
                        'time_range': f"{start_time} to {end_time}",
                        'is_today_request': is_today_request
                    })

                    if result['waypoints']:
                        # Add source indicator to each waypoint
                        for waypoint in result['waypoints']:
                            waypoint['source'] = 'api'

                        _logger.info(f"✅ Retrieved {len(result['waypoints'])} waypoints from ADSUN API")
                    else:
                        _logger.info(f"ℹ️ No waypoints found in API for the specified time range")

                    return result
                else:
                    _logger.error(f"❌ API call failed: {result.get('message', 'Unknown error')}")
                    return {
                        'success': False,
                        'error': result.get('message', 'API call failed'),
                        'waypoints': []
                    }

            except Exception as e:
                _logger.error(f"❌ Exception during API call: {e}")
                return {
                    'success': False,
                    'error': f'Failed to fetch journey history: {str(e)}',
                    'waypoints': []
                }

        except AdsunRequestTokenException as e:
            _logger.error(f"❌ ADSUN authentication error: {e}")
            return {
                'success': False,
                'error': f'Authentication failed: {str(e)}',
                'waypoints': []
            }
        except Exception as e:
            _logger.error(f"❌ Unexpected error in get_journey_history: {e}")
            import traceback
            _logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': f'Server error: {str(e)}',
                'waypoints': []
            }

    @http.route('/fleet/gps/journey/latest-position', type='json', auth='user', methods=['POST'], csrf=False)
    def get_latest_position(self, vehicle_id=None, device_serial=None, **kwargs):
        """
        Get latest position from ADSUN API

        Args:
            vehicle_id (int): Vehicle ID
            device_serial (str): Device serial number

        Returns:
            dict: Latest position data or error
        """
        try:
            _logger.info(f"Fetching latest position for vehicle {vehicle_id}, device {device_serial}")

            if not device_serial:
                _logger.error("Device serial number is required")
                return {
                    'success': False,
                    'error': 'Device serial number is required'
                }

            # Try to get from database first for latest sync
            try:
                journey_model = request.env['bm.fleet.transportation.journey'].sudo()
                latest_journey = journey_model.search([
                    ('vehicle_id.adsun_device_serial', '=', device_serial)
                ], order='end_time desc', limit=1)

                if latest_journey and latest_journey.waypoint_ids:
                    latest_waypoint = latest_journey.waypoint_ids.sorted('timestamp', reverse=True)[0]
                    return {
                        'success': True,
                        'position': {
                            'latitude': latest_waypoint.latitude,
                            'longitude': latest_waypoint.longitude,
                            'timestamp': latest_waypoint.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                            'speed': latest_waypoint.speed,
                            'address': latest_waypoint.address,
                            'source': 'database'
                        },
                        'vehicle_id': vehicle_id,
                        'device_serial': device_serial
                    }
            except Exception as e:
                _logger.warning(f"Database query for latest position failed: {e}")

            # Fallback to API
            config = self._get_adsun_api_config()

            # Get current time for API query
            from datetime import datetime, timedelta
            now = datetime.now()
            start_time = (now - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
            end_time = now.strftime('%Y-%m-%d %H:%M:%S')

            params = {
                'deviceSerial': device_serial,
                'startDate': start_time.split(' ')[0],
                'startTime': start_time.split(' ')[1],
                'endDate': end_time.split(' ')[0],
                'endTime': end_time.split(' ')[1]
            }

            response = requests.get(
                f"{config['url']}/Device/GetDeviceTripBySerial?{urlencode(params)}",
                headers=self._get_headers(),
                verify=config['ssl_verify'],
                timeout=config['timeout']
            )

            if response.status_code == 200:
                api_data = response.json()
                waypoints = self._transform_waypoint_data(api_data)

                if waypoints:
                    latest = waypoints[-1]  # Get the last waypoint
                    return {
                        'success': True,
                        'position': {
                            'latitude': latest['latitude'],
                            'longitude': latest['longitude'],
                            'timestamp': latest['timestamp'],
                            'speed': latest['speed'],
                            'address': latest['address'],
                            'source': 'api'
                        },
                        'vehicle_id': vehicle_id,
                        'device_serial': device_serial
                    }
                else:
                    return {
                        'success': False,
                        'error': 'No position data available'
                    }
            else:
                return {
                    'success': False,
                    'error': f'API request failed: HTTP {response.status_code}'
                }

        except Exception as e:
            _logger.error(f"Error fetching latest position: {e}")
            return {
                'success': False,
                'error': f'Server error: {str(e)}'
            }

    @http.route('/fleet/gps/test-connection', type='json', auth='user', methods=['POST'], csrf=False)
    def test_adsun_connection(self, **kwargs):
        """
        Test ADSUN API connectivity and configuration

        Returns:
            dict: Connection test results with detailed diagnostics
        """
        try:
            _logger.info("🧪 Testing ADSUN API connection...")

            # Test 1: Get API configuration
            try:
                config = self._get_adsun_api_config()
                _logger.info(f"✅ API config loaded: {config['url']}")
            except Exception as e:
                _logger.error(f"❌ API config failed: {e}")
                return {
                    'success': False,
                    'error': f'Configuration error: {str(e)}',
                    'test_stage': 'configuration'
                }

            # Test 2: Get authentication headers
            try:
                headers = self._get_headers()
                _logger.info("✅ Authentication headers obtained")
            except Exception as e:
                _logger.error(f"❌ Authentication failed: {e}")
                return {
                    'success': False,
                    'error': f'Authentication error: {str(e)}',
                    'test_stage': 'authentication'
                }

            # Test 3: Get vehicles with ADSUN devices
            try:
                vehicles = request.env['fleet.vehicle'].sudo().search([
                    ('adsun_device_serial', '!=', False),
                    ('adsun_device_serial', '!=', ''),
                ], limit=3)

                if not vehicles:
                    return {
                        'success': True,
                        'warning': 'No vehicles with ADSUN device serial found',
                        'test_stage': 'no_vehicles',
                        'config': config,
                        'authentication': '✅ Working'
                    }

                test_vehicle = vehicles[0]
                _logger.info(f"✅ Found test vehicle: {test_vehicle.name} ({test_vehicle.adsun_device_serial})")

            except Exception as e:
                _logger.error(f"❌ Vehicle query failed: {e}")
                return {
                    'success': False,
                    'error': f'Database error: {str(e)}',
                    'test_stage': 'database'
                }

            # Test 4: Make actual API call
            try:
                device_serial = test_vehicle.adsun_device_serial
                from datetime import datetime, timedelta
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=1)

                params = {
                    'deviceSerial': device_serial,
                    'startDate': start_time.strftime('%Y-%m-%d'),
                    'startTime': start_time.strftime('%H:%M:%S'),
                    'endDate': end_time.strftime('%Y-%m-%d'),
                    'endTime': end_time.strftime('%H:%M:%S')
                }

                response = requests.get(
                    f"{config['url']}/Device/GetDeviceTripBySerial?{urlencode(params)}",
                    headers=headers,
                    verify=config['ssl_verify'],
                    timeout=config['timeout']
                )

                if response.status_code == 200:
                    data = response.json()
                    waypoints = self._transform_waypoint_data(data)

                    return {
                        'success': True,
                        'message': 'All tests passed successfully',
                        'test_stage': 'completed',
                        'config': config,
                        'authentication': '✅ Working',
                        'vehicle_tested': {
                            'id': test_vehicle.id,
                            'name': test_vehicle.name,
                            'device_serial': device_serial
                        },
                        'api_response': {
                            'status_code': response.status_code,
                            'waypoints_found': len(waypoints),
                            'sample_data': waypoints[0] if waypoints else None
                        }
                    }
                else:
                    return {
                        'success': False,
                        'error': f'API call failed: HTTP {response.status_code}',
                        'test_stage': 'api_call',
                        'response_text': response.text[:500]
                    }

            except requests.exceptions.Timeout:
                _logger.error("❌ Request timeout")
                return {
                    'success': False,
                    'error': 'Request timeout - API server not responding',
                    'test_stage': 'timeout'
                }
            except requests.exceptions.ConnectionError as e:
                _logger.error(f"❌ Connection error: {e}")
                return {
                    'success': False,
                    'error': f'Connection error: {str(e)}',
                    'test_stage': 'connection'
                }
            except Exception as e:
                _logger.error(f"❌ API test failed: {e}")
                return {
                    'success': False,
                    'error': f'API test error: {str(e)}',
                    'test_stage': 'api_test'
                }

        except Exception as e:
            _logger.error(f"💥 Test connection failed: {e}")
            import traceback
            _logger.error(f"💥 Traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': f'Test failed: {str(e)}',
                'test_stage': 'general_error'
            }