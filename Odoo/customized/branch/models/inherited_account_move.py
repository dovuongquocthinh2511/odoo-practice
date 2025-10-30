# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def default_get(self, default_fields):
        res = super(AccountMove, self).default_get(default_fields)
        branch_id = False

        if self._context.get('branch_id'):
            branch_id = self._context.get('branch_id')
        elif self.env.user.branch_id:
            branch_id = self.env.user.branch_id.id
        res.update({
            'branch_id' : branch_id
        })
        return res

    branch_id = fields.Many2one('res.branch', string="Branch")

    @api.model_create_multi
    def create(self, vals_list):
        # Set branch_id context for move lines creation
        for vals in vals_list:
            if vals.get('branch_id') and 'line_ids' in vals:
                # Set context for move lines to inherit branch_id
                self = self.with_context(branch_id=vals['branch_id'])

        return super(AccountMove, self).create(vals_list)

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        """Update all move lines when branch_id changes"""
        if self.branch_id:
            # Update existing move lines with the new branch_id
            for line in self.line_ids:
                line.branch_id = self.branch_id.id

    def _compute_payments_widget_to_reconcile_info(self):
        """
        Override to filter outstanding credits/debits based on user permissions.
        Only show invoices that the current user has read access to avoid permission errors.
        """
        for move in self:
            move.invoice_outstanding_credits_debits_widget = False
            move.invoice_has_outstanding = False

            if move.state != 'posted' \
                    or move.payment_state not in ('not_paid', 'partial') \
                    or not move.is_invoice(include_receipts=True):
                continue

            pay_term_lines = move.line_ids\
                .filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))

            domain = [
                ('account_id', 'in', pay_term_lines.account_id.ids),
                ('parent_state', '=', 'posted'),
                ('partner_id', '=', move.commercial_partner_id.id),
                ('reconciled', '=', False),
                '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0),
            ]

            payments_widget_vals = {'outstanding': True, 'content': [], 'move_id': move.id}

            if move.is_inbound():
                domain.append(('balance', '<', 0.0))
                payments_widget_vals['title'] = _('Outstanding credits')
            else:
                domain.append(('balance', '>', 0.0))
                payments_widget_vals['title'] = _('Outstanding debits')

            # Use sudo to search all potential lines, then filter by permission
            for line in self.env['account.move.line'].sudo().search(domain):
                # Check if current user has read permission on the related move
                try:
                    # Try to read the move without sudo to check permission
                    line.move_id.with_user(self.env.user).check_access('read')

                    # If we reach here, user has permission to access this move
                    if line.currency_id == move.currency_id:
                        # Same foreign currency.
                        amount = abs(line.amount_residual_currency)
                    else:
                        # Different foreign currencies.
                        amount = line.company_currency_id._convert(
                            abs(line.amount_residual),
                            move.currency_id,
                            move.company_id,
                            line.date,
                        )

                    if move.currency_id.is_zero(amount):
                        continue

                    payments_widget_vals['content'].append({
                        'journal_name': line.ref or line.move_id.name,
                        'amount': amount,
                        'currency_id': move.currency_id.id,
                        'id': line.id,
                        'move_id': line.move_id.id,
                        'date': fields.Date.to_string(line.date),
                        'account_payment_id': line.payment_id.id,
                    })

                except Exception:
                    # User doesn't have permission to access this move, skip it
                    continue

            if not payments_widget_vals['content']:
                continue

            move.invoice_outstanding_credits_debits_widget = payments_widget_vals
            move.invoice_has_outstanding = True

    def js_assign_outstanding_line(self, line_id):
        """
        Override to check permission before reconciling outstanding lines.
        Called by the 'payment' widget to reconcile a suggested journal item to the present invoice.
        """
        self.ensure_one()

        # Check if user has permission to access the line's move
        line = self.env['account.move.line'].sudo().browse(line_id)
        try:
            # Check permission on the related move
            line.move_id.with_user(self.env.user).check_access_rights('read')
            line.move_id.with_user(self.env.user).check_access_rule('read')

            # If permission check passes, proceed with reconciliation
            lines = line
            lines += self.line_ids.filtered(lambda l: l.account_id == line.account_id and not l.reconciled)
            return lines.reconcile()

        except Exception:
            # User doesn't have permission, raise a user-friendly error
            from odoo.exceptions import AccessError
            raise AccessError(_("You don't have permission to access this invoice for reconciliation."))


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def default_get(self, default_fields):
        res = super(AccountMoveLine, self).default_get(default_fields)
        branch_id = False

        # Priority 1: Try to get from move_id in context (when creating lines for a specific move)
        if self._context.get('default_move_id'):
            move = self.env['account.move'].browse(self._context.get('default_move_id'))
            if move.branch_id:
                branch_id = move.branch_id.id
        # Priority 2: Try to get branch_id from context (this is set when creating from move)
        elif self._context.get('branch_id'):
            branch_id = self._context.get('branch_id')
        # Priority 3: Fallback to user's default branch
        elif self.env.user.branch_id:
            branch_id = self.env.user.branch_id.id

        res.update({'branch_id': branch_id})
        return res

    @api.model_create_multi
    def create(self, vals_list):
        # Ensure branch_id is set correctly when creating move lines
        for vals in vals_list:
            # Always prioritize getting branch_id from the parent move
            if 'move_id' in vals:
                move = self.env['account.move'].browse(vals['move_id'])
                if move.branch_id:
                    vals['branch_id'] = move.branch_id.id
            # If no move_id but branch_id not set, use context or user default
            elif not vals.get('branch_id'):
                if self._context.get('branch_id'):
                    vals['branch_id'] = self._context.get('branch_id')
                elif self.env.user.branch_id:
                    vals['branch_id'] = self.env.user.branch_id.id

        return super(AccountMoveLine, self).create(vals_list)

    branch_id = fields.Many2one('res.branch', string="Branch", related="move_id.branch_id", store=True)
