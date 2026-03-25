# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class FleetRequestUser(models.Model):
    """
    Fleet Request User - Stores user information for vehicle booking

    Purpose: Simple storage model for user booking workflow information.
    This model only stores data - no UI views, menu items, or complex validations.
    Use Odoo's native Settings > Users & Groups for permission management.

    Fields:
    - user_id: User who books vehicles
    - manager_id: Manager who approves bookings
    - team_id: Department/team the user belongs to
    - sale_admin_id: Sale admin who dispatches vehicles
    """
    _name = 'bm.fleet.request.user'
    _description = 'Fleet Request User - Data Storage Only'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'user_id'
    _order = 'user_id'

    # Core fields per task.txt specification
    user_id = fields.Many2one(
        'res.users',
        string=_('User'),
        required=True,
        ondelete='cascade',
        help='User who will book vehicles'
    )

    manager_id = fields.Many2one(
        'res.users',
        string=_('Manager'),
        required=False,
        ondelete='restrict',
        help='Manager who approves this user\'s bookings'
    )

    team_id = fields.Many2one(
        'bm.fleet.team',
        string=_('Team'),
        required=True,
        ondelete='restrict',
        help='Team the user belongs to'
    )

    sale_admin_id = fields.Many2one(
        'res.users',
        string=_('Sale Admin'),
        required=False,
        ondelete='restrict',
        help='Sale admin who dispatches vehicles for this user\'s bookings'
    )

    # Additional useful fields
    active = fields.Boolean(
        default=True,
        help='Set to false to deactivate this profile without deleting it'
    )

    notes = fields.Text(
        string=_('Notes'),
        help='Additional notes about this user profile'
    )

    # SQL constraints
    _sql_constraints = [
        ('user_unique',
         'unique(user_id)',
         _('Each user can only have one booking profile!'))
    ]

    @api.onchange('team_id')
    def _onchange_team_id(self):
        """Auto-fill manager when team is selected

        Makes adding team members simpler - user only needs to select:
        1. User (user_id)
        2. Team (team_id)

        System auto-fills:
        - manager_id from team's manager
        """
        if self.team_id:
            # Auto-fill manager from team
            if self.team_id.manager_id and not self.manager_id:
                self.manager_id = self.team_id.manager_id

    @api.model
    def create(self, vals):
        """Auto-populate manager if not provided

        Ensures that programmatic creation (e.g., from team form one2many)
        automatically fills in required fields.
        """
        # Auto-fill manager from team if not provided
        if 'team_id' in vals and not vals.get('manager_id'):
            team = self.env['bm.fleet.team'].browse(vals['team_id'])
            if team.manager_id:
                vals['manager_id'] = team.manager_id.id

        return super(FleetRequestUser, self).create(vals)

    @api.model
    def get_user_profile(self, user_id=None):
        """
        Get booking profile for a user
        If user_id not provided, uses current user
        Returns dict with manager_id, team_id, sale_admin_id
        """
        if not user_id:
            user_id = self.env.uid

        profile = self.search([
            ('user_id', '=', user_id),
            ('active', '=', True)
        ], limit=1)

        if profile:
            return {
                'manager_id': profile.manager_id.id,
                'team_id': profile.team_id.id,
                'sale_admin_id': profile.sale_admin_id.id,
            }
        return {}

    @api.depends('user_id', 'team_id')
    def _compute_display_name(self):
        """Compute display name showing user and team"""
        for record in self:
            if record.user_id and record.team_id:
                record.display_name = f"{record.user_id.name} ({record.team_id.name})"
            elif record.user_id:
                record.display_name = record.user_id.name
            else:
                record.display_name = _('New')
