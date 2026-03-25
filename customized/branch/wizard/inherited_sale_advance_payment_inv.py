# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def _create_invoice(self, order, so_line, amount):
        result = super(SaleAdvancePaymentInv, self)._create_invoice(
            order, so_line, amount
        )

        branch_id = False

        if order.branch_id:
            branch_id = order.branch_id.id
        elif self.env.user.branch_id:
            branch_id = self.env.user.branch_id.id

        result.write({"branch_id": branch_id})

        return result


class AccountPaymentRegisterInv(models.TransientModel):
    _inherit = "account.payment.register"

    @api.model
    def default_get(self, fields):
        rec = super(AccountPaymentRegisterInv, self).default_get(fields)
        active_ids = self._context.get("active_ids", [])
        active_model = self._context.get("active_model")
        _logger.info(
            f"Payment Register - Active Model: {active_model}, Active IDs: {active_ids}"
        )

        try:
            # Xử lý cả 2 trường hợp: active_model là 'account.move' hoặc 'account.move.line'
            if active_model == "account.move":
                # Trường hợp được gọi trực tiếp từ account.move
                invoice_defaults = (
                    self.env["account.move"].sudo().browse(active_ids).exists()
                )
                _logger.info(f"Payment Register - Found moves: {invoice_defaults.ids}")
            elif active_model == "account.move.line":
                # Trường hợp được gọi từ account.move.action_register_payment() -> line_ids.action_register_payment()
                move_lines = (
                    self.env["account.move.line"].sudo().browse(active_ids).exists()
                )
                invoice_defaults = move_lines.mapped("move_id")
                _logger.info(
                    f"Payment Register - Found move lines: {move_lines.ids}, moves: {invoice_defaults.ids}"
                )
            else:
                _logger.warning(
                    f"Payment Register - Unsupported active_model: {active_model}"
                )
                return rec

            if invoice_defaults:
                # Lấy tất cả branch_id từ các invoices
                branch_ids = invoice_defaults.mapped("branch_id")
                _logger.info(f"Payment Register - Branch IDs: {branch_ids.ids}")

                # Nếu tất cả invoices có cùng branch_id, thì tự động set
                if len(branch_ids) == 1 and branch_ids:
                    rec["branch_id"] = branch_ids.id
                    _logger.info(f"Payment Register - Set branch_id: {branch_ids.id}")
                elif len(branch_ids) > 1:
                    _logger.info(
                        f"Payment Register - Multiple branches found, not setting default: {branch_ids.ids}"
                    )
                else:
                    _logger.info("Payment Register - No branch found on invoices")
        except Exception as e:
            _logger.error(f"Payment Register - Error in default_get: {e}")

        return rec

    branch_id = fields.Many2one("res.branch")

    def _create_payment_vals_from_wizard(self, batch_result):
        vals = super(AccountPaymentRegisterInv, self)._create_payment_vals_from_wizard(
            batch_result
        )
        if self.branch_id:
            vals.update({"branch_id": self.branch_id.id})
            _logger.info(
                f"Payment Register - Added branch_id to payment vals: {self.branch_id.id}"
            )
        return vals

    def _create_payment_vals_from_batch(self, batch_result):
        vals = super(AccountPaymentRegisterInv, self)._create_payment_vals_from_batch(
            batch_result
        )
        if self.branch_id:
            vals.update({"branch_id": self.branch_id.id})
            _logger.info(
                f"Payment Register - Added branch_id to batch payment vals: {self.branch_id.id}"
            )
        return vals

    # @api.onchange("branch_id")
    # def _onchange_branch_id(self):
    #     selected_brach = self.branch_id
    #     if selected_brach:
    #         user_id = self.env["res.users"].browse(self.env.uid)
    #         user_branch = user_id.sudo().branch_id
    #         if user_branch and user_branch.id != selected_brach.id:
    #             raise UserError(
    #                 "Please select active branch only. Other may create the Multi branch issue. \n\ne.g: If you wish to add other branch then Switch branch from the header and set that."
    #             )
