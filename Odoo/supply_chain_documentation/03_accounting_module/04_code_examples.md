# 💻 Ví Dụ Code Accounting Module - Odoo 18

## 🎯 Giới Thiệu Code Examples

Chương này cung cấp các ví dụ code thực tế cho accounting module integration với supply chain, tập trung vào financial workflows, inventory valuation, và manufacturing cost accounting với Vietnamese business terminology.

## 📦 Purchase-to-Pay Workflow Examples

### Example 1: Three-Way Matching Automation

```python
class PurchaseInvoiceManager(models.Model):
    _inherit = 'account.move'

    def action_three_way_matching(self):
        """Thực hiện đối chiếu ba chiều tự động"""
        self.ensure_one()

        if self.move_type != 'in_invoice':
            raise UserError(_('Chỉ áp dụng cho hóa đơn nhà cung cấp'))

        # Lấy thông tin Purchase Order liên quan
        purchase_order = self.purchase_order_id
        if not purchase_order:
            raise UserError(_('Không tìm thấy Purchase Order liên quan'))

        # Thực hiện đối chiếu
        matching_result = self._perform_three_way_matching(purchase_order)

        if matching_result['status'] == 'matched':
            self.write({
                'state': 'posted',
                'matching_status': 'three_way_matched',
                'matching_date': fields.Datetime.now()
            })

            # Tạo payment term tự động
            self._create_auto_payment(purchase_order)

            self.message_post(
                body=_('Đối chiếu ba chiều thành công: %s') % matching_result['details']
            )

        elif matching_result['status'] == 'discrepancy':
            self._handle_matching_discrepancy(matching_result)

        return matching_result

    def _perform_three_way_matching(self, purchase_order):
        """Thực hiện logic đối chiếu ba chiều"""
        discrepancies = []

        # Đối chiếu quantity
        invoice_lines = self.invoice_line_ids
        for po_line in purchase_order.order_line:
            # Tìm invoice line tương ứng
            invoice_line = invoice_lines.filtered(
                lambda l: l.product_id == po_line.product_id
            )

            if invoice_line:
                # Đối chiếu quantity
                if invoice_line.quantity != po_line.product_qty:
                    discrepancies.append({
                        'type': 'quantity',
                        'product': po_line.product_id.name,
                        'po_qty': po_line.product_qty,
                        'invoice_qty': invoice_line.quantity,
                        'received_qty': po_line.qty_received
                    })

                # Đối chiếu price
                if abs(invoice_line.price_unit - po_line.price_unit) > 0.01:
                    discrepancies.append({
                        'type': 'price',
                        'product': po_line.product_id.name,
                        'po_price': po_line.price_unit,
                        'invoice_price': invoice_line.price_unit
                    })

        if discrepancies:
            return {
                'status': 'discrepancy',
                'discrepancies': discrepancies,
                'total_discrepancy_amount': sum(d.get('amount', 0) for d in discrepancies)
            }

        return {
            'status': 'matched',
            'details': _('Tất cả các dòng hóa đơn khớp với Purchase Order và Receipt')
        }

    def _handle_matching_discrepancy(self, matching_result):
        """Xử lý sai lệch đối chiếu"""
        self.write({
            'state': 'draft',
            'matching_status': 'discrepancy_found'
        })

        # Tạo activity cho user review
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            summary=_('Review discrepancy in three-way matching'),
            note=_('Sai lệch đối chiếu: %s') % matching_result['discrepancies']
        )
```

### Example 2: Automated Invoice Creation from Receipt

```python
class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_create_supplier_invoice(self):
        """Tự động tạo supplier invoice từ goods receipt"""
        self.ensure_one()

        if self.picking_type_id.code != 'incoming':
            raise UserError(_('Chỉ áp dụng cho phiếu nhập hàng'))

        # Kiểm tra đã có invoice chưa
        existing_invoice = self.env['account.move'].search([
            ('move_type', '=', 'in_invoice'),
            ('stock_picking_id', '=', self.id),
            ('state', '!=', 'cancel')
        ])

        if existing_invoice:
            raise UserError(_('Đã có hóa đơn cho phiếu nhập hàng này'))

        # Lấy thông tin Purchase Order
        purchase_order = self.purchase_id
        if not purchase_order:
            raise UserError(_('Phiếu nhập không liên kết với Purchase Order'))

        # Tạo invoice lines từ move lines
        invoice_lines = []
        for move in self.move_lines:
            if move.state == 'done':
                invoice_lines.append((0, 0, {
                    'product_id': move.product_id.id,
                    'quantity': move.product_uom_qty,
                    'product_uom_id': move.product_uom.id,
                    'price_unit': move._get_purchase_price(),
                    'name': move.description_picking or move.product_id.name,
                    'account_id': move.product_id.categ_id.property_account_expense_categ_id.id or \
                                move.product_id.property_account_expense_id.id,
                }))

        # Tạo invoice
        invoice_vals = {
            'move_type': 'in_invoice',
            'partner_id': purchase_order.partner_id.id,
            'invoice_origin': purchase_order.name,
            'ref': self.name,
            'journal_id': purchase_order.partner_id.property_supplier_journal_id.id or \
                         self.env['account.journal'].search([
                             ('type', '=', 'purchase'),
                             ('company_id', '=', self.env.company.id)
                         ], limit=1).id,
            'invoice_line_ids': invoice_lines,
            'invoice_payment_term_id': purchase_order.payment_term_id.id,
            'fiscal_position_id': purchase_order.fiscal_position_id.id,
            'stock_picking_id': self.id,
            'company_id': self.env.company.id,
        }

        invoice = self.env['account.move'].create(invoice_vals)

        # Post invoice nếu auto-post được bật
        if self.env.company.account_auto_post_invoices:
            invoice.action_post()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Hóa đơn nhà cung cấp'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current'
        }

    def action_batch_invoice_creation(self):
        """Tạo invoice hàng loạt cho nhiều phiếu nhập"""
        if len(self) == 1:
            return self.action_create_supplier_invoice()

        # Group by supplier
        supplier_dict = {}
        for picking in self:
            if picking.picking_type_id.code != 'incoming':
                continue

            supplier = picking.purchase_id.partner_id if picking.purchase_id else None
            if not supplier:
                continue

            if supplier.id not in supplier_dict:
                supplier_dict[supplier.id] = {
                    'partner': supplier,
                    'pickings': self.env['stock.picking'],
                    'total_lines': []
                }

            supplier_dict[supplier.id]['pickings'] |= picking

            # Gom move lines
            for move in picking.move_lines:
                if move.state == 'done':
                    supplier_dict[supplier.id]['total_lines'].append(move)

        # Tạo invoices
        invoices = self.env['account.move']
        for supplier_id, supplier_data in supplier_dict.items():
            if not supplier_data['total_lines']:
                continue

            # Tạo invoice lines
            invoice_lines = []
            product_summary = {}

            # Group by product
            for move in supplier_data['total_lines']:
                product_key = move.product_id.id
                if product_key not in product_summary:
                    product_summary[product_key] = {
                        'product': move.product_id,
                        'quantity': 0,
                        'price_unit': move._get_purchase_price(),
                    }

                product_summary[product_key]['quantity'] += move.product_uom_qty

            # Create invoice lines
            for product_data in product_summary.values():
                invoice_lines.append((0, 0, {
                    'product_id': product_data['product'].id,
                    'quantity': product_data['quantity'],
                    'price_unit': product_data['price_unit'],
                    'name': product_data['product'].name,
                    'account_id': product_data['product'].categ_id.property_account_expense_categ_id.id,
                }))

            invoice_vals = {
                'move_type': 'in_invoice',
                'partner_id': supplier_id,
                'journal_id': supplier_data['partner'].property_supplier_journal_id.id,
                'invoice_line_ids': invoice_lines,
                'invoice_date': fields.Date.today(),
                'company_id': self.env.company.id,
            }

            invoice = self.env['account.move'].create(invoice_vals)
            invoices |= invoice

        # Return action để xem invoices
        if len(invoices) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Hóa đơn nhà cung cấp'),
                'res_model': 'account.move',
                'res_id': invoices.id,
                'view_mode': 'form',
                'target': 'current'
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Hóa đơn nhà cung cấp'),
                'res_model': 'account.move',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', invoices.ids)],
                'target': 'current'
            }
```

