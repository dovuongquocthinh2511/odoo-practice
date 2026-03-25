# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.sql_db import SQL

class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    branch_id = fields.Many2one('res.branch')

    def _select(self):
        select_query = super(PurchaseReport, self)._select()
        return SQL("%s, po.branch_id as branch_id", select_query)

    def _group_by(self):
        group_by_query = super(PurchaseReport, self)._group_by()
        return SQL("%s, po.branch_id", group_by_query)
