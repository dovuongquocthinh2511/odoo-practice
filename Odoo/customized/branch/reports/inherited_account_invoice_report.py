# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.sql_db import SQL

class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    branch_id = fields.Many2one('res.branch')

    def _select(self):
        select_query = super(AccountInvoiceReport, self)._select()
        return SQL("%s, move.branch_id", select_query)