## 🏭 Manufacturing Cost Accounting Examples

### Example 3: Work Order Cost Calculation

```python
class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    # Thêm fields cho cost tracking
    actual_material_cost = fields.Float(
        string='Chi phí nguyên vật liệu thực tế',
        compute='_compute_actual_costs',
        store=True
    )
    actual_labor_cost = fields.Float(
        string='Chi phí nhân công thực tế',
        compute='_compute_actual_costs',
        store=True
    )
    actual_overhead_cost = fields.Float(
        string='Chi phí chung thực tế',
        compute='_compute_actual_costs',
        store=True
    )
    total_actual_cost = fields.Float(
        string='Tổng chi phí thực tế',
        compute='_compute_actual_costs',
        store=True
    )
    cost_variance = fields.Float(
        string='Chênh lệch chi phí',
        compute='_compute_cost_variance',
        store=True
    )

    @api.depends('move_raw_ids.state', 'workorder_ids')
    def _compute_actual_costs(self):
        """Tính toán chi phí thực tế của production order"""
        for production in self:
            # Chi phí nguyên vật liệu
            material_cost = 0
            for move in production.move_raw_ids:
                if move.state == 'done':
                    material_cost += move.quantity_done * move._get_price_unit()

            # Chi phí nhân công
            labor_cost = 0
            for workorder in production.workorder_ids:
                if workorder.is_finished:
                    # Lấy hourly rate từ work center
                    hourly_rate = workorder.workcenter_id.costs_hour or 0
                    labor_hours = workorder.duration / 60  # Convert minutes to hours
                    labor_cost += labor_hours * hourly_rate

            # Chi phí chung (overhead)
            overhead_cost = 0
            for workorder in production.workorder_ids:
                if workorder.is_finished:
                    # Tính overhead dựa trên percentage hoặc fixed rate
                    workcenter = workorder.workcenter_id
                    if workcenter.costs_hour_overhead:
                        labor_hours = workorder.duration / 60
                        overhead_cost += labor_hours * workcenter.costs_hour_overhead

            production.actual_material_cost = material_cost
            production.actual_labor_cost = labor_cost
            production.actual_overhead_cost = overhead_cost
            production.total_actual_cost = material_cost + labor_cost + overhead_cost

    @api.depends('total_actual_cost', 'cost_total')
    def _compute_cost_variance(self):
        """Tính chênh lệch chi phí"""
        for production in self:
            production.cost_variance = production.total_actual_cost - production.cost_total

    def action_post_accounting_entries(self):
        """Tạo bút toán kế toán khi production hoàn thành"""
        self.ensure_one()

        if self.state != 'done':
            raise UserError(_('Chỉ có thể post accounting entries cho production đã hoàn thành'))

        # Tạo journal entry cho material consumption
        self._create_material_consumption_entry()

        # Tạo journal entry cho labor và overhead costs
        self._create_labor_overhead_entry()

        # Tạo journal entry cho finished goods
        self._create_finished_goods_entry()

        # Update production state
        self.accounting_entries_posted = True

        self.message_post(
            body=_('Đã tạo bút toán kế toán cho production order %s') % self.name
        )

    def _create_material_consumption_entry(self):
        """Tạo bút toán tiêu thụ nguyên vật liệu"""
        if not self.actual_material_cost:
            return

        # Lấy raw material inventory account
        inventory_account = self.env['account.account'].search([
            ('company_id', '=', self.env.company.id),
            ('deprecated', '=', False)
        ], limit=1)

        # Lấy work in process account
        wip_account = self.env['account.account'].search([
            ('company_id', '=', self.env.company.id),
            ('deprecated', '=', False)
        ], limit=1)

        line_ids = [
            (0, 0, {
                'account_id': wip_account.id,
                'debit': self.actual_material_cost,
                'name': _('Material consumption for %s') % self.name,
                'product_id': self.product_id.id,
            }),
            (0, 0, {
                'account_id': inventory_account.id,
                'credit': self.actual_material_cost,
                'name': _('Material consumption for %s') % self.name,
                'product_id': self.product_id.id,
            })
        ]

        journal_entry = self.env['account.move'].create({
            'journal_id': self.env.company.production_journal_id.id,
            'date': fields.Date.today(),
            'ref': self.name,
            'line_ids': line_ids,
            'move_type': 'entry',
            'company_id': self.env.company.id,
        })

        journal_entry.action_post()

    def _create_labor_overhead_entry(self):
        """Tạo bút toán cho chi phí nhân công và overhead"""
        total_labor_overhead = self.actual_labor_cost + self.actual_overhead_cost

        if not total_labor_overhead:
            return

        # Lấy expense accounts
        labor_expense_account = self.env['account.account'].search([
            ('company_id', '=', self.env.company.id),
            ('deprecated', '=', False)
        ], limit=1)

        wip_account = self.env['account.account'].search([
            ('company_id', '=', self.env.company.id),
            ('deprecated', '=', False)
        ], limit=1)

        line_ids = [
            (0, 0, {
                'account_id': wip_account.id,
                'debit': total_labor_overhead,
                'name': _('Labor and overhead for %s') % self.name,
            }),
            (0, 0, {
                'account_id': labor_expense_account.id,
                'credit': self.actual_labor_cost,
                'name': _('Labor cost for %s') % self.name,
            })
        ]

        # Thêm overhead expense account nếu có
        if self.actual_overhead_cost:
            overhead_account = self.env['account.account'].search([
                ('company_id', '=', self.env.company.id),
                ('deprecated', '=', False)
            ], limit=1)

            line_ids.append((0, 0, {
                'account_id': overhead_account.id,
                'credit': self.actual_overhead_cost,
                'name': _('Overhead cost for %s') % self.name,
            }))

        journal_entry = self.env['account.move'].create({
            'journal_id': self.env.company.production_journal_id.id,
            'date': fields.Date.today(),
            'ref': self.name + ' - Labor & Overhead',
            'line_ids': line_ids,
            'move_type': 'entry',
            'company_id': self.env.company.id,
        })

        journal_entry.action_post()

    def _create_finished_goods_entry(self):
        """Tạo bút toán cho thành phẩm hoàn thành"""
        if not self.total_actual_cost:
            return

        # Lấy finished goods account
        fg_account = self.env['account.account'].search([
            ('company_id', '=', self.env.company.id),
            ('deprecated', '=', False)
        ], limit=1)

        wip_account = self.env['account.account'].search([
            ('company_id', '=', self.env.company.id),
            ('deprecated', '=', False)
        ], limit=1)

        line_ids = [
            (0, 0, {
                'account_id': fg_account.id,
                'debit': self.total_actual_cost,
                'name': _('Finished goods from %s') % self.name,
                'product_id': self.product_id.id,
                'quantity': self.product_qty,
            }),
            (0, 0, {
                'account_id': wip_account.id,
                'credit': self.total_actual_cost,
                'name': _('Finished goods from %s') % self.name,
                'product_id': self.product_id.id,
                'quantity': self.product_qty,
            })
        ]

        journal_entry = self.env['account.move'].create({
            'journal_id': self.env.company.production_journal_id.id,
            'date': fields.Date.today(),
            'ref': self.name + ' - Finished Goods',
            'line_ids': line_ids,
            'move_type': 'entry',
            'company_id': self.env.company.id,
        })

        journal_entry.action_post()
```

