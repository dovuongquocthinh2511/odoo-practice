# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

# MODIFICATION: Changed branch assignment logic to prioritize picking_type.branch_id
# This ensures stock.picking belongs to the branch where the warehouse is located,
# not the branch that created the PO. This is more logical for inventory management.


class purchase_order(models.Model):

    _inherit = 'purchase.order.line'

    
    def _prepare_account_move_line(self, move=False):
        result = super(purchase_order, self)._prepare_account_move_line(move)
        result.update({
            'branch_id' : self.order_id.branch_id.id or False,
            
        })
        return result


    @api.model
    def default_get(self, default_fields):
        res = super(purchase_order, self).default_get(default_fields)
        branch_id = False
        if self._context.get('branch_id'):
            branch_id = self._context.get('branch_id')
        elif self.env.user.branch_id:
            branch_id = self.env.user.branch_id.id
        res.update({'branch_id' : branch_id})
        return res

    branch_id = fields.Many2one('res.branch', string="Branch")


    def _prepare_stock_moves(self, picking):
        result = super(purchase_order, self)._prepare_stock_moves(picking)

        branch_id = False
        # Ưu tiên 1: Lấy từ picking.branch_id (đã được set từ picking_type)
        if picking and picking.branch_id:
            branch_id = picking.branch_id.id
        # Ưu tiên 2: Lấy từ order line branch_id
        elif self.branch_id:
            branch_id = self.branch_id.id
        # Ưu tiên 3: Lấy từ user hiện tại
        elif self.env.user.branch_id:
            branch_id = self.env.user.branch_id.id

        for res in result:
            res.update({'branch_id' : branch_id})

        return result


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    
    @api.model
    def default_get(self,fields):
        res = super(PurchaseOrder, self).default_get(fields)
        branch_id = picking_type_id = False

        if self.env.user.branch_id:
            branch_id = self.env.user.branch_id.id

        if branch_id:
            # Sử dụng sudo() để đảm bảo truy cập được warehouse của chi nhánh khác
            branched_warehouse = self.env['stock.warehouse'].sudo().search([('branch_id','=',branch_id)])
            if branched_warehouse:
                picking_type_id = branched_warehouse[0].in_type_id.id
        else:
            picking = self._default_picking_type()
            picking_type_id = picking.id

        res.update({
            'branch_id' : branch_id,
            'picking_type_id' : picking_type_id
        })

        return res

    branch_id = fields.Many2one('res.branch', string='Branch')
    purchase_manual_currency_rate_active = fields.Boolean(string="Apply Manual Exchange")
    purchase_manual_currency_rate = fields.Float(string="Rate")

    @api.model
    def _prepare_picking(self):
        res = super(PurchaseOrder, self)._prepare_picking()
        branch_id = False

        # Ưu tiên 1: Lấy từ picking_type_id.branch_id (nơi nhận hàng)
        # Sử dụng sudo() để đảm bảo truy cập được picking type của chi nhánh khác
        if self.picking_type_id and self.picking_type_id.sudo().branch_id:
            branch_id = self.picking_type_id.sudo().branch_id.id
        # Ưu tiên 2: Lấy từ PO.branch_id
        elif self.branch_id:
            branch_id = self.branch_id.id
        # Ưu tiên 3: Lấy từ user hiện tại
        elif self.env.user.branch_id:
            branch_id = self.env.user.branch_id.id

        res.update({
            'branch_id' : branch_id
        })
        return res


    def _prepare_invoice(self):
        result = super(PurchaseOrder, self)._prepare_invoice()
        branch_id = False
        if self.branch_id:
            branch_id = self.branch_id.id
        elif self.env.user.branch_id:
            branch_id = self.env.user.branch_id.id

        result.update({
                
                'branch_id' : branch_id
            })
        
        return result
    def action_view_invoice(self, invoices=False):
        '''
        This function returns an action that display existing vendor bills of given purchase order ids.
        When only one found, show the vendor bill immediately.
        '''

        result = super(PurchaseOrder, self).action_view_invoice(invoices)

        branch_id = False
        if self.branch_id:
            branch_id = self.branch_id.id
        elif self.env.user.branch_id:
            branch_id = self.env.user.branch_id.id


        result.update({
                
                'branch_id' : branch_id
            })
        

        return result

    # @api.onchange('branch_id')
    # def _onchange_branch_id(self):
    #     selected_brach = self.branch_id
    #     if selected_brach:
    #         user_id = self.env['res.users'].browse(self.env.uid)
    #         user_branch = user_id.sudo().branch_id
    #         if user_branch and user_branch.id != selected_brach.id:
    #             raise UserError("Please select active branch only. Other may create the Multi branch issue. \n\ne.g: If you wish to add other branch then Switch branch from the header and set that.")