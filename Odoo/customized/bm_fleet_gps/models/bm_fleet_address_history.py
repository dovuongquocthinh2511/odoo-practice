# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import requests
import logging

_logger = logging.getLogger(__name__)


class FleetAddressHistory(models.Model):
    _name = 'bm.fleet.address.history'
    _description = 'Lịch sử địa chỉ công tác'
    _order = 'usage_count desc, write_date desc'

    name = fields.Char(
        string='Địa chỉ đầy đủ',
        required=True,
        index=True,
        help='Địa chỉ đầy đủ từ OpenStreetMap hoặc do người dùng nhập'
    )

    latitude = fields.Float(
        string='Vĩ độ',
        digits=(10, 7),
        help='Vĩ độ (Latitude) từ OpenStreetMap'
    )

    longitude = fields.Float(
        string='Kinh độ',
        digits=(10, 7),
        help='Kinh độ (Longitude) từ OpenStreetMap'
    )

    usage_count = fields.Integer(
        string='Số lần sử dụng',
        default=1,
        help='Số lần địa chỉ này được sử dụng'
    )

    last_used_date = fields.Datetime(
        string='Lần dùng cuối',
        default=fields.Datetime.now,
        help='Lần cuối cùng địa chỉ này được sử dụng'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company,
        help='Công ty sử dụng địa chỉ này'
    )

    active = fields.Boolean(
        string='Hoạt động',
        default=True,
        help='Bỏ chọn để ẩn địa chỉ khỏi gợi ý'
    )

    _sql_constraints = [
        ('name_company_unique',
         'UNIQUE(name, company_id)',
         'Địa chỉ này đã tồn tại trong hệ thống!')
    ]

    @api.model
    def record_address_usage(self, address_data):
        """
        Ghi lại việc sử dụng địa chỉ

        :param address_data: dict với keys: name, latitude, longitude
        :return: địa chỉ record đã tạo/cập nhật, hoặc empty recordset nếu thiếu name
        """
        if not address_data.get('name'):
            return self.browse()  # Return empty recordset instead of False

        # Tìm địa chỉ đã tồn tại
        existing = self.search([
            ('name', '=', address_data['name']),
            ('company_id', '=', self.env.company.id)
        ], limit=1)

        if existing:
            # Cập nhật số lần sử dụng và thời gian
            existing.write({
                'usage_count': existing.usage_count + 1,
                'last_used_date': fields.Datetime.now(),
                # Cập nhật tọa độ nếu có (có thể đã thay đổi)
                'latitude': address_data.get('latitude') or existing.latitude,
                'longitude': address_data.get('longitude') or existing.longitude,
            })
            return existing
        else:
            # Tạo mới
            return self.create({
                'name': address_data['name'],
                'latitude': address_data.get('latitude'),
                'longitude': address_data.get('longitude'),
                'usage_count': 1,
                'last_used_date': fields.Datetime.now(),
            })

    @api.model
    def search_address_suggestions(self, query, limit=5):
        """
        Tìm kiếm địa chỉ gợi ý từ lịch sử

        :param query: chuỗi tìm kiếm
        :param limit: số lượng kết quả tối đa
        :return: list of dict [{name, latitude, longitude, usage_count}, ...]
        """
        if not query or len(query) < 2:
            return []

        # Tìm địa chỉ có chứa query (case-insensitive)
        domain = [
            ('name', 'ilike', query),
            ('company_id', '=', self.env.company.id),
            ('active', '=', True)
        ]

        addresses = self.search(domain, limit=limit, order='usage_count desc, write_date desc')

        return [{
            'name': addr.name,
            'latitude': addr.latitude,
            'longitude': addr.longitude,
            'usage_count': addr.usage_count,
            'source': 'history',  # Đánh dấu đây là từ lịch sử
        } for addr in addresses]

    @api.model
    def search_openmap_autocomplete(self, query, limit=5):
        """
        Tìm kiếm địa chỉ từ OpenMap.vn API (backend proxy để bảo mật API key)

        :param query: chuỗi tìm kiếm
        :param limit: số lượng kết quả tối đa
        :return: list of dict [{id, display_name, name}, ...]
        """
        if not query or len(query) < 2:
            return []

        try:
            # Lấy API key từ system parameters (bảo mật)
            api_key = self.env['ir.config_parameter'].sudo().get_param('openmap.api.key')
            if not api_key:
                _logger.warning('OpenMap.vn API key not configured in system parameters')
                return []

            # Call OpenMap.vn autocomplete API
            url = 'https://mapapis.openmap.vn/v1/autocomplete'
            params = {
                'apikey': api_key,
                'text': query,
                'limit': limit
            }

            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()

            data = response.json()

            # Transform response
            results = []
            for feature in data.get('features', []):
                properties = feature.get('properties', {})
                results.append({
                    'id': properties.get('id'),
                    'display_name': properties.get('label') or properties.get('name', ''),
                    'name': properties.get('name', ''),
                    'source': 'openmap'
                })

            return results

        except requests.exceptions.RequestException as e:
            _logger.error(f'OpenMap.vn API error: {str(e)}')
            return []
        except Exception as e:
            _logger.error(f'Unexpected error in OpenMap autocomplete: {str(e)}')
            return []

    @api.model
    def get_openmap_place_detail(self, place_id):
        """
        Lấy chi tiết địa điểm từ OpenMap.vn để có tọa độ

        :param place_id: ID của địa điểm từ autocomplete
        :return: dict {display_name, latitude, longitude} hoặc False
        """
        if not place_id:
            return False

        try:
            # Lấy API key từ system parameters
            api_key = self.env['ir.config_parameter'].sudo().get_param('openmap.api.key')
            if not api_key:
                _logger.warning('OpenMap.vn API key not configured')
                return False

            # Call OpenMap.vn place detail API
            url = 'https://mapapis.openmap.vn/v1/place'
            params = {
                'apikey': api_key,
                'ids': place_id,
                'format': 'google'
            }

            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()

            data = response.json()

            # Extract coordinates from response
            result = data.get('result', {})
            geometry = result.get('geometry', {})
            location = geometry.get('location', {})

            if location.get('lat') and location.get('lng'):
                return {
                    'display_name': result.get('formatted_address', ''),
                    'latitude': location['lat'],
                    'longitude': location['lng'],
                    'source': 'openmap'
                }

            return False

        except requests.exceptions.RequestException as e:
            _logger.error(f'OpenMap.vn place detail API error: {str(e)}')
            return False
        except Exception as e:
            _logger.error(f'Unexpected error in OpenMap place detail: {str(e)}')
            return False