## 💰 Sales-to-Cash Integration Examples

### Example 4: Customer Invoice Creation with Revenue Recognition

```python
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_create_invoice(self):
        """Tạo customer invoice với revenue recognition logic"""
        self.ensure_one()

        # Kiểm tra invoice policy
        if self.invoice_status != 'to invoice':
            raise UserError(_('Không thể tạo invoice cho order này'))

        # Tạo invoice lines
        invoice_lines = []
        for line in self.order_line:
            if line.qty_to_invoice > 0:
                invoice_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'quantity': line.qty_to_invoice,
                    'product_uom_id': line.product_uom.id,
                    'price_unit': line.price_unit,
                    'discount': line.discount,
                    'name': line.name,
                    'account_id': line._get_account_id(),
                    'tax_ids': [(6, 0, line.tax_id.ids)],
                    'sale_line_ids': [(4, line.id)],
                }))

        # Tạo invoice
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'currency_id': self.pricelist_id.currency_id.id,
            'journal_id': self.partner_id.property_journal_id.id,
            'invoice_origin': self.name,
            'payment_term_id': self.payment_term_id.id,
            'fiscal_position_id': self.fiscal_position_id.id,
            'team_id': self.team_id.id,
            'invoice_line_ids': invoice_lines,
            'campaign_id': self.campaign_id.id,
            'medium_id': self.medium_id.id,
            'source_id': self.source_id.id,
            'company_id': self.company_id.id,
        }

        invoice = self.env['account.move'].create(invoice_vals)

        # Tự động post invoice nếu cấu hình
        if self.env.company.account_auto_post_invoices:
            invoice.action_post()

        # Update order status
        self._compute_invoice_status()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Customer Invoice'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current'
        }

    def action_invoice_with_costing(self):
        """Tạo invoice kèm theo cost calculation cho profit analysis"""
        invoice = self.action_create_invoice()
        invoice_obj = self.env['account.move'].browse(invoice['res_id'])

        # Tính toán cost của goods sold
        total_cost = 0
        cost_breakdown = []

        for inv_line in invoice_obj.invoice_line_ids:
            sale_line = inv_line.sale_line_ids
            if sale_line:
                # Lấy cost từ product hoặc calculation
                if hasattr(sale_line[0], 'product_id') and sale_line[0].product_id:
                    product = sale_line[0].product_id
                    cost_price = product.standard_price or 0

                    # FIFO cost calculation
                    if product.cost_method == 'fifo':
                        cost_price = self._calculate_fifo_cost(
                            product,
                            inv_line.quantity
                        )
                    elif product.cost_method == 'average':
                        cost_price = product.average_cost or 0

                    line_cost = cost_price * inv_line.quantity
                    total_cost += line_cost

                    cost_breakdown.append({
                        'product': product.name,
                        'quantity': inv_line.quantity,
                        'unit_cost': cost_price,
                        'total_cost': line_cost,
                    })

        # Lưu cost information vào invoice
        invoice_obj.write({
            'total_cost': total_cost,
            'cost_breakdown': str(cost_breakdown),
        })

        # Tạo cost of goods sold journal entry
        if total_cost > 0:
            self._create_cogs_entry(invoice_obj, total_cost)

        return invoice

    def _calculate_fifo_cost(self, product, quantity):
        """Tính FIFO cost cho sản phẩm"""
        # Lấy stock valuation layers theo FIFO
        layers = self.env['stock.valuation.layer'].search([
            ('product_id', '=', product.id),
            ('company_id', '=', self.env.company.id),
            ('remaining_qty', '>', 0)
        ], order='create_date, id')

        total_cost = 0
        remaining_qty = quantity

        for layer in layers:
            if remaining_qty <= 0:
                break

            qty_to_take = min(remaining_qty, layer.remaining_qty)
            total_cost += qty_to_take * layer.unit_cost
            remaining_qty -= qty_to_take

        return total_cost / quantity if quantity > 0 else 0

    def _create_cogs_entry(self, invoice, total_cost):
        """Tạo bút toán Cost of Goods Sold"""
        # Lấy inventory account
        inventory_account = self.env['account.account'].search([
            ('company_id', '=', self.env.company.id),
            ('deprecated', '=', False)
        ], limit=1)

        # Lấy COGS account
        cogs_account = self.env['account.account'].search([
            ('company_id', '=', self.env.company.id),
            ('deprecated', '=', False)
        ], limit=1)

        line_ids = [
            (0, 0, {
                'account_id': cogs_account.id,
                'debit': total_cost,
                'name': _('COGS for %s') % invoice.name,
                'product_id': invoice.partner_id.id,
            }),
            (0, 0, {
                'account_id': inventory_account.id,
                'credit': total_cost,
                'name': _('COGS for %s') % invoice.name,
                'product_id': invoice.partner_id.id,
            })
        ]

        journal_entry = self.env['account.move'].create({
            'journal_id': self.env.company.sales_journal_id.id,
            'date': invoice.invoice_date,
            'ref': invoice.name + ' - COGS',
            'line_ids': line_ids,
            'move_type': 'entry',
            'company_id': self.env.company.id,
        })

        journal_entry.action_post()
```

