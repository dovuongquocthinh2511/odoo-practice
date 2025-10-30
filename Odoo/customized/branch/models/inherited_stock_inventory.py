# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import logging

from psycopg2 import Error, OperationalError

from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools.float_utils import float_compare, float_is_zero


class StockQuant(models.Model):
    _inherit = 'stock.quant'


    branch_id = fields.Many2one('res.branch', related = 'location_id.branch_id')

    def _apply_inventory(self):
        if not self.env.user.has_groups('stock.group_stock_manager'):
            raise UserError(_('Only a stock manager can validate an inventory adjustment.'))

        # Call parent method first to handle the core inventory logic
        result = super()._apply_inventory()

        # Then add branch-specific logic for moves created by parent method
        # Find the moves that were just created for this inventory
        recent_moves = self.env['stock.move'].search([
            ('is_inventory', '=', True),
            ('state', '=', 'done'),
            ('product_id', 'in', self.mapped('product_id').ids),
            ('location_id', 'in', self.mapped('location_id').ids +
                                  self.mapped('product_id.property_stock_inventory').ids),
            ('location_dest_id', 'in', self.mapped('location_id').ids +
                                       self.mapped('product_id.property_stock_inventory').ids)
        ], order='create_date desc', limit=len(self))

        # Update branch_id for the moves
        for move in recent_moves:
            # Find the corresponding quant to get branch_id
            quant = self.filtered(lambda q: q.product_id == move.product_id and
                                           (q.location_id == move.location_id or
                                            q.location_id == move.location_dest_id))
            if quant and quant[0].branch_id:
                move.write({'branch_id': quant[0].branch_id.id})

        return result

    def _get_inventory_move_values(self, qty, location_id, location_dest_id, package_id=False, package_dest_id=False):
        """ Called when user manually set a new quantity (via `inventory_quantity`)
        just before creating the corresponding stock move.

        :param location_id: `stock.location`
        :param location_dest_id: `stock.location`
        :param package_id: `stock.quant.package`
        :param package_dest_id: `stock.quant.package`
        :return: dict with all values needed to create a new `stock.move` with its move line.
        """
        # Get the base values from parent method
        values = super()._get_inventory_move_values(qty, location_id, location_dest_id, package_id, package_dest_id)

        # Add branch_id to the move values
        if self.branch_id:
            values['branch_id'] = self.branch_id.id

        return values

# class stock_inventory(models.Model):
#     _inherit = 'stock.inventory'


#     @api.model
#     def default_get(self,fields):
#         res = super(stock_inventory, self).default_get(fields)
#         if res.get('location_id'):
#             location_branch = self.env['stock.location'].browse(res.get('location_id')).branch_id.id
#             if location_branch:
#                 res['branch_id'] = location_branch 
#         else:
#             user_branch = self.env['res.users'].browse(self.env.uid).branch_id
#             if user_branch:
#                 res['branch_id'] = user_branch.id
#         return res

#     branch_id = fields.Many2one('res.branch')


#     def post_inventory(self):
#         # The inventory is posted as a single step which means quants cannot be moved from an internal location to another using an inventory
#         # as they will be moved to inventory loss, and other quants will be created to the encoded quant location. This is a normal behavior
#         # as quants cannot be reuse from inventory location (users can still manually move the products before/after the inventory if they want).
#         self.mapped('move_ids').filtered(lambda move: move.state != 'done')._action_done()
#         for move_id in self.move_ids:
#             account_move =self.env['account.move'].search([('stock_move_id','=',move_id.id)])
#             account_move.write({'branch_id':self.branch_id.id})
#             for line in account_move.line_ids:
#                     line.write({'branch_id':self.branch_id.id})


#     @api.onchange('branch_id')
#     def _onchange_branch_id(self):
#         selected_brach = self.branch_id
#         if selected_brach:
#             user_id = self.env['res.users'].browse(self.env.uid)
#             user_branch = user_id.sudo().branch_id
#             if user_branch and user_branch.id != selected_brach.id:
#                 raise UserError("Please select active branch only. Other may create the Multi branch issue. \n\ne.g: If you wish to add other branch then Switch branch from the header and set that.")