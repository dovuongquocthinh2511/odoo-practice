# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class FleetServiceRejectionWizard(models.TransientModel):
    _name = 'bm.fleet.service.rejection.wizard'
    _description = 'Service Rejection Wizard'

    request_id = fields.Many2one(
        'fleet.vehicle.log.services',
        string='Đơn đặt xe',
        required=True,
        readonly=True,
        ondelete='cascade',
        help='Đơn đặt xe cần từ chối'
    )
    rejection_reason = fields.Text(string='Lý do từ chối', required=True)

    def action_confirm_rejection(self):
        """Confirm rejection with reason"""
        self.ensure_one()

        if not self.request_id:
            raise UserError(_('Đơn đặt xe không tồn tại'))

        self.request_id.write({
            'state': 'cancelled',
            'rejection_reason': self.rejection_reason,
            'rejected_by': self.env.user.id,
            'rejection_date': fields.Datetime.now(),
        })

        self.request_id.activity_unlink(['mail.mail_activity_data_todo'])

        return {'type': 'ir.actions.act_window_close'}
