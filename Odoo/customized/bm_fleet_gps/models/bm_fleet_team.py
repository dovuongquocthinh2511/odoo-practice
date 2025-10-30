# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class FleetTeam(models.Model):
    _name = 'bm.fleet.team'
    _description = 'Fleet Team'
    _order = 'name'

    name = fields.Char(
        string=_('Team Name'),
        required=True,
        translate=True
    )

    manager_id = fields.Many2one(
        'res.users',
        string=_('Manager')
    )

    member_ids = fields.One2many(
        'bm.fleet.request.user',
        'team_id',
        string=_('Team Members'),
        help='Users who are members of this team (via bm.fleet.request.user)'
    )

    member_count = fields.Integer(
        string=_('Number of Members'),
        compute='_compute_member_count',
        store=True
    )

    parent_id = fields.Many2one(
        'bm.fleet.team',
        string=_('Parent Team'),
        ondelete='restrict'
    )

    company_id = fields.Many2one(
        'res.company',
        string=_('Company'),
        default=lambda self: self.env.company
    )

    active = fields.Boolean(default=True)

    description = fields.Text(string=_('Description'))

    _sql_constraints = [
        ('name_company_unique', 'unique(name, company_id)',
         'Tên team phải unique trong cùng company!')
    ]

    @api.depends('member_ids')
    def _compute_member_count(self):
        """Compute number of team members"""
        for team in self:
            team.member_count = len(team.member_ids)
