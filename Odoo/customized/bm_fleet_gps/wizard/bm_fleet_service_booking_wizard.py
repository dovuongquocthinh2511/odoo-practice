# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from markupsafe import Markup

from ..utils import notification_helper, validation_helper


class FleetServiceBookingWizard(models.TransientModel):
    _name = 'bm.fleet.service.booking.wizard'
    _description = 'Wizard Đăng ký đặt xe'

    service_category = fields.Selection([
        ('work', 'Dịch vụ công tác'),
        ('other', 'Khác'),
    ], string='Phân loại dịch vụ', required=True, default='work')

    work_departure_location = fields.Char(
        string='Địa điểm đi',
        required=True,
        size=512
    )

    work_departure_latitude = fields.Float(
        string='Vĩ độ (điểm đi)',
        digits=(10, 7)
    )

    work_departure_longitude = fields.Float(
        string='Kinh độ (điểm đi)',
        digits=(10, 7)
    )

    work_location = fields.Char(
        string='Địa điểm đến',
        required=True,
        size=512
    )

    work_location_latitude = fields.Float(
        string='Vĩ độ (điểm đến)',
        digits=(10, 7)
    )

    work_location_longitude = fields.Float(
        string='Kinh độ (điểm đến)',
        digits=(10, 7)
    )

    work_purpose = fields.Text(
        string='Mục đích công tác',
        required=True
    )

    work_date_start = fields.Datetime(
        string='Ngày giờ bắt đầu công tác',
        required=True,
        default=fields.Datetime.now
    )

    work_date_end = fields.Datetime(
        string='Ngày giờ kết thúc dự kiến',
        required=True
    )

    team_id = fields.Many2one(
        'bm.fleet.team',
        string='Team yêu cầu',
        required=True,
        help='Team nào yêu cầu đặt xe'
    )

    requester_id = fields.Many2one(
        'res.users',
        string='Người yêu cầu',
        required=True,
        default=lambda self: self.env.user,
        help='Người tạo đơn đặt xe (có thể đặt thay cho người khác)'
    )

    user_ids = fields.Many2many(
        'res.users',
        'fleet_booking_wizard_user_rel',
        'wizard_id',
        'user_id',
        string='Thành viên tham gia',
        default=lambda self: self.env.user,
        help='Các thành viên đi cùng (không bắt buộc phải bao gồm người yêu cầu)'
    )

    description = fields.Text(string='Mô tả chi tiết')
    notes = fields.Text(string='Ghi chú')

    manager_id = fields.Many2one(
        'res.users',
        string='Người phê duyệt',
        required=False,
        help='Người sẽ phê duyệt đơn đặt xe này. Nếu để trống, hệ thống sẽ tự động chọn manager từ cấu hình user.'
    )

    # Computed cached fields to avoid repeated searches
    requester_user_request_id = fields.Many2one(
        comodel_name='bm.fleet.request.user',
        string='Requester Profile',
        compute='_compute_requester_user_request',
        store=True,
        help='Cached request user profile for the requester'
    )

    manager_user_request_id = fields.Many2one(
        comodel_name='bm.fleet.request.user',
        string='Manager Profile',
        compute='_compute_manager_user_request',
        store=True,
        help='Cached request user profile for the manager'
    )

    @api.depends('requester_id')
    def _compute_requester_user_request(self):
        """Compute and cache requester's request user profile"""
        for wizard in self:
            if wizard.requester_id:
                wizard.requester_user_request_id = self.env['bm.fleet.request.user'].search([
                    ('user_id', '=', wizard.requester_id.id),
                    ('active', '=', True)
                ], limit=1)
            else:
                wizard.requester_user_request_id = False

    @api.depends('manager_id')
    def _compute_manager_user_request(self):
        """Compute and cache manager's request user profile"""
        for wizard in self:
            if wizard.manager_id:
                wizard.manager_user_request_id = self.env['bm.fleet.request.user'].search([
                    ('user_id', '=', wizard.manager_id.id),
                    ('active', '=', True)
                ], limit=1)
            else:
                wizard.manager_user_request_id = False

    @api.model
    def default_get(self, fields_list):
        """Auto-assign team_id and manager_id based on requester context

        Team Strategy:
        1. Check bm.fleet.request.user for requester's assigned team → use that team (PRIORITY)
        2. If no profile, find requester's most recent booking with a team → use that team
        3. If no history, find team where requester is the manager → use that team
        4. If none found, leave empty (user must select manually)

        Manager Strategy:
        1. If team_id was auto-assigned, get manager from that team
        2. If no team, find any user with fleet manager role

        IMPORTANT: Uses requester_id (not current user) to support booking on behalf of others
        """
        defaults = super(FleetServiceBookingWizard, self).default_get(fields_list)

        # Get requester_id from defaults (already set to current user by field default)
        # This allows proper logic when admin books on behalf of another user
        requester_id = defaults.get('requester_id', self.env.user.id)

        # OPTIMIZATION: Query once and reuse for both team_id and manager_id
        request_user_rec = self.env['bm.fleet.request.user'].search([
            ('user_id', '=', requester_id),
            ('active', '=', True)
        ], limit=1)

        if 'team_id' in fields_list and not defaults.get('team_id'):
            # PRIORITY: Check requester's request user profile for assigned team
            if request_user_rec and request_user_rec.team_id:
                defaults['team_id'] = request_user_rec.team_id.id
            else:
                # Fallback 1: Check requester's recent booking history
                recent_booking = self.env['fleet.vehicle.log.services'].search([
                    ('submitted_by', '=', requester_id),
                    ('team_id', '!=', False)
                ], order='create_date desc', limit=1)

                if recent_booking and recent_booking.team_id:
                    defaults['team_id'] = recent_booking.team_id.id
                else:
                    # Fallback 2: Check if requester manages a team
                    managed_team = self.env['bm.fleet.team'].search([
                        ('manager_id', '=', requester_id),
                        ('active', '=', True)
                    ], limit=1)

                    if managed_team:
                        defaults['team_id'] = managed_team.id

        # Auto-assign manager_id from requester's request user profile
        # REUSE request_user_rec from above - no need to search again
        if 'manager_id' in fields_list and not defaults.get('manager_id'):
            if request_user_rec and request_user_rec.manager_id:
                defaults['manager_id'] = request_user_rec.manager_id.id

        return defaults

    @api.onchange('requester_id')
    def _onchange_requester_id(self):
        """Auto-update team_id and manager_id when requester changes

        Use case: Admin đặt xe thay cho user khác
        When admin selects a different requester:
        1. Load team and manager from new requester's profile
        2. Fallback to requester's recent booking history if no profile
        3. Clear team/manager if no data found for requester
        """
        if self.requester_id:
            # Find request user profile for new requester
            request_user_rec = self.env['bm.fleet.request.user'].search([
                ('user_id', '=', self.requester_id.id),
                ('active', '=', True)
            ], limit=1)

            if request_user_rec:
                # Update team from requester's profile
                if request_user_rec.team_id:
                    self.team_id = request_user_rec.team_id
                else:
                    self.team_id = False

                # Update manager from requester's profile
                if request_user_rec.manager_id:
                    self.manager_id = request_user_rec.manager_id
                else:
                    self.manager_id = False
            else:
                # Fallback: Check recent booking history of requester
                recent_booking = self.env['fleet.vehicle.log.services'].search([
                    ('submitted_by', '=', self.requester_id.id),
                    ('team_id', '!=', False)
                ], order='create_date desc', limit=1)

                if recent_booking:
                    self.team_id = recent_booking.team_id
                    self.manager_id = recent_booking.manager_id if recent_booking.manager_id else False
                else:
                    # No profile and no history - clear fields
                    self.team_id = False
                    self.manager_id = False
        else:
            # No requester selected - clear fields
            self.team_id = False
            self.manager_id = False

    @api.onchange('team_id')
    def _onchange_team_id(self):
        """Auto-update manager_id when team changes

        When user selects a different team:
        1. Try to get manager from selected team
        2. If team has no manager, get manager from requester's request user profile
        3. Update manager_id field automatically
        """
        if self.team_id:
            service_model = self.env['fleet.vehicle.log.services']
            manager_id = service_model._get_default_manager(
                team_id=self.team_id.id,
                user_manager_id=self.manager_id.id if self.manager_id else None
            )
            if manager_id:
                self.manager_id = manager_id
        else:
            # If no team selected, get manager from requester's request user profile (cached)
            self.manager_id = self.requester_user_request_id.manager_id if self.requester_user_request_id else False

    @api.onchange('work_date_start')
    def _onchange_work_date_start(self):
        """Auto set end datetime to start datetime + 1 day"""
        if self.work_date_start:
            from datetime import timedelta
            self.work_date_end = self.work_date_start + timedelta(days=1)

    def _record_addresses(self):
        """Record departure and destination addresses to history"""
        address_history = self.env['bm.fleet.address.history']

        if self.work_departure_location:
            address_history.record_address_usage({
                'name': self.work_departure_location,
                'latitude': self.work_departure_latitude,
                'longitude': self.work_departure_longitude,
            })

        if self.work_location:
            address_history.record_address_usage({
                'name': self.work_location,
                'latitude': self.work_location_latitude,
                'longitude': self.work_location_longitude,
            })

    def action_create_booking(self):
        """Create booking request from wizard"""
        self.ensure_one()

        required_fields = {
            'requester_id': 'Người yêu cầu',
            'team_id': 'Team yêu cầu',
            'work_departure_location': 'Địa điểm đi',
            'work_location': 'Địa điểm đến',
            'work_purpose': 'Mục đích công tác'
        }
        missing_fields = validation_helper.validate_required_fields(self, required_fields)
        if missing_fields:
            return notification_helper.show_validation_error(missing_fields)

        if self.work_date_end < self.work_date_start:
            return notification_helper.show_notification(
                title='Lỗi thời gian',
                message='Ngày kết thúc phải sau ngày bắt đầu'
            )

        self._record_addresses()

        default_service_type = self.env.ref('bm_fleet_gps.fleet_service_type_booking', raise_if_not_found=False)

        # Get manager from requester's cached request user profile
        # Use cached field instead of searching - avoids repeated database queries
        manager_id = self.manager_id.id if self.manager_id else (
            self.requester_user_request_id.manager_id.id if self.requester_user_request_id and self.requester_user_request_id.manager_id else False
        )

        service_vals = {
            'service_category': self.service_category,
            'service_type_id': default_service_type.id if default_service_type else False,
            'submitted_by': self.requester_id.id,
            'work_departure_location': self.work_departure_location,
            'work_departure_latitude': self.work_departure_latitude,
            'work_departure_longitude': self.work_departure_longitude,
            'work_location': self.work_location,
            'work_location_latitude': self.work_location_latitude,
            'work_location_longitude': self.work_location_longitude,
            'work_purpose': self.work_purpose,
            'work_date_start': self.work_date_start,
            'work_date_end': self.work_date_end,
            'date': self.work_date_start,
            'team_id': self.team_id.id,
            'user_ids': [(6, 0, self.user_ids.ids)] if self.user_ids else False,
            'description': self.description or self.work_purpose,
            'notes': self.notes,
            'manager_id': manager_id,
            # dispatched_by will be auto-filled when Sale Admin actually dispatches the vehicle
            'state': 'new',
        }

        service = self.env['fleet.vehicle.log.services'].create(service_vals)

        return {
            'name': _('Đơn đặt xe'),
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.vehicle.log.services',
            'res_id': service.id,
            'view_mode': 'form',
            'target': 'current',
        }