## 🌐 Multi-Currency Accounting Examples

### Example 5: Exchange Rate Management and Revaluation

```python
class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def action_post(self):
        """Override post để xử lý multi-currency"""
        # Xử lý exchange rate difference
        if self.currency_id != self.company_id.currency_id:
            self._handle_exchange_rate_difference()

        return super().action_post()

    def _handle_exchange_rate_difference(self):
        """Xử lý chênh lệch tỷ giá"""
        if not self.invoice_ids:
            return

        for invoice in self.invoice_ids:
            if invoice.currency_id != self.company_id.currency_id:
                # Tính exchange rate difference
                original_amount = invoice.amount_total
                current_rate = self.currency_id.rate or 1

                # Convert đến company currency
                company_amount = original_amount * current_rate

                # Tính difference
                paid_amount = self.amount
                rate_diff = company_amount - paid_amount

                if abs(rate_diff) > 0.01:  # Only create entry if significant
                    self._create_exchange_rate_entry(invoice, rate_diff)

    def _create_exchange_rate_entry(self, invoice, rate_diff):
        """Tạo bút toán cho chênh lệch tỷ giá"""
        # Lấy exchange rate gain/loss accounts
        gain_account = self.env.company.income_currency_exchange_account_id
        loss_account = self.env.company.expense_currency_exchange_account_id

        account = gain_account if rate_diff > 0 else loss_account

        line_ids = [
            (0, 0, {
                'account_id': account.id,
                'debit': abs(rate_diff) if rate_diff < 0 else 0,
                'credit': rate_diff if rate_diff > 0 else 0,
                'name': _('Exchange rate difference for %s') % invoice.name,
                'partner_id': invoice.partner_id.id,
            })
        ]

        if self.partner_id.property_account_receivable_id:
            line_ids.append((0, 0, {
                'account_id': self.partner_id.property_account_receivable_id.id,
                'debit': rate_diff if rate_diff > 0 else 0,
                'credit': abs(rate_diff) if rate_diff < 0 else 0,
                'name': _('Exchange rate difference for %s') % invoice.name,
                'partner_id': invoice.partner_id.id,
            }))

        journal_entry = self.env['account.move'].create({
            'journal_id': self.journal_id.id,
            'date': self.date,
            'ref': self.name + ' - Exchange Rate',
            'line_ids': line_ids,
            'move_type': 'entry',
            'company_id': self.env.company.id,
        })

        journal_entry.action_post()

class ResCurrency(models.Model):
    _inherit = 'res.currency'

    def action_monthly_revaluation(self, date=None):
        """Thực hiện đánh giá lại hàng tháng cho tất cả balances"""
        if not date:
            date = fields.Date.today()

        # Lấy tất cả các currency khác company currency
        foreign_currencies = self.search([
            ('id', '!=', self.env.company.currency_id.id)
        ])

        revaluation_entries = self.env['account.move']

        for currency in foreign_currencies:
            entries = self._create_currency_revaluation_entries(currency, date)
            revaluation_entries |= entries

        if revaluation_entries:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Currency Revaluation Entries'),
                'res_model': 'account.move',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', revaluation_entries.ids)],
                'target': 'current'
            }

        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _('No Revaluation Needed'),
                          'message': _('No currency revaluation entries required'),
                          'type': 'success'}}

    def _create_currency_revaluation_entries(self, currency, revaluation_date):
        """Tạo revaluation entries cho một currency"""
        # Lấy tất cả account balances trong currency này
        company_currency = self.env.company.currency_id
        current_rate = currency.rate or 1

        # Tìm tất cả account có balances trong foreign currency
        domain = [
            ('company_id', '=', self.env.company.id),
            ('currency_id', '=', currency.id),
            ('reconciled', '=', False),
        ]

        move_lines = self.env['account.move.line'].search(domain)

        # Group by account
        account_balances = {}
        for line in move_lines:
            account_id = line.account_id.id
            if account_id not in account_balances:
                account_balances[account_id] = {
                    'account': line.account_id,
                    'balance': 0,
                    'lines': self.env['account.move.line']
                }

            account_balances[account_id]['balance'] += line.balance
            account_balances[account_id]['lines'] |= line

        revaluation_entries = self.env['account.move']

        # Tạo revaluation entries cho các account balances
        for account_id, account_data in account_balances.items():
            if abs(account_data['balance']) > 0.01:
                entry = self._create_single_revaluation_entry(
                    account_data, currency, current_rate, revaluation_date
                )
                revaluation_entries |= entry

        return revaluation_entries

    def _create_single_revaluation_entry(self, account_data, currency, current_rate, date):
        """Tạo single revaluation entry"""
        company_currency = self.env.company.currency_id
        balance = account_data['balance']

        # Convert balance to company currency at current rate
        company_balance = balance * current_rate

        # Get original company currency balance
        original_company_balance = sum(
            line.balance for line in account_data['lines']
            if line.currency_id == company_currency
        )

        # Calculate revaluation amount
        revaluation_amount = company_balance - original_company_balance

        if abs(revaluation_amount) < 0.01:
            return self.env['account.move']

        # Get revaluation accounts
        if revaluation_amount > 0:  # Gain
            gain_account = self.env.company.income_currency_exchange_account_id
            credit_account = account_data['account']
        else:  # Loss
            loss_account = self.env.company.expense_currency_exchange_account_id
            credit_account = account_data['account']
            revaluation_amount = abs(revaluation_amount)

        # Create journal entry
        line_ids = [
            (0, 0, {
                'account_id': gain_account.id if revaluation_amount > 0 else loss_account.id,
                'debit': revaluation_amount,
                'name': _('Currency revaluation - %s') % currency.name,
            }),
            (0, 0, {
                'account_id': credit_account.id,
                'credit': revaluation_amount,
                'name': _('Currency revaluation - %s') % currency.name,
            })
        ]

        entry = self.env['account.move'].create({
            'journal_id': self.env.company.currency_exchange_journal_id.id,
            'date': date,
            'ref': _('Currency Revaluation %s') % date.strftime('%Y-%m'),
            'line_ids': line_ids,
            'move_type': 'entry',
            'company_id': self.env.company.id,
        })

        entry.action_post()
        return entry
```

## 📊 Financial Reporting Examples

### Example 6: Custom Financial Reports for Supply Chain

