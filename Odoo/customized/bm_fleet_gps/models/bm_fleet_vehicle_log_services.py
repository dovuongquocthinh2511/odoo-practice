# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from markupsafe import Markup

from ..utils import notification_helper, validation_helper

# Constants
READONLY_STATES = {
    'new': [('readonly', False)],
    'pending_manager': [('readonly', True)],
    'pending_dispatch': [('readonly', True)],
    'running': [('readonly', True)],
    'done': [('readonly', True)],
    'cancelled': [('readonly', True)]
}


class FleetVehicleLogServices(models.Model):
    _name = 'fleet.vehicle.log.services'
    _inherit = ['fleet.vehicle.log.services']

    def _setup_fields(self):
        """Override vehicle_id to be optional"""
        super(FleetVehicleLogServices, self)._setup_fields()
        if 'vehicle_id' in self._fields:
            self._fields['vehicle_id'].required = False
            self._fields['vehicle_id'].store = True
            self._fields['vehicle_id'].check_company = False

    def _check_required_fields(self, vals):
        """Bypass vehicle_id validation during workflow transitions"""
        if 'vehicle_id' in vals or (not vals.get('vehicle_id') and hasattr(self, 'vehicle_id')):
            vals_copy = dict(vals)
            vehicle_field = self._fields.get('vehicle_id')
            if vehicle_field:
                original_required = vehicle_field.required
                vehicle_field.required = False
                try:
                    return super(FleetVehicleLogServices, self)._check_required_fields(vals_copy)
                finally:
                    vehicle_field.required = original_required
        return super(FleetVehicleLogServices, self)._check_required_fields(vals)

    name = fields.Char(
        string='Mã đặt xe',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New'),
        help='Mã tham chiếu duy nhất cho đơn đặt xe'
    )

    @api.depends('name')
    def _compute_display_name(self):
        """Override display_name to show booking code"""
        for record in self:
            record.display_name = record.name if record.name else _('New')

    def _validate_required_fields(self, field_map):
        """Validate required fields and return list of missing field names

        Args:
            field_map: dict mapping field names to display names

        Returns:
            list of missing field display names
        """
        return validation_helper.validate_required_fields(self, field_map)

    def _show_validation_error(self, missing_fields):
        """Show validation error notification

        Args:
            missing_fields: list of missing field display names

        Returns:
            dict: notification action
        """
        return notification_helper.show_validation_error(missing_fields)

    def _open_rejection_wizard(self):
        """Open rejection wizard for current record

        Returns:
            dict: wizard action
        """
        self.ensure_one()
        return {
            'name': _('Nhập lý do từ chối'),
            'type': 'ir.actions.act_window',
            'res_model': 'bm.fleet.service.rejection.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_request_id': self.id,
            }
        }

    def _reject_with_state_check(self, expected_state, state_display_name):
        """Generic rejection with state validation

        Helper method to reduce duplication between manager and dispatch rejection actions.

        Args:
            expected_state: Expected state for rejection
            state_display_name: Translated state name for error message

        Returns:
            dict: Rejection wizard action

        Raises:
            UserError: If record is not in expected state
        """
        for record in self:
            if record.state != expected_state:
                raise UserError(
                    _('Chỉ có thể từ chối khi ở trạng thái %s') % state_display_name
                )
            return record._open_rejection_wizard()

    def _get_default_manager(self, team_id=None, user_manager_id=None):
        """Get default manager with priority order

        Args:
            team_id: Team ID to get manager from
            user_manager_id: User-selected manager ID

        Returns:
            int: Manager user ID or False if not found

        Priority:
            1. User-selected manager (user_manager_id parameter)
            2. Team manager
            3. Any user with fleet manager role
        """
        if user_manager_id:
            return user_manager_id

        if team_id:
            team = self.env['bm.fleet.team'].browse(team_id)
            if team and team.manager_id:
                return team.manager_id.id

        # Fallback: Get any manager from bm.fleet.request.user records
        manager_rec = self.env['bm.fleet.request.user'].search([], limit=1)
        return manager_rec.manager_id.id if manager_rec else False

    def _check_state_transition(self, expected_state, error_message):
        """Validate state before transition

        Args:
            expected_state: Expected current state
            error_message: Error message if validation fails

        Raises:
            UserError: If record not in expected state
        """
        for record in self:
            if record.state != expected_state:
                raise UserError(_(error_message))

    def _check_user_permission(self, group_xmlid, error_message):
        """Check if user has required permission

        Base Admin (base.group_system) always has permission to bypass workflow checks.

        Args:
            group_xmlid: XML ID of required group (e.g., 'bm_fleet_gps.group_bm_fleet_sale_admin')
            error_message: Error message if permission denied

        Raises:
            UserError: If user lacks permission
        """
        # Base Admin can perform all workflow actions
        if self.env.user.has_group('base.group_system'):
            return

        if not self.env.user.has_group(group_xmlid):
            raise UserError(_(error_message))

    def _manage_activity(self, action='unlink', user_id=None, summary=None):
        """Manage activity lifecycle

        Args:
            action: 'unlink' or 'schedule'
            user_id: User ID for scheduled activity
            summary: Activity summary text
        """
        for record in self:
            if action == 'unlink':
                record.activity_unlink(['mail.mail_activity_data_todo'])
            elif action == 'schedule' and user_id and summary:
                record.activity_schedule('mail.mail_activity_data_todo',
                                       user_id=user_id,
                                       summary=summary)

    def _write_with_workflow_context(self, vals):
        """Write values with workflow context flag

        Args:
            vals: Dictionary of field values to write
        """
        return self.with_context(from_action_method=True).write(vals)

    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Xe',
        required=False,
        store=True,
        help='Xe được phân công cho dịch vụ này',
        tracking=False,
        check_company=False,
        states={'done': [('readonly', True)], 'cancelled': [('readonly', True)]}
    )

    service_type_id = fields.Many2one(
        'fleet.service.type',
        string='Loại dịch vụ chính',
        required=False,
        tracking=True
    )

    service_category = fields.Selection([
        ('work', 'Dịch vụ công tác'),
    ], string='Dịch vụ', default='work', required=True, readonly=True, tracking=True)

    work_location = fields.Char(
        string='Địa điểm công tác',
        size=512,
        states=READONLY_STATES,
        tracking=True
    )

    work_location_latitude = fields.Float(
        string='Vĩ độ (Latitude)',
        digits=(10, 7),
        help='Vĩ độ của địa điểm công tác từ bản đồ',
        states=READONLY_STATES
    )

    work_location_longitude = fields.Float(
        string='Kinh độ (Longitude)',
        digits=(10, 7),
        help='Kinh độ của địa điểm công tác từ bản đồ',
        states=READONLY_STATES
    )

    work_purpose = fields.Text(
        string='Mục đích công tác',
        states=READONLY_STATES,
        tracking=True
    )

    work_date_start = fields.Datetime(
        string='Ngày giờ bắt đầu công tác',
        states=READONLY_STATES,
        tracking=True
    )

    work_date_end = fields.Datetime(
        string='Ngày giờ kết thúc dự kiến',
        states=READONLY_STATES,
        tracking=True
    )

    work_departure_location = fields.Char(
        string='Địa điểm đi',
        size=512,
        states=READONLY_STATES,
        tracking=True
    )

    work_departure_latitude = fields.Float(
        string='Vĩ độ điểm đi',
        digits=(10, 7),
        states=READONLY_STATES
    )

    work_departure_longitude = fields.Float(
        string='Kinh độ điểm đi',
        digits=(10, 7),
        states=READONLY_STATES
    )

    team_id = fields.Many2one(
        'bm.fleet.team',
        string='Team yêu cầu',
        states=READONLY_STATES
    )

    user_ids = fields.Many2many(
        'res.users',
        'fleet_service_user_rel',
        'service_id',
        'user_id',
        string='Người đi công tác',
        states=READONLY_STATES
    )

    manager_id = fields.Many2one(
        'res.users',
        string='Người phê duyệt',
        tracking=True,
        related=False,
        store=True,
        states=READONLY_STATES,
        help='Người sẽ phê duyệt đơn đặt xe này'
    )

    date = fields.Datetime(
        string='Ngày xe khởi hành',
        help='Ngày và giờ xe khởi hành',
        tracking=True,
        states={'done': [('readonly', True)], 'cancelled': [('readonly', True)]}
    )

    date_arrival = fields.Datetime(
        string='Ngày xe đến',
        help='Ngày và giờ xe trở về',
        tracking=True,
        states={'done': [('readonly', True)], 'cancelled': [('readonly', True)]}
    )

    driver_id = fields.Many2one(
        'res.partner',
        string='Tài xế',
        domain=[('is_company', '=', False)],
        states={'done': [('readonly', True)], 'cancelled': [('readonly', True)]},
        tracking=True
    )

    manager_approval_date = fields.Datetime(string='Ngày phê duyệt', readonly=True)
    dispatched_by = fields.Many2one('res.users', string='Người điều xe', readonly=True)
    admin_approval_date = fields.Datetime(string='Ngày điều xe', readonly=True)
    rejection_reason = fields.Text(string='Lý do từ chối', readonly=True)
    rejected_by = fields.Many2one('res.users', string='Người từ chối', readonly=True)
    rejection_date = fields.Datetime(string='Ngày từ chối', readonly=True)

    submitted_by = fields.Many2one(
        'res.users',
        string='Người đặt xe',
        readonly=True,
        help='Người tạo đơn đăng ký đặt xe'
    )

    submission_date = fields.Datetime(
        string='Ngày đặt xe',
        readonly=True,
        help='Ngày giờ tạo đơn đăng ký đặt xe'
    )

    state = fields.Selection([
        ('new', 'Mới'),
        ('pending_manager', 'Quản lý phê duyệt'),
        ('pending_dispatch', 'Đợi điều xe'),
        ('running', 'Đang chạy'),
        ('done', 'Hoàn thành'),
        ('cancelled', 'Hủy phê duyệt'),
    ], default='new', string='Trạng thái', tracking=True, group_expand='_expand_states')

    transportation_journey_count = fields.Integer(
        string='Số điểm hành trình',
        compute='_compute_transportation_journey_count',
        help='Number of GPS waypoints for the dispatched vehicle'
    )

    def _expand_states(self, values, domain):
        """Expand states for Kanban view"""
        return [key for key, val in self._fields['state'].selection]

    @api.depends('vehicle_id', 'date', 'date_arrival')
    def _compute_transportation_journey_count(self):
        """Count transportation journey waypoints for the dispatched vehicle

        Counts waypoints within the booking date range if dates are set.
        Otherwise counts all waypoints for the vehicle.
        """
        for record in self:
            if not record.vehicle_id:
                record.transportation_journey_count = 0
                continue

            # Build domain with date filtering
            domain = [('vehicle_id', '=', record.vehicle_id.id)]

            if record.date and record.date_arrival:
                # Count only waypoints within booking period
                domain += [
                    ('timestamp', '>=', record.date),
                    ('timestamp', '<=', record.date_arrival)
                ]
            elif record.date:
                # Count from departure date onwards
                domain += [('timestamp', '>=', record.date)]

            record.transportation_journey_count = self.env['bm.fleet.transportation.journey'].search_count(domain)

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        """Auto-fill driver from selected vehicle"""
        if self.vehicle_id and self.vehicle_id.driver_id and not self.driver_id:
            self.driver_id = self.vehicle_id.driver_id

    @api.constrains('vehicle_id', 'state')
    def _check_vehicle_required(self):
        """Vehicle is required only when service is running or done"""
        for record in self:
            if record.state in ['running', 'done'] and not record.vehicle_id:
                raise UserError(_('Xe là bắt buộc khi dịch vụ đang chạy hoặc hoàn thành'))
        return True

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-generate booking reference code and populate booking person info"""
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') in ['New', _('New'), 'Mới']:
                vals['name'] = self.env['ir.sequence'].next_by_code('fleet.vehicle.log.services') or _('New')

            if 'submitted_by' not in vals:
                vals['submitted_by'] = self.env.user.id
            if 'submission_date' not in vals:
                vals['submission_date'] = fields.Datetime.now()

        return super(FleetVehicleLogServices, self).create(vals_list)

    def write(self, vals):
        """Prevent users from changing state/protected fields directly - only Base Admin can bypass"""
        # Base Admin can edit all fields at any time
        is_base_admin = self.env.user.has_group('base.group_system')
        from_action_method = self.env.context.get('from_action_method')

        # State change restriction (only Base Admin can drag/drop)
        if 'state' in vals and not from_action_method and not is_base_admin:
            raise UserError(_('Không thể thay đổi trạng thái trực tiếp. Vui lòng sử dụng các nút phê duyệt trong form view.'))

        # Protected field restrictions (approval/dispatch fields) - only enforce for non-Base-Admin
        if not is_base_admin and not from_action_method:
            readonly_fields = {
                'manager_id', 'manager_approval_date',
                'vehicle_id', 'driver_id', 'date', 'date_arrival',
                'dispatched_by', 'admin_approval_date'
            }

            # Check if user is trying to write to protected fields on existing records
            restricted_fields = set(vals.keys()) & readonly_fields
            if restricted_fields and self.filtered(lambda r: r.id):
                # Sale Admin can edit dispatch fields
                dispatch_fields = {'vehicle_id', 'driver_id', 'date', 'date_arrival'}
                if restricted_fields & dispatch_fields and not self.env.user.has_group('bm_fleet_gps.group_bm_fleet_sale_admin'):
                    raise UserError(_('Bạn không có quyền thay đổi thông tin điều xe'))

        # Auto-populate dispatch info when Sale Admin assigns vehicle/driver
        for record in self:
            if record.state == 'pending_dispatch' and not record.dispatched_by:
                if ('vehicle_id' in vals and vals['vehicle_id']) or ('driver_id' in vals and vals['driver_id']):
                    vals['dispatched_by'] = self.env.user.id
                    vals['admin_approval_date'] = fields.Datetime.now()

        if from_action_method:
            return super(FleetVehicleLogServices, self.with_context(__no_check_required_fields=True)).write(vals)
        return super(FleetVehicleLogServices, self).write(vals)

    def action_submit(self):
        """Submit service for manager approval"""
        self._check_state_transition('new', 'Chỉ có thể gửi phê duyệt khi ở trạng thái Mới')

        for record in self:
            required_fields = {
                'work_departure_location': 'Địa điểm đi',
                'work_location': 'Địa điểm đến',
                'work_purpose': 'Mục đích công tác',
                'work_date_start': 'Ngày giờ bắt đầu công tác',
                'work_date_end': 'Ngày giờ kết thúc dự kiến',
                'team_id': 'Team yêu cầu',
                'user_ids': 'Người đi công tác'
            }

            missing_fields = record._validate_required_fields(required_fields)
            if missing_fields:
                return record._show_validation_error(missing_fields)

            record._write_with_workflow_context({'state': 'pending_manager'})

            if record.manager_id:
                summary_parts = []
                if record.service_type_id and record.service_type_id.name:
                    summary_parts.append(record.service_type_id.name)
                if record.description:
                    summary_parts.append(record.description)
                activity_summary = f'Phê duyệt dịch vụ: {" - ".join(summary_parts) if summary_parts else "Dịch vụ mới"}'
                record._manage_activity('schedule', user_id=record.manager_id.id, summary=activity_summary)
        return True

    def action_manager_approve(self):
        """Manager approves the service

        Permission: Only the assigned manager or Base Admin can approve.
        Special behavior for Base Admin: Always updates manager_id to Base Admin user
        regardless of existing manager assignment.
        """
        self._check_state_transition('pending_manager', 'Chỉ có thể phê duyệt khi ở trạng thái Quản lý phê duyệt')

        # Check if user is the assigned manager or Base Admin
        for record in self:
            if not (self.env.user == record.manager_id or self.env.user.has_group('base.group_system')):
                raise UserError(_('Bạn không có quyền phê duyệt'))

        for record in self:
            write_vals = {'state': 'pending_dispatch', 'manager_approval_date': fields.Datetime.now()}

            # Base Admin approval: always update manager_id to Base Admin user
            if self.env.user.has_group('base.group_system'):
                write_vals['manager_id'] = self.env.user.id
            # Regular manager: only set if empty
            elif not record.manager_id:
                write_vals['manager_id'] = self.env.user.id

            record._write_with_workflow_context(write_vals)
            record._manage_activity('unlink')

            admin_user = record.manager_id if record.manager_id else self.env.user
            summary = f'Điều xe cho dịch vụ: {record.service_type_id.name or record.description}'
            record._manage_activity('schedule', user_id=admin_user.id, summary=summary)
        return True

    def action_manager_reject(self):
        """Manager rejects - open rejection wizard"""
        return self._reject_with_state_check('pending_manager', _('Quản lý phê duyệt'))

    def action_dispatch_approve(self):
        """Sale Admin dispatch vehicle"""
        self._check_state_transition('pending_dispatch', 'Chỉ có thể điều xe khi ở trạng thái Đợi điều xe')
        self._check_user_permission('bm_fleet_gps.group_bm_fleet_sale_admin', 'Bạn không có quyền điều xe')

        for record in self:
            required_fields = {
                'vehicle_id': 'Xe',
                'driver_id': 'Tài xế',
                'date': 'Ngày xe khởi hành',
                'date_arrival': 'Ngày xe đến'
            }

            missing_fields = record._validate_required_fields(required_fields)
            if missing_fields:
                return record._show_validation_error(missing_fields)

            write_vals = {'state': 'running'}
            if not record.dispatched_by:
                write_vals['dispatched_by'] = self.env.user.id
                write_vals['admin_approval_date'] = fields.Datetime.now()

            record._write_with_workflow_context(write_vals)
            record._manage_activity('unlink')
        return True

    def action_dispatch_reject(self):
        """Admin rejects - open rejection wizard"""
        return self._reject_with_state_check('pending_dispatch', _('Đợi điều xe'))

    def action_set_to_done(self):
        """Mark service as done - Only Sale Admin can complete bookings"""
        self._check_state_transition('running', 'Chỉ có thể hoàn thành khi ở trạng thái Đang chạy')
        self._check_user_permission('bm_fleet_gps.group_bm_fleet_sale_admin', 'Bạn không có quyền hoàn thành đơn đặt xe')

        for record in self:
            record._write_with_workflow_context({'state': 'done'})
        return True

    def action_reset_to_new(self):
        """Reset to new state

        Permission: Users can reset their own bookings, managers can reset their team's bookings
        """
        for record in self:
            # Base Admin or assigned manager can reset any booking
            # Regular users can only reset their own bookings
            is_manager_or_admin = (self.env.user == record.manager_id or self.env.user.has_group('base.group_system'))
            if not is_manager_or_admin:
                if record.create_uid != self.env.user:
                    raise UserError(_('Bạn chỉ được phép reset đơn đặt xe do bạn tạo'))

            record._write_with_workflow_context({
                'state': 'new',
                'manager_approval_date': False,
                'admin_approval_date': False,
                'rejection_reason': False,
                'rejected_by': False,
                'rejection_date': False,
            })
            record._manage_activity('unlink')
        return True

    def _get_vehicle_for_journey(self):
        """Get the vehicle record for journey display

        Returns:
            fleet.vehicle: The vehicle assigned to this booking
        """
        return self.vehicle_id

    def action_view_transportation_journeys(self):
        """Open transportation journeys with date range filtering

        Shows waypoints within the booking period (date → date_arrival).
        If no dates set, shows all waypoints for the vehicle.
        """
        self.ensure_one()
        vehicle = self._get_vehicle_for_journey()

        if not vehicle:
            raise UserError(_('Chưa có xe được điều cho đơn đặt xe này'))

        # Build domain with date filtering if dates are set
        domain = [('vehicle_id', '=', vehicle.id)]

        if self.date and self.date_arrival:
            # Filter waypoints within the booking date range
            domain += [
                ('timestamp', '>=', self.date),
                ('timestamp', '<=', self.date_arrival)
            ]
        elif self.date:
            # If only departure date, filter from that date onwards
            domain += [('timestamp', '>=', self.date)]

        # Build title with date range
        if self.date and self.date_arrival:
            title = _('Hành trình - %s (%s → %s)') % (
                vehicle.name,
                self.date.strftime('%d/%m/%Y %H:%M'),
                self.date_arrival.strftime('%d/%m/%Y %H:%M')
            )
        elif self.date:
            title = _('Hành trình - %s (từ %s)') % (
                vehicle.name,
                self.date.strftime('%d/%m/%Y %H:%M')
            )
        else:
            title = _('Hành trình - %s') % vehicle.name

        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'res_model': 'bm.fleet.transportation.journey',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {
                'default_vehicle_id': vehicle.id,
                'search_default_vehicle_id': vehicle.id,
            }
        }

    def action_view_journey_map(self):
        """Open map view to display route for the dispatched vehicle

        Shows route on map for the booking period (date → date_arrival).
        If no waypoints in range, map will show latest vehicle location.
        """
        self.ensure_one()

        if not self.vehicle_id:
            raise UserError(_('Chưa có xe được điều cho đơn đặt xe này'))

        context = {
            'default_vehicle_id': self.vehicle_id.id,
            'search_default_vehicle_id': self.vehicle_id.id,
            'fleet_journey_vehicle_filter': self.vehicle_id.id,
        }

        # Add date range to context for map filtering
        # Convert to user's timezone for display (avoids UTC confusion)
        if self.date:
            context['fleet_journey_date_from'] = fields.Datetime.context_timestamp(
                self, self.date
            ).isoformat()
        if self.date_arrival:
            context['fleet_journey_date_to'] = fields.Datetime.context_timestamp(
                self, self.date_arrival
            ).isoformat()

        # Build title with date range
        if self.date and self.date_arrival:
            title = _('Tuyến đường - %s (%s → %s)') % (
                self.vehicle_id.name,
                self.date.strftime('%d/%m/%Y %H:%M'),
                self.date_arrival.strftime('%d/%m/%Y %H:%M')
            )
        elif self.date:
            title = _('Tuyến đường - %s (từ %s)') % (
                self.vehicle_id.name,
                self.date.strftime('%d/%m/%Y %H:%M')
            )
        else:
            title = _('Tuyến đường - %s') % self.vehicle_id.name

        return {
            'type': 'ir.actions.client',
            'name': title,
            'tag': 'fleet_journey_map_action',
            'target': 'current',
            'context': context
        }
