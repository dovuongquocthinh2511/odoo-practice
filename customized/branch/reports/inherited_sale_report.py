# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    branch_id = fields.Many2one('res.branch')

    def _select_sale(self):
        select_query = super()._select_sale()

        return select_query + ", s.branch_id"