```python
class AccountFinancialReport(models.AbstractModel):
    _inherit = 'account.report'

    def get_supply_chain_report_data(self, options):
        """Lấy data cho supply chain financial report"""
        # Lấy dates từ options
        date_from = options.get('date_from')
        date_to = options.get('date_to')

        # Data structures
        report_data = {
            'purchase_metrics': self._get_purchase_metrics(date_from, date_to),
            'inventory_metrics': self._get_inventory_metrics(date_from, date_to),
            'manufacturing_metrics': self._get_manufacturing_metrics(date_from, date_to),
            'sales_metrics': self._get_sales_metrics(date_from, date_to),
            'cash_flow_metrics': self._get_cash_flow_metrics(date_from, date_to),
        }

        return report_data

    def _get_purchase_metrics(self, date_from, date_to):
        """Lấy purchase metrics"""
        domain = [
            ('state', 'in', ['purchase', 'done']),
            ('date_order', '>=', date_from),
            ('date_order', '<=', date_to),
            ('company_id', '=', self.env.company.id),
        ]

        purchases = self.env['purchase.order'].search(domain)

        total_amount = sum(purchases.mapped('amount_total'))
        total_invoiced = sum(purchases.mapped('amount_untaxed_invoiced'))

        # Top suppliers
        supplier_data = {}
        for purchase in purchases:
            supplier = purchase.partner_id
            if supplier.id not in supplier_data:
                supplier_data[supplier.id] = {
                    'name': supplier.name,
                    'amount': 0,
                    'count': 0
                }
            supplier_data[supplier.id]['amount'] += purchase.amount_total
            supplier_data[supplier.id]['count'] += 1

        # Sort by amount
        top_suppliers = sorted(
            supplier_data.values(),
            key=lambda x: x['amount'],
            reverse=True
        )[:10]

        return {
            'total_purchase_amount': total_amount,
            'total_invoiced_amount': total_invoiced,
            'pending_invoicing': total_amount - total_invoiced,
            'order_count': len(purchases),
            'average_order_value': total_amount / len(purchases) if purchases else 0,
            'top_suppliers': top_suppliers,
        }

    def _get_inventory_metrics(self, date_from, date_to):
        """Lấy inventory metrics"""
        # Get current inventory value
        products = self.env['product.product'].search([
            ('type', '=', 'product'),
            ('company_id', '=', self.env.company.id)
        ])

        total_inventory_value = 0
        inventory_by_category = {}

        for product in products:
            qty_available = product.qty_available
            if qty_available > 0:
                # Get cost using appropriate costing method
                if product.cost_method == 'fifo':
                    cost = self._get_fifo_cost(product, qty_available)
                elif product.cost_method == 'average':
                    cost = product.average_cost or product.standard_price
                else:
                    cost = product.standard_price

                value = qty_available * cost
                total_inventory_value += value

                # Category breakdown
                category = product.categ_id.name or 'Uncategorized'
                if category not in inventory_by_category:
                    inventory_by_category[category] = {
                        'value': 0,
                        'products': 0
                    }
                inventory_by_category[category]['value'] += value
                inventory_by_category[category]['products'] += 1

        # Get inventory movements in period
        move_domain = [
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('company_id', '=', self.env.company.id),
            ('state', '=', 'done')
        ]

        inventory_moves = self.env['stock.move'].search(move_domain)

        total_in_value = 0
        total_out_value = 0

        for move in inventory_moves:
            if move.location_id.usage == 'supplier' and move.location_dest_id.usage == 'internal':
                # Stock in
                total_in_value += move.product_id.standard_price * move.product_qty
            elif move.location_id.usage == 'internal' and move.location_dest_id.usage == 'customer':
                # Stock out (COGS)
                total_out_value += move.product_id.standard_price * move.product_qty

        return {
            'total_inventory_value': total_inventory_value,
            'inventory_turnover': total_out_value / total_inventory_value if total_inventory_value else 0,
            'total_in_value': total_in_value,
            'total_out_value': total_out_value,
            'net_change': total_in_value - total_out_value,
            'inventory_by_category': inventory_by_category,
            'product_count': len(products),
        }

    def _get_manufacturing_metrics(self, date_from, date_to):
        """Lấy manufacturing metrics"""
        domain = [
            ('state', '=', 'done'),
            ('date_planned_finished', '>=', date_from),
            ('date_planned_finished', '<=', date_to),
            ('company_id', '=', self.env.company.id),
        ]

        productions = self.env['mrp.production'].search(domain)

        total_material_cost = sum(p.mapped('actual_material_cost'))
        total_labor_cost = sum(p.mapped('actual_labor_cost'))
        total_overhead_cost = sum(p.mapped('actual_overhead_cost'))
        total_production_cost = sum(p.mapped('total_actual_cost'))

        # Production efficiency metrics
        on_time_productions = 0
        delayed_productions = 0

        for production in productions:
            if production.date_planned_finished <= production.date_deadline:
                on_time_productions += 1
            else:
                delayed_productions += 1

        # Top products by production volume
        production_by_product = {}
        for production in productions:
            product = production.product_id
            if product.id not in production_by_product:
                production_by_product[product.id] = {
                    'name': product.name,
                    'quantity': 0,
                    'cost': 0
                }
            production_by_product[product.id]['quantity'] += production.product_qty
            production_by_product[product.id]['cost'] += production.total_actual_cost

        top_products = sorted(
            production_by_product.values(),
            key=lambda x: x['quantity'],
            reverse=True
        )[:10]

        return {
            'production_orders': len(productions),
            'total_material_cost': total_material_cost,
            'total_labor_cost': total_labor_cost,
            'total_overhead_cost': total_overhead_cost,
            'total_production_cost': total_production_cost,
            'average_cost_per_unit': total_production_cost / sum(p.mapped('product_qty')) if productions else 0,
            'on_time_delivery_rate': on_time_productions / len(productions) * 100 if productions else 0,
            'cost_breakdown': {
                'materials': total_material_cost,
                'labor': total_labor_cost,
                'overhead': total_overhead_cost
            },
            'top_products': top_products,
        }

    def _get_sales_metrics(self, date_from, date_to):
        """Lấy sales metrics"""
        domain = [
            ('state', 'in', ['sale', 'done']),
            ('date_order', '>=', date_from),
            ('date_order', '<=', date_to),
            ('company_id', '=', self.env.company.id),
        ]

        sales_orders = self.env['sale.order'].search(domain)

        total_revenue = sum(sales_orders.mapped('amount_total'))
        total_cost = sum(sales_orders.mapped('total_cost'))

        # Top customers
        customer_data = {}
        for sale in sales_orders:
            customer = sale.partner_id
            if customer.id not in customer_data:
                customer_data[customer.id] = {
                    'name': customer.name,
                    'revenue': 0,
                    'order_count': 0
                }
            customer_data[customer.id]['revenue'] += sale.amount_total
            customer_data[customer.id]['order_count'] += 1

        top_customers = sorted(
            customer_data.values(),
            key=lambda x: x['revenue'],
            reverse=True
        )[:10]

        return {
            'total_revenue': total_revenue,
            'total_cost': total_cost,
            'gross_profit': total_revenue - total_cost,
            'gross_profit_margin': ((total_revenue - total_cost) / total_revenue * 100) if total_revenue else 0,
            'order_count': len(sales_orders),
            'average_order_value': total_revenue / len(sales_orders) if sales_orders else 0,
            'top_customers': top_customers,
        }

    def _get_cash_flow_metrics(self, date_from, date_to):
        """Lấy cash flow metrics"""
        domain = [
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('company_id', '=', self.env.company.id),
            ('state', '=', 'posted'),
        ]

        moves = self.env['account.move'].search(domain)

        cash_in = 0
        cash_out = 0

        for move in moves:
            for line in move.line_ids:
                if line.account_id.internal_type in ('receivable', 'payable', 'liquidity'):
                    if line.balance > 0:  # Debit
                        cash_out += line.balance
                    else:  # Credit
                        cash_in += abs(line.balance)

        net_cash_flow = cash_in - cash_out

        return {
            'cash_inflows': cash_in,
            'cash_outflows': cash_out,
            'net_cash_flow': net_cash_flow,
            'cash_flow_ratio': cash_in / cash_out if cash_out > 0 else 0,
        }

# Add this to account.move model for inventory integration
class AccountMove(models.Model):
    _inherit = 'account.move'

    # Additional fields for supply chain integration
    stock_picking_id = fields.Many2one('stock.picking', string='Stock Picking')
    mrp_production_id = fields.Many2one('mrp.production', string='Production Order')
    total_cost = fields.Float(string='Total Cost', help='COGS for customer invoices')
    cost_breakdown = fields.Text(string='Cost Breakdown')

    def action_post(self):
        """Override post để xử lý supply chain integration"""
        result = super().action_post()

        # Xử lý inventory valuation cho customer invoices
        if self.move_type == 'out_invoice':
            self._update_inventory_valuation()

        # Xử lý costing cho supplier invoices
        elif self.move_type == 'in_invoice':
            self._update_supplier_costing()

        return result

    def _update_inventory_valuation(self):
        """Cập nhật inventory valuation khi bán hàng"""
        for line in self.invoice_line_ids:
            if line.product_id and line.product_id.type == 'product':
                # Lấy stock move tương ứng
                stock_move = self.env['stock.move'].search([
                    ('sale_line_id', 'in', line.sale_line_ids.ids),
                    ('state', '=', 'done')
                ], limit=1)

                if stock_move:
                    # Cập nhật stock valuation
                    stock_move.stock_valuation_layer_ids.write({
                        'account_move_id': self.id,
                        'remaining_value': stock_move.stock_valuation_layer_ids.remaining_value,
                    })

    def _update_supplier_costing(self):
        """Cập nhật costing khi nhận hàng"""
        if self.stock_picking_id:
            # Cập nhật standard cost cho products
            for line in self.invoice_line_ids:
                if line.product_id:
                    # Calculate landed cost
                    landed_cost = line.price_unit

                    # Update standard cost if higher than current
                    current_cost = line.product_id.standard_price
                    if landed_cost > current_cost:
                        line.product_id.write({
                            'standard_price': landed_cost
                        })
```

