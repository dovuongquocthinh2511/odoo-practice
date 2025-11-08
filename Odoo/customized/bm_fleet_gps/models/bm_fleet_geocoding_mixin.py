# -*- coding: utf-8 -*-

import requests
import logging
import time
from odoo import models

_logger = logging.getLogger(__name__)


class GeocodingMixin(models.AbstractModel):
    """Mixin for geocoding functionality - converts coordinates to addresses

    Provides two geocoding methods:
    1. ADSUN Geocoding API (primary, Vietnam-specific)
    2. OpenStreetMap Nominatim (fallback, global coverage)

    Inherits from ApiConfigMixin for centralized API configuration.
    """
    _name = 'bm.fleet.geocoding.mixin'
    _inherit = ['bm.fleet.api.config.mixin']
    _description = 'Geocoding Mixin for GPS Coordinates'

    def geocode_coordinates(self, lat, lng, use_openstreetmap_fallback=True):
        """Geocode coordinates to address

        Args:
            lat (float): Latitude
            lng (float): Longitude
            use_openstreetmap_fallback (bool): Use OSM if ADSUN fails

        Returns:
            str: Address or empty string if failed
        """
        if not (lat and lng):
            return ''

        # Try ADSUN first (Vietnam-specific, faster)
        address = self._fetch_from_adsun_geocode(lat, lng)

        # Fallback to OpenStreetMap if ADSUN fails
        if not address and use_openstreetmap_fallback:
            address = self._fetch_from_openstreetmap(lat, lng)

        return address or ''

    def _fetch_from_adsun_geocode(self, lat, lng):
        """Fetch address from ADSUN Geocode API

        Uses centralized API configuration via _get_ssl_verify() mixin method.

        Args:
            lat (float): Latitude
            lng (float): Longitude

        Returns:
            str: Address or None if failed
        """
        try:
            # Get SSL verification setting from centralized config helper
            ssl_verify = self._get_ssl_verify()

            url = "https://geocode.adsun.vn/Geocode/GetAddress"
            params = {'lat': lat, 'lng': lng}

            response = requests.get(url, params=params, verify=ssl_verify)

            if response.status_code == 200:
                data = response.json()
                address = data.get('Address')
                if address:
                    _logger.debug(f"ADSUN Geocode: Found address for ({lat}, {lng})")
                    return address
                else:
                    _logger.debug(f"ADSUN Geocode: No address for ({lat}, {lng})")
            else:
                _logger.warning(f"ADSUN Geocode API error: {response.status_code}")

        except requests.RequestException as e:
            _logger.warning(f"ADSUN Geocode request failed: {e}")
        except Exception as e:
            _logger.error(f"ADSUN Geocode unexpected error: {e}")

        return None

    def _fetch_from_openstreetmap(self, lat, lng):
        """Fetch address from OpenStreetMap Nominatim API

        Uses OpenStreetMap's free reverse geocoding service.
        Respects rate limit: 1 request/second

        Args:
            lat (float): Latitude
            lng (float): Longitude

        Returns:
            str: Address or None if failed
        """
        try:
            url = "https://nominatim.openstreetmap.org/reverse"
            params = {
                'lat': lat,
                'lon': lng,
                'format': 'json',
                'addressdetails': 1,
                'accept-language': 'vi'  # Vietnamese preference
            }

            headers = {
                'User-Agent': 'Odoo Fleet GPS Module/1.0 (Contact: admin@example.com)'
            }

            # Respect rate limit: 1 request/second
            time.sleep(1.1)

            response = requests.get(url, params=params, headers=headers)

            if response.status_code == 200:
                data = response.json()

                # Build address from components
                address_parts = []
                addr = data.get('address', {})

                # Add road/street
                road = addr.get('road') or addr.get('street')
                if road:
                    address_parts.append(road)

                # Add suburb/neighbourhood
                suburb = addr.get('suburb') or addr.get('neighbourhood') or addr.get('quarter')
                if suburb:
                    address_parts.append(suburb)

                # Add city/town
                city = addr.get('city') or addr.get('town') or addr.get('village')
                if city:
                    address_parts.append(city)

                # Add state/province
                state = addr.get('state') or addr.get('province')
                if state:
                    address_parts.append(state)

                # Add country
                country = addr.get('country')
                if country:
                    address_parts.append(country)

                if address_parts:
                    address = ', '.join(address_parts)
                    _logger.debug(f"OpenStreetMap: Found address for ({lat}, {lng})")
                    return address
                else:
                    # Fallback to display_name
                    display_name = data.get('display_name')
                    if display_name:
                        _logger.debug(f"OpenStreetMap: Using display_name for ({lat}, {lng})")
                        return display_name

            elif response.status_code == 429:
                _logger.warning(f"OpenStreetMap rate limit exceeded for ({lat}, {lng})")
            else:
                _logger.warning(f"OpenStreetMap API error: {response.status_code}")

        except requests.RequestException as e:
            _logger.warning(f"OpenStreetMap request failed: {e}")
        except Exception as e:
            _logger.error(f"OpenStreetMap unexpected error: {e}")

        return None