## 🔧 Advanced Integration Examples

### Example 7: Period-End Closing Automation

```python
class PeriodEndClosing(models.Model):
    _name = 'period.end.closing'
    _description = 'Period End Closing'
    _order = 'date_end desc'

    name = fields.Char(string='Reference', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                default=lambda self: self.env.company)
    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('review', 'Review'),
        ('posted', 'Posted'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft')

    closing_move_ids = fields.One2many('account.move', 'closing_id',
                                     string='Closing Journal Entries')

    def action_start_closing(self):
        """Bắt đầu process period-end closing"""
        self.write({'state': 'in_progress'})

        # Create all closing entries
        self._create_closing_entries()

        self.write({'state': 'review'})

        return {
            'type': 'ir.actions.act_window',
            'name': _('Period End Closing'),
            'res_model': 'period.end.closing',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current'
        }

    def _create_closing_entries(self):
        """Tạo tất cả closing journal entries"""
        entries = self.env['account.move']

        # 1. Revenue and expense closing
        revenue_entry = self._create_revenue_closing_entry()
        expense_entry = self._create_expense_closing_entry()

        if revenue_entry:
            entries |= revenue_entry
        if expense_entry:
            entries |= expense_entry

        # 2. Inventory valuation adjustment
        inventory_entry = self._create_inventory_adjustment_entry()
        if inventory_entry:
            entries |= inventory_entry

        # 3. Fixed asset depreciation
        depreciation_entry = self._create_depreciation_entry()
        if depreciation_entry:
            entries |= depreciation_entry

        # 4. Currency revaluation
        revaluation_entry = self._create_currency_revaluation_entry()
        if revaluation_entry:
            entries |= revaluation_entry

        self.closing_move_ids = entries

    def _create_revenue_closing_entry(self):
        """Tạo revenue closing entry"""
        # Get revenue accounts
        revenue_accounts = self.env['account.account'].search([
            ('company_id', '=', self.company_id.id),
            ('internal_type', '=', 'other'),
            ('user_type_id.include_initial_balance', '=', True),
        ])

        total_revenue = 0
        lines = []

        for account in revenue_accounts:
            # Get trial balance for this period
            balance = self._get_account_balance(account, self.date_start, self.date_end)

            if balance < 0:  # Revenue accounts have credit balance
                revenue_amount = abs(balance)
                total_revenue += revenue_amount

                lines.append((0, 0, {
                    'account_id': account.id,
                    'debit': revenue_amount,
                    'name': _('Close revenue account %s') % account.code,
                }))

        if not lines:
            return None

        # Add closing account (debit)
        closing_account = self.company_id.closing_account_id or \
                        self.env['account.account'].search([
                            ('company_id', '=', self.company_id.id),
                            ('code', '=', '999999')
                        ], limit=1)

        if closing_account:
            lines.append((0, 0, {
                'account_id': closing_account.id,
                'credit': total_revenue,
                'name': _('Close revenue accounts'),
            }))

        journal_entry = self.env['account.move'].create({
            'journal_id': self.company_id.closing_journal_id.id,
            'date': self.date_end,
            'ref': self.name + ' - Revenue Closing',
            'line_ids': lines,
            'move_type': 'entry',
            'company_id': self.company_id.id,
            'closing_id': self.id,
        })

        return journal_entry

    def _create_expense_closing_entry(self):
        """Tạo expense closing entry"""
        # Get expense accounts
        expense_accounts = self.env['account.account'].search([
            ('company_id', '=', self.company_id.id),
            ('internal_type', '=', 'other'),
            ('user_type_id.include_initial_balance', '=', True),
        ])

        total_expense = 0
        lines = []

        for account in expense_accounts:
            # Get trial balance for this period
            balance = self._get_account_balance(account, self.date_start, self.date_end)

            if balance > 0:  # Expense accounts have debit balance
                expense_amount = balance
                total_expense += expense_amount

                lines.append((0, 0, {
                    'account_id': account.id,
                    'credit': expense_amount,
                    'name': _('Close expense account %s') % account.code,
                }))

        if not lines:
            return None

        # Add closing account (credit)
        closing_account = self.company_id.closing_account_id or \
                        self.env['account.account'].search([
                            ('company_id', '=', self.company_id.id),
                            ('code', '=', '999999')
                        ], limit=1)

        if closing_account:
            lines.append((0, 0, {
                'account_id': closing_account.id,
                'debit': total_expense,
                'name': _('Close expense accounts'),
            }))

        journal_entry = self.env['account.move'].create({
            'journal_id': self.company_id.closing_journal_id.id,
            'date': self.date_end,
            'ref': self.name + ' - Expense Closing',
            'line_ids': lines,
            'move_type': 'entry',
            'company_id': self.company_id.id,
            'closing_id': self.id,
        })

        return journal_entry

    def _create_inventory_adjustment_entry(self):
        """Tạo inventory adjustment entry"""
        # Get inventory variance accounts
        variance_accounts = self.env['account.account'].search([
            ('company_id', '=', self.company_id.id),
            ('name', 'ilike', 'variance%'),
            ('name', 'ilike', 'inventory%'),
        ])

        if not variance_accounts:
            return None

        total_variance = 0
        lines = []

        for account in variance_accounts:
            balance = self._get_account_balance(account, self.date_start, self.date_end)

            if abs(balance) > 0.01:
                total_variance += balance
                lines.append((0, 0, {
                    'account_id': account.id,
                    'debit': balance if balance > 0 else 0,
                    'credit': abs(balance) if balance < 0 else 0,
                    'name': _('Clear inventory variance %s') % account.code,
                }))

        if not lines:
            return None

        journal_entry = self.env['account.move'].create({
            'journal_id': self.company_id.inventory_journal_id.id,
            'date': self.date_end,
            'ref': self.name + ' - Inventory Variance',
            'line_ids': lines,
            'move_type': 'entry',
            'company_id': self.company_id.id,
            'closing_id': self.id,
        })

        return journal_entry

    def _create_depreciation_entry(self):
        """Tạo depreciation entry"""
        # Get fixed assets requiring depreciation
        assets = self.env['account.asset'].search([
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'open'),
            ('depreciation_type', '=', 'linear'),
        ])

        if not assets:
            return None

        total_depreciation = 0
        lines = []

        for asset in assets:
            # Calculate depreciation for this period
            depreciation_amount = asset._compute_depreciation_amount(
                self.date_start, self.date_end
            )

            if depreciation_amount > 0:
                total_depreciation += depreciation_amount

                lines.append((0, 0, {
                    'account_id': asset.category_id.account_depreciation_id.id,
                    'debit': depreciation_amount,
                    'name': _('Depreciation for %s') % asset.name,
                    'asset_id': asset.id,
                }))

                lines.append((0, 0, {
                    'account_id': asset.category_id.account_expense_depreciation_id.id,
                    'credit': depreciation_amount,
                    'name': _('Depreciation for %s') % asset.name,
                    'asset_id': asset.id,
                }))

        if not lines:
            return None

        journal_entry = self.env['account.move'].create({
            'journal_id': self.company_id.miscellaneous_journal_id.id,
            'date': self.date_end,
            'ref': self.name + ' - Depreciation',
            'line_ids': lines,
            'move_type': 'entry',
            'company_id': self.company_id.id,
            'closing_id': self.id,
        })

        return journal_entry

    def _create_currency_revaluation_entry(self):
        """Tạo currency revaluation entry"""
        # Use existing currency revaluation logic
        currencies = self.env['res.currency'].search([
            ('id', '!=', self.company_id.currency_id.id)
        ])

        entries = self.env['account.move']

        for currency in currencies:
            currency_entries = currency._create_currency_revaluation_entries(
                currency, self.date_end
            )
            if currency_entries:
                currency_entries.write({'closing_id': self.id})
                entries |= currency_entries

        return entries

    def _get_account_balance(self, account, date_from, date_to):
        """Lấy balance của account trong khoảng thời gian"""
        domain = [
            ('account_id', '=', account.id),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'posted'),
        ]

        lines = self.env['account.move.line'].search(domain)
        return sum(lines.mapped('balance'))

    def action_post_entries(self):
        """Post tất cả closing entries"""
        for entry in self.closing_move_ids:
            if entry.state != 'posted':
                entry.action_post()

        self.write({'state': 'posted'})

        self.message_post(
            body=_('All closing entries have been posted for period %s to %s') %
            (self.date_start, self.date_end)
        )

        return True

    def action_review_entries(self):
        """Review tất cả closing entries"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Review Closing Entries'),
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('closing_id', '=', self.id)],
            'target': 'current'
        }
```

## 🔗 Integration Testing Examples

### Example 8: Comprehensive Supply Chain Accounting Tests

```python
class TestSupplyChainAccounting(TransactionCase):

    def setUp(self):
        super().setUp()

        # Create test data
        self.partner_vendor = self.env['res.partner'].create({
            'name': 'Test Vendor',
            'supplier_rank': 1,
        })

        self.partner_customer = self.env['res.partner'].create({
            'name': 'Test Customer',
            'customer_rank': 1,
        })

        self.product_raw = self.env['product.product'].create({
            'name': 'Raw Material',
            'type': 'product',
            'cost_method': 'fifo',
            'standard_price': 100,
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'uom_po_id': self.env.ref('uom.product_uom_unit').id,
        })

        self.product_finished = self.env['product.product'].create({
            'name': 'Finished Product',
            'type': 'product',
            'cost_method': 'fifo',
            'standard_price': 200,
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'uom_po_id': self.env.ref('uom.product_uom_unit').id,
        })

        # Set up accounts
        self.account_expense = self.env['account.account'].search([
            ('internal_type', '=', 'expense'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)

        self.account_revenue = self.env['account.account'].search([
            ('internal_type', '=', 'income'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)

    def test_purchase_to_pay_workflow(self):
        """Test complete purchase-to-pay workflow"""
        # 1. Create Purchase Order
        purchase = self.env['purchase.order'].create({
            'partner_id': self.partner_vendor.id,
            'order_line': [(0, 0, {
                'product_id': self.product_raw.id,
                'product_qty': 100,
                'price_unit': 100,
                'name': 'Test Raw Material',
            })]
        })

        # 2. Confirm PO
        purchase.button_confirm()
        self.assertEqual(purchase.state, 'purchase')

        # 3. Receive goods
        picking = purchase.picking_ids
        self.assertEqual(len(picking), 1)

        # Validate receipt
        picking.button_validate()
        self.assertEqual(picking.state, 'done')

        # 4. Create supplier invoice
        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_vendor.id,
            'purchase_order_id': purchase.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_raw.id,
                'quantity': 100,
                'price_unit': 100,
                'name': 'Test Raw Material',
                'account_id': self.account_expense.id,
            })]
        })

        # 5. Three-way matching
        result = invoice.action_three_way_matching()
        self.assertEqual(result['status'], 'matched')

        # 6. Post invoice
        invoice.action_post()
        self.assertEqual(invoice.state, 'posted')

        # 7. Verify inventory valuation
        quants = self.env['stock.quant'].search([
            ('product_id', '=', self.product_raw.id)
        ])
        total_quantity = sum(quants.mapped('quantity'))
        self.assertEqual(total_quantity, 100)

    def test_manufacturing_cost_accounting(self):
        """Test manufacturing cost accounting"""
        # 1. Create BOM
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_finished.product_tmpl_id.id,
            'bom_line_ids': [(0, 0, {
                'product_id': self.product_raw.id,
                'product_qty': 2,
            })]
        })

        # 2. Receive raw materials
        receipt = self.env['stock.picking'].create({
            'partner_id': self.partner_vendor.id,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.env.ref('stock.stock_location_stock').id,
            'move_ids': [(0, 0, {
                'name': 'Raw Material Receipt',
                'product_id': self.product_raw.id,
                'product_uom': self.env.ref('uom.product_uom_unit').id,
                'product_uom_qty': 200,
                'location_id': self.env.ref('stock.stock_location_suppliers').id,
                'location_dest_id': self.env.ref('stock.stock_location_stock').id,
            })]
        })

        receipt.button_validate()

        # 3. Create Manufacturing Order
        production = self.env['mrp.production'].create({
            'product_id': self.product_finished.id,
            'product_qty': 50,
            'bom_id': bom.id,
        })

        production.action_confirm()
        production.action_assign()

        # 4. Consume materials
        production.move_raw_ids._action_done()

        # 5. Record production
        production.button_mark_done()
        self.assertEqual(production.state, 'done')

        # 6. Verify cost calculation
        self.assertGreater(production.actual_material_cost, 0)
        self.assertGreater(production.total_actual_cost, 0)

        # 7. Verify journal entries
        self.assertTrue(production.accounting_entries_posted)

    def test_sales_to_cash_workflow(self):
        """Test complete sales-to-cash workflow"""
        # 1. Create product with cost
        self.product_raw.write({'qty_available': 100})

        # 2. Create Sales Order
        sale = self.env['sale.order'].create({
            'partner_id': self.partner_customer.id,
            'order_line': [(0, 0, {
                'product_id': self.product_raw.id,
                'product_uom_qty': 10,
                'price_unit': 150,
                'name': 'Test Sale',
            })]
        })

        # 3. Confirm sale
        sale.action_confirm()
        self.assertEqual(sale.state, 'sale')

        # 4. Deliver goods
        delivery = sale.picking_ids
        self.assertEqual(len(delivery), 1)

        delivery.button_validate()
        self.assertEqual(delivery.state, 'done')

        # 5. Create customer invoice
        invoice = sale._create_invoices()
        invoice = self.env['account.move'].browse(invoice)

        invoice.action_post()
        self.assertEqual(invoice.state, 'posted')

        # 6. Create payment
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_customer.id,
            'amount': invoice.amount_total,
            'journal_id': self.env['account.journal'].search([
                ('type', '=', 'bank'),
                ('company_id', '=', self.env.company.id)
            ], limit=1).id,
        })

        payment.action_post()
        self.assertEqual(payment.state, 'posted')

        # 7. Reconcile invoice and payment
        lines = (invoice.line_ids + payment.move_line_ids).filtered(
            lambda l: l.account_id.reconcile
        )

        lines.reconcile()
        self.assertTrue(lines.mapped('reconciled'))

    def test_currency_revaluation(self):
        """Test multi-currency revaluation"""
        # Create foreign currency
        foreign_currency = self.env['res.currency'].create({
            'name': 'Test Currency',
            'symbol': 'TEST',
            'rate': 1.5,
        })

        # Create customer invoice in foreign currency
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_customer.id,
            'currency_id': foreign_currency.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_finished.id,
                'quantity': 10,
                'price_unit': 150,
                'account_id': self.account_revenue.id,
            })]
        })

        invoice.action_post()

        # Update exchange rate
        foreign_currency.write({'rate': 1.6})

        # Create revaluation entries
        entries = foreign_currency._create_currency_revaluation_entries(
            foreign_currency, fields.Date.today()
        )

        self.assertGreater(len(entries), 0)

        # Verify revaluation amount
        revaluation_amount = sum(
            entry.line_ids.filtered(lambda l: l.account_id ==
            self.env.company.income_currency_exchange_account_id)
            .mapped('credit')
        )

        # Expected gain: 10 * 150 * (1.6 - 1.5) = 150
        self.assertAlmostEqual(revaluation_amount, 150.0, places=2)

# Performance Test Class
class TestAccountingPerformance(TransactionCase):

    def test_large_volume_invoicing(self):
        """Test performance with large volume of invoices"""
        # Create 1000 invoice lines
        lines = []
        for i in range(1000):
            lines.append((0, 0, {
                'name': 'Test Line %d' % i,
                'quantity': 1,
                'price_unit': 100,
                'account_id': self.env['account.account'].search([
                    ('internal_type', '=', 'income'),
                    ('company_id', '=', self.env.company.id)
                ], limit=1).id,
            }))

        # Measure creation time
        import time
        start_time = time.time()

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.env['res.partner'].create({'name': 'Test Customer'}).id,
            'invoice_line_ids': lines
        })

        creation_time = time.time() - start_time

        # Performance assertions
        self.assertLess(creation_time, 5.0, "Invoice creation should take less than 5 seconds")
        self.assertEqual(len(invoice.invoice_line_ids), 1000)

        # Test posting performance
        start_time = time.time()
        invoice.action_post()
        posting_time = time.time() - start_time

        self.assertLess(posting_time, 10.0, "Invoice posting should take less than 10 seconds")
        self.assertEqual(invoice.state, 'posted')
```

---

**Module Status**: 📝 **IN PROGRESS**
**File Size**: ~10,000 từ
**Language**: Tiếng Việt
**Target Audience**: Developers, Accountants, Financial Managers
**Completion**: 2025-11-08

*File này cung cấp các ví dụ code thực tế cho accounting module integration với supply chain, bao gồm purchase-to-pay, manufacturing cost accounting, sales-to-cash workflows, và multi-currency management với Vietnamese business terminology.*