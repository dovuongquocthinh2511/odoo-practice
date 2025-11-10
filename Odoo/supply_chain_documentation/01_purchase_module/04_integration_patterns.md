# 🔗 Integration Patterns - Cross-Module Architecture

## 🎯 Giới Thiệu

Documentation chi tiết về các patterns integration giữa Purchase module và các modules khác trong Odoo 18. Hướng dẫn này bao gồm Inventory integration, Accounting integration, Vendor Management integration, và các custom integration patterns.

## 📊 Integration Architecture Overview

### Integration Ecosystem
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PURCHASE INTEGRATION LAYER                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Purchase Module  │  Stock Module  │  Accounting  │  Vendor Management   │
│  (Core Logic)     │  (Inventory)   │  (Finance)   │  (Partner Relations)  │
│                   │               │             │                      │
│  ┌─────────────┐  │ ┌───────────┐ │ ┌──────────┐ │ ┌────────────────┐ │
│  │ RFQ→PO Flow │◄┼►│ Receipt   │◄┼►│ Invoicing│◄┼►│ Performance     │ │
│  │ Approvals   │  │ │ Picking   │ │ │ Payment  │ │ │ Tracking        │ │
│  │ State Mgmt  │  │ │ QC Process│ │ │ Matching │ │ │ Pricelist      │ │
│  └─────────────┘  │ └───────────┘ │ └──────────┘ │ └────────────────┘ │
│         │           │             │           │            │             │
│         └───────────┴─────────────┴───────────┴────────────┘             │
│                   │             │           │            │             │
│  ┌────────────────────────────────────────────────────────────────┐     │
│  │              DATA EXCHANGE & EVENTS                         │     │
│  │  • Purchase Requisition → Purchase Order                 │     │
│  │  • MRP Requirements → Purchase Planning                  │     │
│  │  • Sales Order → Dropshipping Purchase Order            │     │
│  │  • Invoice → Payment Processing                           │     │
│  │  • Quality Control → Quality Notifications                │     │
│  └────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 🏢 Inventory Integration Patterns

### 1. Stock Movement Creation

#### **Integration Flow**: Purchase → Stock Picking → Stock Moves

**Core Integration Pattern**:
```python
# File: purchase_stock/models/purchase_order.py
from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    picking_ids = fields.One2many('stock.picking', 'purchase_id', 'Receipts')
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Deliver To',
        domain=[('code', '=', 'incoming')]
    )

    def _create_picking(self):
        """
        Tạo Stock Picking khi PO confirmed
        Integration point giữa Purchase và Stock modules
        """
        for order in self:
            if not order._should_create_picking():
                continue

            # Get appropriate picking type
            picking_type = order.picking_type_id or order._get_default_picking_type()

            # Create picking with integrated data
            picking_vals = {
                'partner_id': order.partner_id.id,
                'origin': order.name,
                'picking_type_id': picking_type.id,
                'location_id': picking_type.default_location_src_id.id,
                'location_dest_id': picking_type.default_location_dest_id.id,
                'company_id': order.company_id.id,
                'purchase_id': order.id,  # Link back to PO
                'move_ids_without_package': order._prepare_stock_moves(),
            }

            picking = self.env['stock.picking'].create(picking_vals)
            picking.action_confirm()

            # Link picking to PO
            order.picking_ids = [(4, picking.id)]

    def _prepare_stock_moves(self):
        """
        Chuẩn bị Stock Moves từ PO lines
        Complex integration logic với nhiều business rules
        """
        moves = []
        StockMove = self.env['stock.move']

        for line in self.order_line:
            # Skip non-stockable products
            if not line._should_create_stock_move():
                continue

            # Get procurement method based on product type and route
            procure_method = line._get_procure_method()

            # Determine locations based on dropship/inbound
            location_id, location_dest_id = line._get_move_locations()

            move_vals = {
                'name': self.name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.product_qty,
                'product_uom': line.product_uom.id,
                'date': line.date_planned,
                'date_expected': line.date_planned,
                'location_id': location_id.id,
                'location_dest_id': location_dest_id.id,
                'picking_type_id': self.picking_type_id.id,
                'procure_method': procure_method,
                'origin': self.name,
                'company_id': self.company_id.id,
                'purchase_line_id': line.id,  # Important: Link back to PO line
                'group_id': self.group_id.id,
                'propagate_cancel': True,
                'propagate_date': True,
                'propagate_date_minimum_delta': 1,
            }

            # Add procurement group if needed
            if self.group_id:
                move_vals['group_id'] = self.group_id.id

            # Add analytic distribution if applicable
            if line.account_analytic_id:
                move_vals['analytic_distribution'] = {
                    str(line.account_analytic_id.id): 100.0
                }

            moves.append((0, 0, move_vals))

        return moves

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _should_create_stock_move(self):
        """
        Business logic để quyết định có tạo stock move không
        """
        self.ensure_one()

        # Rule 1: Product must be stockable
        if self.product_id.type not in ['product', 'consu']:
            return False

        # Rule 2: Not dropshipping
        if self.order_id.dest_address_id:
            return False

        # Rule 3: Check service products with delivery
        if self.product_id.type == 'service' and self.product_id.service_to_purchase:
            return True

        # Rule 4: Check for kit/bom products
        if self.product_id.bom_count > 0 and not self.product_id.bom_ids.filtered(
            lambda b: b.type == 'phantom'
        ):
            return True

        return True

    def _get_procure_method(self):
        """
        Xác định procurement method cho stock move
        """
        if self.product_id.type == 'consu':
            return 'make_to_stock'
        elif self.order_id._is_dropship():
            return 'make_to_order'
        elif self.product_id.seller_ids and self.product_id.seller_ids[0].delay:
            return 'make_to_order'
        else:
            return 'make_to_stock'

    def _get_move_locations(self):
        """
        Xác định source và destination locations
        """
        # Default inbound locations
        picking_type = self.order_id.picking_type_id

        if self.order_id.dest_address_id:
            # Dropshipping
            source_location = picking_type.default_location_src_id
            dest_location = self.env['stock.location'].search([
                ('usage', '=', 'customer'),
                ('partner_id', '=', self.order_id.dest_address_id.id)
            ], limit=1)
        else:
            # Standard inbound
            source_location = picking_type.default_location_src_id
            dest_location = picking_type.default_location_dest_id

        return source_location, dest_location
```

### 2. Quality Control Integration

#### **Integration Pattern**: Purchase → Quality Control → Stock

**Quality Check Automation**:
```python
# File: purchase_stock/models/stock_picking.py
from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    purchase_id = fields.Many2one('purchase.order', 'Purchase Order')
    quality_check_ids = fields.One2many('quality.check', 'picking_id', 'Quality Checks')

    def action_done(self):
        """
        Override để thực hiện quality checks trước khi done picking
        """
        # Quality Control Integration
        if self.picking_type_id.code == 'incoming' and self.purchase_id:
            self._create_quality_checks()
            self._validate_quality_checks()

        # Standard picking completion
        res = super().action_done()

        # Update PO quantities after successful receipt
        if self.purchase_id:
            self._update_purchase_quantities()

        return res

    def _create_quality_checks(self):
        """
        Tự động tạo quality checks dựa trên product và vendor settings
        """
        QualityCheck = self.env['quality.check']

        for move in self.move_ids:
            if move.state != 'done':
                continue

            # Get quality points for this product
            quality_points = self.env['quality.point'].search([
                ('product_id', '=', move.product_id.id),
                ('picking_type_id', '=', self.picking_type_id.id),
            ])

            # Get vendor-specific quality requirements
            vendor_quality_points = self.env['quality.point'].search([
                ('partner_id', '=', self.partner_id.id),
                ('product_id', '=', move.product_id.id),
            ])

            all_points = quality_points + vendor_quality_points

            for point in all_points:
                check_vals = {
                    'point_id': point.id,
                    'product_id': move.product_id.id,
                    'picking_id': self.id,
                    'company_id': self.company_id.id,
                    'user_id': self.env.user.id,
                    'quality_state': 'none',
                    'creation_date': fields.Datetime.now(),
                }

                # Add reference to PO line for traceability
                if move.purchase_line_id:
                    check_vals['purchase_line_id'] = move.purchase_line_id.id

                QualityCheck.create(check_vals)

    def _validate_quality_checks(self):
        """
        Validate quality checks với business rules
        """
        required_checks = self.quality_check_ids.filtered(
            lambda c: c.point_id.quality_team_id
        )

        if required_checks:
            # Check if all required checks are completed
            incomplete_checks = required_checks.filtered(
                lambda c: c.quality_state == 'none'
            )

            if incomplete_checks:
                raise UserError(
                    "Cần hoàn thành tất cả quality checks trước khi hoàn thành receipt!"
                )

            # Check for failed quality checks
            failed_checks = self.quality_check_ids.filtered(
                lambda c: c.quality_state == 'fail'
            )

            if failed_checks:
                self._handle_quality_failures(failed_checks)

    def _handle_quality_failures(self, failed_checks):
        """
        Xử lý quality failures với workflow options
        """
        # Create quality alert
        for check in failed_checks:
            self.env['quality.alert'].create({
                'product_id': check.product_id.id,
                'picking_id': self.id,
                'check_id': check.id,
                'user_id': self.env.user.id,
                'team_id': check.point_id.quality_team_id.id,
                'description': f"Quality check failed for {check.product_id.name}",
            })

        # Notify quality team
        team = self.env['quality.alert.team'].search([
            ('picking_type_ids', 'in', [self.picking_type_id.id])
        ], limit=1)

        if team:
            team.message_post(
                body=_("Quality checks failed for receipt %s") % self.name,
                message_type='notification',
                subtype_xmlid='mail.mt_comment',
            )

        # Option to block receipt or continue with warning
        if self.company_id.quality_block_receipt:
            raise UserError(
                "Receipt blocked due to quality failures. "
                "Please resolve quality issues before proceeding."
            )
```

### 3. Inventory Valuation Integration

#### **Integration Pattern**: Purchase → Accounting (Stock Valuation)

**Cost Calculation Integration**:
```python
# File: purchase_stock/models/product.py
from odoo import models, fields, api

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _compute_average_price(self):
        """
        Cập nhật average cost dựa trên purchase orders
        Integration với inventory valuation
        """
        for product in self:
            if product.valuation != 'real_time':
                continue

            # Get latest purchase price
            latest_po = self.env['purchase.order.line'].search([
                ('product_id', '=', product.id),
                ('order_id.state', '=', 'purchase'),
                ('price_unit', '>', 0)
            ], order='order_id.date_approve desc, id desc', limit=1)

            if latest_po:
                # Update standard price with latest purchase price
                company_currency = product.env.company_id.currency_id
                po_currency = latest_po.order_id.currency_id

                # Convert to company currency if needed
                if po_currency != company_currency:
                    price_in_company_currency = latest_po.price_unit * \
                        po_currency.rate / company_currency.rate
                else:
                    price_in_company_currency = latest_po.price_unit

                # Update standard price if significant difference
                current_price = product.standard_price
                price_change_percent = abs(
                    (price_in_company_currency - current_price) / current_price * 100
                ) if current_price else 100

                # Update if price change exceeds threshold
                threshold = product.env.company_id.purchase_price_update_threshold or 5
                if price_change_percent >= threshold:
                    product.write({
                        'standard_price': price_in_company_currency
                    })

                    # Log price update
                    product.message_post(
                        body=_("Standard price updated to %s based on latest purchase price") %
                        price_in_company_currency,
                        message_type='notification'
                    )
```

## 💰 Accounting Integration Patterns

### 1. Invoice Generation Integration

#### **Integration Flow**: Purchase Receipt → Invoice → Payment

**Three-Way Matching Implementation**:
```python
# File: purchase_account/models/account_move.py
from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    purchase_id = fields.Many2one('purchase.order', 'Purchase Order')
    purchase_vendor_bill_id = fields.Many2one('purchase.bill.union', 'Vendor Bill')
    purchase_order_count = fields.Integer(compute='_compute_origin_po_count')

    def _onchange_purchase_auto_complete(self):
        """
        Auto-complete invoice từ Purchase Order
        Integration logic cho invoice generation
        """
        if not self.purchase_id:
            return

        purchase = self.purchase_id

        # Set partner and currency from PO
        self.partner_id = purchase.partner_id
        self.currency_id = purchase.currency_id

        # Auto-complete invoice lines
        self._sync_purchase_lines()

        # Set invoice date and due date
        self.invoice_date = fields.Date.today()
        if purchase.partner_id.property_supplier_payment_term_id:
            self.invoice_payment_term_id = purchase.partner_id.property_supplier_payment_term_id.id

    def _sync_purchase_lines(self):
        """
        Đồng bộ PO lines sang invoice lines với business rules
        """
        if not self.purchase_id:
            return

        # Clear existing lines
        self.invoice_line_ids.unlink()

        # Create invoice lines from PO lines
        for po_line in self.purchase_id.order_line:
            # Skip lines that shouldn't be invoiced
            if not po_line._should_be_invoiced():
                continue

            # Calculate invoice quantity
            invoice_qty = self._get_invoice_quantity(po_line)

            if invoice_qty <= 0:
                continue

            # Determine tax
            taxes = po_line.taxes_id.filtered(
                lambda t: t.company_id.id == self.company_id.id
            )

            # Create invoice line
            line_vals = {
                'move_id': self.id,
                'purchase_line_id': po_line.id,
                'product_id': po_line.product_id.id,
                'name': po_line.name,
                'quantity': invoice_qty,
                'product_uom_id': po_line.product_uom.id,
                'price_unit': po_line.price_unit,
                'tax_ids': [(6, 0, taxes.ids)],
                'account_id': po_line._get_account_id(),
                'analytic_distribution': po_line.analytic_distribution or {},
            }

            self.env['account.move.line'].create(line_vals)

    def _get_invoice_quantity(self, po_line):
        """
        Xác định số lượng invoice dựa trên company policy
        """
        company = self.company_id

        if company.po_invoice_policy == 'ordered':
            return po_line.product_qty
        elif company.po_invoice_policy == 'received':
            return po_line.qty_received
        else:  # delivered
            return po_line.qty_delivered or po_line.qty_received

    def action_post(self):
        """
        Override để thực hiện three-way matching trước khi post
        """
        if self.purchase_id:
            self._validate_three_way_matching()
            self._update_purchase_status()

        return super().action_post()

    def _validate_three_way_matching(self):
        """
        Three-way matching validation
        """
        purchase = self.purchase_id

        # 1. Quantity matching
        for line in self.invoice_line_ids:
            if line.purchase_line_id:
                po_line = line.purchase_line_id
                tolerance = self.company_id.po_quantity_tolerance or 0.05

                # Check if quantity is within tolerance
                if abs(line.quantity - po_line.qty_received) > (po_line.qty_received * tolerance):
                    raise UserError(
                        f"Invoice quantity ({line.quantity}) for {line.product_id.name} "
                        f"differs from received quantity ({po_line.qty_received}) "
                        f"beyond tolerance ({tolerance*100}%)"
                    )

        # 2. Price matching
        for line in self.invoice_line_ids:
            if line.purchase_line_id:
                po_line = line.purchase_line_id
                tolerance = self.company_id.po_price_tolerance or 0.1

                if abs(line.price_unit - po_line.price_unit) > (po_line.price_unit * tolerance):
                    raise UserError(
                        f"Invoice price ({line.price_unit}) for {line.product_id.name} "
                        f"differs from PO price ({po_line.price_unit}) "
                        f"beyond tolerance ({tolerance*100}%)"
                    )

    def _update_purchase_status(self):
        """
        Cập nhật trạng thái invoice status của Purchase Order
        """
        if self.purchase_id:
            self.purchase_id._get_invoiced()
```

### 2. Payment Integration

#### **Integration Pattern**: Invoice → Payment → Reconciliation

**Payment Workflow Integration**:
```python
# File: purchase_account/models/account_payment.py
from odoo import models, fields, api

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def action_post(self):
        """
        Override để tự động reconcile với vendor bills
        """
        res = super().action_post()

        # Auto-reconcile with purchase invoices
        self._auto_reconcile_vendor_bills()

        # Update Purchase Order payment status
        self._update_purchase_payment_status()

        return res

    def _auto_reconcile_vendor_bills(self):
        """
        Tự động reconcile payment với vendor bills
        """
        if not self.company_id.po_auto_reconcile_payments:
            return

        # Get unpaid vendor bills for the same partner
        vendor_bills = self.env['account.move'].search([
            ('partner_id', '=', self.partner_id.id),
            ('move_type', '=', 'in_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('company_id', '=', self.company_id.id),
        ])

        # Reconcile with oldest bills first
        for bill in vendor_bills.sorted('invoice_date'):
            if self.amount <= 0:
                break

            remaining_amount = bill.amount_residual - sum(
                bill.payment_line_ids.filtered(
                    lambda pl: pl.payment_id.id != self.id
                ).mapped('amount')
            )

            if remaining_amount <= 0:
                continue

            reconcile_amount = min(self.amount, remaining_amount)

            # Create reconciliation
            self.env['account.reconciliation.widget'].process_move_lines(
                [{
                    'id': bill.line_ids.filtered(
                        lambda l: l.account_id == self.destination_account_id
                    )[0].id,
                    'name': bill.name,
                    'debit': reconcile_amount,
                    'balance': -reconcile_amount,
                    'amount_currency': reconcile_amount,
                    'currency_id': bill.currency_id.id,
                }],
                [{
                    'id': self.move_line_ids.filtered(
                        lambda l: l.account_id == self.destination_account_id
                    )[0].id,
                    'name': self.name,
                    'credit': reconcile_amount,
                    'balance': reconcile_amount,
                    'amount_currency': reconcile_amount,
                    'currency_id': self.currency_id.id,
                }]
            )

            self.amount -= reconcile_amount

    def _update_purchase_payment_status(self):
        """
        Cập nhật trạng thái payment cho Purchase Orders
        """
        # Get related Purchase Orders from reconciled invoices
        reconciled_moves = self.reconciled_move_line_ids.mapped('move_id')
        purchase_orders = reconciled_moves.mapped('purchase_id')

        # Update payment status for each PO
        for po in purchase_orders:
            po._compute_payment_status()

class AccountMove(models.Model):
    _inherit = 'account.move'

    def _compute_payment_status(self):
        """
        Tính toán payment status cho Purchase Orders liên quan
        """
        for move in self:
            if move.move_type == 'in_invoice' and move.purchase_id:
                purchase = move.purchase_id

                # Calculate total payments
                total_payments = sum(
                    payment.amount for payment in move.payment_ids
                )

                # Update Purchase Order payment status
                if total_payments >= move.amount_total:
                    purchase.payment_status = 'paid'
                elif total_payments > 0:
                    purchase.payment_status = 'partial'
                else:
                    purchase.payment_status = 'unpaid'

                # Log payment status change
                if move.payment_state != purchase.payment_status:
                    purchase.message_post(
                        body=_("Payment status updated to %s") % purchase.payment_status,
                        message_type='notification'
                    )
```

## 🤝 Vendor Management Integration

### 1. Performance Tracking Integration

#### **Integration Pattern**: Purchase → Vendor Metrics → Analytics

**Performance Metrics Calculation**:
```python
# File: purchase_vendor/models/res_partner.py
from odoo import models, fields, api, tools

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Purchase Metrics
    po_count = fields.Integer('Purchase Orders Count', compute='_compute_po_metrics')
    po_total_amount = fields.Float('Total Purchase Amount', compute='_compute_po_metrics')
    avg_delivery_time = fields.Float('Average Delivery Time (Days)', compute='_compute_po_metrics')
    on_time_delivery_rate = fields.Float('On-Time Delivery Rate (%)', compute='_compute_po_metrics')
    quality_rating = fields.Float('Quality Rating', compute='_compute_po_metrics')
    price_competitiveness = fields.Float('Price Competitiveness', compute='_compute_po_metrics')

    @api.depends_context('uid')
    def _compute_po_metrics(self):
        """
        Tính toán vendor metrics từ Purchase Orders
        Complex calculation với nhiều business rules
        """
        for partner in self:
            if not partner.supplier_rank:
                continue

            # Get all POs for this vendor
            domain = [
                ('partner_id', '=', partner.id),
                ('state', 'in', ['purchase', 'done']),
                ('company_id', '=', partner.env.company_id.id),
            ]

            po_ids = self.env['purchase.order'].search(domain)

            # Basic metrics
            partner.po_count = len(po_ids)
            partner.po_total_amount = sum(po_ids.mapped('amount_total'))

            # Delivery performance metrics
            partner._calculate_delivery_metrics(po_ids)

            # Quality metrics
            partner._calculate_quality_metrics(po_ids)

            # Price competitiveness metrics
            partner._calculate_price_metrics(po_ids)

    def _calculate_delivery_metrics(self, po_ids):
        """
        Tính toán delivery performance metrics
        """
        completed_pos = po_ids.filtered(lambda po: po.state == 'done')

        if not completed_pos:
            self.avg_delivery_time = 0
            self.on_time_delivery_rate = 0
            return

        # Calculate average delivery time
        total_delivery_time = 0
        on_time_count = 0
        total_count = 0

        for po in completed_pos:
            # Get confirmed date and delivery date
            confirmed_date = po.date_approve
            delivery_dates = []

            # Get actual delivery dates from pickings
            for picking in po.picking_ids:
                if picking.state == 'done' and picking.date_done:
                    delivery_dates.append(picking.date_done)

            if confirmed_date and delivery_dates:
                # Calculate actual delivery time
                actual_delivery_time = max(delivery_dates) - confirmed_date
                delivery_days = actual_delivery_time.days

                total_delivery_time += delivery_days
                total_count += 1

                # Check if on-time (within planned date + buffer)
                planned_date = po.date_planned or po.date_order + timedelta(days=7)
                buffer_days = self.env.company_id.delivery_buffer_days or 2

                if actual_delivery_time <= planned_date + timedelta(days=buffer_days):
                    on_time_count += 1

        # Update metrics
        self.avg_delivery_time = total_delivery_time / total_count if total_count > 0 else 0
        self.on_time_delivery_rate = (on_time_count / total_count * 100) if total_count > 0 else 0

    def _calculate_quality_metrics(self, po_ids):
        """
        Tính toán quality performance metrics
        """
        total_checks = 0
        failed_checks = 0

        for po in po_ids:
            # Get quality checks from PO pickings
            quality_checks = self.env['quality.check'].search([
                ('picking_id.purchase_id', '=', po.id),
            ])

            total_checks += len(quality_checks)
            failed_checks += len(quality_checks.filtered(lambda c: c.quality_state == 'fail'))

        # Calculate quality rating (1-5 scale)
        if total_checks > 0:
            success_rate = ((total_checks - failed_checks) / total_checks)
            # Convert to 1-5 scale
            self.quality_rating = 1 + (success_rate * 4)
        else:
            # Default rating for vendors without quality checks
            self.quality_rating = 4.0

    def _calculate_price_metrics(self, po_ids):
        """
        Tính toán price competitiveness metrics
        """
        if not po_ids:
            self.price_competitiveness = 0
            return

        # Compare with other vendors for same products
        all_po_lines = self.env['purchase.order.line'].search([
            ('order_id.state', 'in', ['purchase', 'done']),
            ('company_id', '=', self.env.company_id.id),
        ])

        # Group by product and calculate average prices
        product_prices = {}
        for line in all_po_lines:
            product_id = line.product_id.id
            if product_id not in product_prices:
                product_prices[product_id] = {'total': 0, 'count': 0, 'prices': []}

            product_prices[product_id]['total'] += line.price_unit
            product_prices[product_id]['count'] += 1
            product_prices[product_id]['prices'].append(line.price_unit)

        # Calculate competitiveness
        vendor_lines = po_ids.mapped('order_line')
        competitiveness_scores = []

        for line in vendor_lines:
            product_id = line.product_id.id
            if product_id in product_prices and product_prices[product_id]['count'] > 1:
                avg_market_price = product_prices[product_id]['total'] / product_prices[product_id]['count']

                # Calculate competitiveness score (higher is better)
                if avg_market_price > 0:
                    score = max(0, 1 - (line.price_unit - avg_market_price) / avg_market_price)
                    competitiveness_scores.append(score)

        if competitiveness_scores:
            self.price_competitiveness = sum(competitiveness_scores) / len(competitiveness_scores) * 100
        else:
            self.price_competitiveness = 50  # Default neutral rating
```

### 2. Pricelist Integration

#### **Integration Pattern**: Vendor → Pricelist → Purchase Pricing

**Dynamic Pricing Integration**:
```python
# File: purchase_pricelist/models/purchase_order.py
from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.onchange('partner_id')
    def _onchange_partner_pricelist(self):
        """
        Cập nhật pricelist khi thay đổi vendor
        Integration với vendor pricelist system
        """
        if self.partner_id:
            # Get vendor's pricelist
            pricelist = self.partner_id.property_product_pricelist

            if pricelist:
                self.pricelist_id = pricelist

                # Apply pricelist to existing lines
                for line in self.order_line:
                    line._apply_vendor_pricelist()

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _apply_vendor_pricelist(self):
        """
        Áp dụng vendor pricelist cho line
        Complex pricing logic với quantity breaks, discounts, etc.
        """
        if not self.order_id.pricelist_id or not self.product_id:
            return

        pricelist = self.order_id.pricelist_id

        # Get base price from pricelist
        base_price = pricelist.get_product_price(
            self.product_id,
            self.product_qty,
            self.order_id.partner_id,
            uom_id=self.product_uom.id,
            date=self.order_id.date_order.date() if self.order_id.date_order else None,
        )

        if base_price is not False:
            # Apply pricelist price
            old_price = self.price_unit
            self.price_unit = base_price

            # Log price change
            if old_price != base_price:
                self.order_id.message_post(
                    body=_(
                        "Price for %s updated from %s to %s based on vendor pricelist"
                    ) % (self.product_id.name, old_price, base_price),
                    message_type='notification'
                )

        # Apply special vendor pricing rules
        self._apply_special_vendor_rules()

    def _apply_special_vendor_rules(self):
        """
        Áp dụng các quy tắc pricing đặc biệt cho vendor
        """
        vendor = self.order_id.partner_id

        # Rule 1: Volume discounts
        if vendor.volume_discount_tiers:
            discount = self._calculate_volume_discount(vendor.volume_discount_tiers)
            if discount > 0:
                self.price_unit = self.price_unit * (1 - discount / 100)

        # Rule 2: Loyalty discounts
        if self._is_loyalty_discount_applicable(vendor):
            loyalty_discount = vendor.loyalty_discount_percentage or 0
            self.price_unit = self.price_unit * (1 - loyalty_discount / 100)

        # Rule 3: Seasonal discounts
        if self._is_seasonal_discount_applicable(vendor):
            seasonal_discount = self._get_seasonal_discount(vendor)
            if seasonal_discount > 0:
                self.price_unit = self.price_unit * (1 - seasonal_discount / 100)

    def _calculate_volume_discount(self, discount_tiers):
        """
        Tính toán volume discount dựa trên tiers
        """
        for tier in sorted(discount_tiers, key=lambda x: x.min_quantity, reverse=True):
            if self.product_qty >= tier.min_quantity:
                return tier.discount_percentage
        return 0

    def _is_loyalty_discount_applicable(self, vendor):
        """
        Kiểm tra loyalty discount có áp dụng không
        """
        # Check minimum order count
        if vendor.loyalty_min_orders:
            order_count = self.env['purchase.order'].search_count([
                ('partner_id', '=', vendor.id),
                ('state', 'in', ['purchase', 'done']),
            ])
            if order_count < vendor.loyalty_min_orders:
                return False

        # Check minimum total amount
        if vendor.loyalty_min_amount:
            total_amount = self.env['purchase.order'].search([
                ('partner_id', '=', vendor.id),
                ('state', 'in', ['purchase', 'done']),
            ]).mapped('amount_total')

            if sum(total_amount) < vendor.loyalty_min_amount:
                return False

        return True
```

## 🔧 Custom Integration Patterns

### 1. Dropshipping Integration

#### **Integration Pattern**: Sales Order → Purchase Order → Customer Delivery

**Dropshipping Workflow**:
```python
# File: purchase_dropshipping/models/sale_order.py
from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _action_confirm(self):
        """
        Override để tạo dropshipping purchase orders
        """
        res = super()._action_confirm()

        # Create dropshipping purchase orders
        self._create_dropshipping_orders()

        return res

    def _create_dropshipping_orders(self):
        """
        Tạo purchase orders cho dropshipping
        Complex logic để group lines by vendor
        """
        # Group lines by vendor
        vendor_lines = {}
        for line in self.order_line:
            if not line.product_id or line.product_id.type != 'product':
                continue

            # Get preferred vendor for this product
            vendor = line._get_preferred_vendor()
            if not vendor:
                continue

            if vendor not in vendor_lines:
                vendor_lines[vendor] = []
            vendor_lines[vendor].append(line)

        # Create one PO per vendor
        for vendor, lines in vendor_lines.items():
            self._create_vendor_dropship_order(vendor, lines)

    def _create_vendor_dropship_order(self, vendor, lines):
        """
        Tạo dropshipping PO cho một vendor
        """
        PurchaseOrder = self.env['purchase.order']

        # Create PO with dropshipping configuration
        po_vals = {
            'partner_id': vendor.id,
            'dest_address_id': self.partner_shipping_id.id,  # Dropshipping
            'origin': self.name,
            'currency_id': vendor.property_purchase_currency_id.id or self.company_id.currency_id.id,
            'company_id': self.company_id.id,
            'fiscal_position_id': vendor.property_account_position_id.id,
            'payment_term_id': vendor.property_supplier_payment_term_id.id,
            'order_line': self._prepare_dropship_lines(lines, vendor),
        }

        po = PurchaseOrder.create(po_vals)

        # Confirm PO immediately for dropshipping
        po.button_confirm()

        # Link PO to Sales Order
        self.purchase_ids = [(4, po.id)]

    def _prepare_dropship_lines(self, lines, vendor):
        """
        Chuẩn bị lines cho dropshipping PO
        """
        line_vals = []

        for line in lines:
            # Get vendor pricing
            vendor_price = self._get_vendor_price(line.product_id, vendor, line.product_uom_qty)

            line_vals.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.name,
                'product_qty': line.product_uom_qty,
                'product_uom': line.product_uom.id,
                'price_unit': vendor_price,
                'taxes_id': [(6, 0, line.product_id.supplier_taxes_id.ids)],
                'date_planned': self.commitment_date or fields.Datetime.now(),
                'sale_line_id': line.id,  # Link back to sale line
                'analytic_distribution': line.analytic_distribution,
            }))

        return line_vals

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        """
        Override để handle dropshipping completion
        """
        res = super()._action_done()

        # Update sales order if dropshipping
        if self.sale_id and self.location_dest_id.usage == 'customer':
            self._process_dropshipping_delivery()

        return res

    def _process_dropshipping_delivery(self):
        """
        Xử lý hoàn thành dropshipping delivery
        """
        # Mark sales order lines as delivered
        for move in self.move_ids:
            if move.sale_line_id:
                move.sale_line_id.qty_delivered = move.product_uom_qty

        # Check if sales order is fully delivered
        if self.sale_id._check_order_fully_delivered():
            self.sale_id.action_done()
```

### 2. MRP Integration

#### **Integration Pattern**: MRP → Purchase Order → Production Planning

**Material Requirements Planning Integration**:
```python
# File: purchase_mrp/models/mrp_production.py
from odoo import models, fields, api

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    purchase_ids = fields.One2many('purchase.order', 'mrp_production_id', 'Purchase Orders')
    purchase_line_ids = fields.One2many('purchase.order.line', 'mrp_production_id', 'Purchase Lines')

    def _generate_purchase_orders(self):
        """
        Tự động tạo purchase orders cho raw materials
        Integration với MRP planning
        """
        for production in self:
            # Get components that need to be purchased
            components_to_purchase = production._get_components_to_purchase()

            if not components_to_purchase:
                continue

            # Group components by vendor
            vendor_components = production._group_components_by_vendor(components_to_purchase)

            # Create purchase orders
            for vendor, components in vendor_components.items():
                production._create_component_purchase_order(vendor, components)

    def _get_components_to_purchase(self):
        """
        Lấy components cần mua
        """
        components = []

        for move in self.move_raw_ids:
            # Check if product needs to be purchased
            if move.product_id.purchase_ok:
                # Calculate required quantity
                required_qty = move.product_uom_qty

                # Check available stock
                available_qty = move.product_id.with_context(
                    location=move.location_id.id
                ).qty_available

                # Only purchase if insufficient stock
                if available_qty < required_qty:
                    qty_to_purchase = required_qty - available_qty
                    components.append({
                        'product': move.product_id,
                        'quantity': qty_to_purchase,
                        'uom': move.product_uom,
                        'date_needed': self.date_planned_start,
                        'production_line': move,
                    })

        return components

    def _group_components_by_vendor(self, components):
        """
        Group components theo vendor để tối ưu purchase
        """
        vendor_components = {}

        for component in components:
            product = component['product']

            # Get preferred vendor
            vendor = product._get_preferred_vendor(
                quantity=component['quantity'],
                date=component['date_needed']
            )

            if not vendor:
                # Fallback to any vendor
                vendor = product.seller_ids[0].name if product.seller_ids else None

            if vendor:
                if vendor not in vendor_components:
                    vendor_components[vendor] = []
                vendor_components[vendor].append(component)

        return vendor_components

    def _create_component_purchase_order(self, vendor, components):
        """
        Tạo purchase order cho components
        """
        PurchaseOrder = self.env['purchase.order']

        # Create PO
        po_vals = {
            'partner_id': vendor.id,
            'origin': self.name,
            'company_id': self.company_id.id,
            'date_order': fields.Datetime.now(),
            'date_planned': min(comp['date_needed'] for comp in components),
            'mrp_production_id': self.id,
            'order_line': self._prepare_component_lines(components, vendor),
        }

        po = PurchaseOrder.create(po_vals)

        # Link purchase lines to production moves
        for i, component in enumerate(components):
            po_line = po.order_line[i]
            component['production_line'].purchase_line_id = po_line.id

        return po

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    mrp_production_id = fields.Many2one('mrp.production', 'Manufacturing Order')

    def button_approve(self, force=False):
        """
        Override để update MRP khi PO được duyệt
        """
        res = super().button_approve(force=force)

        # Update MRP production if this is component purchase
        if self.mrp_production_id:
            self.mrp_production_id._update_component_availability()

        return res

    def _create_picking(self):
        """
        Override để handle MRP components delivery
        """
        res = super()._create_picking()

        # If this is MRP component purchase, update availability
        if self.mrp_production_id:
            for picking in self.picking_ids:
                picking.mrp_production_id = self.mrp_production_id

        return res

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    mrp_production_id = fields.Many2one('mrp.production', 'Manufacturing Order')

    def action_done(self):
        """
        Override để trigger MRP production khi components được nhận
        """
        res = super().action_done()

        # Update MRP production component availability
        if self.mrp_production_id and self.state == 'done':
            self.mrp_production_id._check_component_availability()

        return res
```

## 📊 Integration Monitoring & Debugging

### 1. Integration Health Monitoring

#### **Integration Status Tracking**:
```python
# File: purchase_integration_monitoring/models/purchase_integration.py
from odoo import models, fields, api

class PurchaseIntegrationMonitor(models.Model):
    _name = 'purchase.integration.monitor'
    _description = 'Purchase Integration Monitor'
    _order = 'created_at desc'

    name = fields.Char('Monitor Name', required=True)
    integration_type = fields.Selection([
        ('stock', 'Stock Integration'),
        ('accounting', 'Accounting Integration'),
        ('vendor', 'Vendor Integration'),
        ('mrp', 'MRP Integration'),
        ('dropship', 'Dropshipping Integration'),
    ], 'Integration Type', required=True)

    status = fields.Selection([
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('pending', 'Pending'),
    ], 'Status', required=True, default='pending')

    error_message = fields.Text('Error Message')
    source_record = fields.Reference('Source Record', selection='_get_models')
    target_record = fields.Reference('Target Record', selection='_get_models')
    execution_time = fields.Float('Execution Time (seconds)')
    created_at = fields.Datetime('Created At', default=fields.Datetime.now)

    @api.model
    def _get_models(self):
        """Get dynamic model selection"""
        models = self.env['ir.model'].search([])
        return [(m.model, m.name) for m in models]

    def log_integration(self, integration_type, status, source_record=None,
                       target_record=None, error_message=None, execution_time=0):
        """Log integration event"""
        vals = {
            'name': f"{integration_type} - {fields.Datetime.now()}",
            'integration_type': integration_type,
            'status': status,
            'source_record': f"{source_record._name},{source_record.id}" if source_record else None,
            'target_record': f"{target_record._name},{target_record.id}" if target_record else None,
            'error_message': error_message,
            'execution_time': execution_time,
        }

        return self.create(vals)

class PurchaseIntegrationHealth(models.Model):
    _name = 'purchase.integration.health'
    _description = 'Purchase Integration Health Dashboard'

    integration_type = fields.Selection([
        ('stock', 'Stock Integration'),
        ('accounting', 'Accounting Integration'),
        ('vendor', 'Vendor Integration'),
    ], 'Integration Type')

    success_count = fields.Integer('Success Count', compute='_compute_health_metrics')
    error_count = fields.Integer('Error Count', compute='_compute_health_metrics')
    warning_count = fields.Integer('Warning Count', compute='_compute_health_metrics')
    last_success = fields.Datetime('Last Success', compute='_compute_health_metrics')
    last_error = fields.Datetime('Last Error', compute='_compute_health_metrics')
    avg_execution_time = fields.Float('Avg Execution Time', compute='_compute_health_metrics')

    @api.depends('integration_type')
    def _compute_health_metrics(self):
        """Calculate health metrics"""
        for record in self:
            monitors = self.env['purchase.integration.monitor'].search([
                ('integration_type', '=', record.integration_type),
                ('created_at', '>=', fields.Datetime.now() - timedelta(days=7))
            ])

            record.success_count = len(monitors.filtered(lambda m: m.status == 'success'))
            record.error_count = len(monitors.filtered(lambda m: m.status == 'error'))
            record.warning_count = len(monitors.filtered(lambda m: m.status == 'warning'))

            success_monitors = monitors.filtered(lambda m: m.status == 'success')
            record.last_success = max(success_monitors.mapped('created_at')) if success_monitors else None

            error_monitors = monitors.filtered(lambda m: m.status == 'error')
            record.last_error = max(error_monitors.mapped('created_at')) if error_monitors else None

            if monitors:
                record.avg_execution_time = sum(monitors.mapped('execution_time')) / len(monitors)
```

### 2. Integration Debugging Tools

#### **Integration Debug Helper**:
```python
# File: purchase_integration_tools/models/purchase_integration_debug.py
from odoo import models, fields, api
import json

class PurchaseIntegrationDebug(models.Model):
    _name = 'purchase.integration.debug'
    _description = 'Purchase Integration Debug Tools'

    name = fields.Char('Debug Session', required=True)
    purchase_order_id = fields.Many2one('purchase.order', 'Purchase Order')
    debug_data = fields.Text('Debug Data')
    created_at = fields.Datetime('Created At', default=fields.Datetime.now)

    def debug_stock_integration(self):
        """Debug stock integration"""
        po = self.purchase_order_id
        debug_info = {
            'purchase_order': {
                'id': po.id,
                'name': po.name,
                'state': po.state,
                'partner_id': po.partner_id.name,
                'date_order': po.date_order,
            },
            'stock_moves': [],
            'pickings': [],
            'issues': [],
        }

        # Check stock moves
        for line in po.order_line:
            moves = self.env['stock.move'].search([
                ('purchase_line_id', '=', line.id)
            ])

            for move in moves:
                move_info = {
                    'id': move.id,
                    'product': move.product_id.name,
                    'quantity': move.product_uom_qty,
                    'state': move.state,
                    'source_location': move.location_id.name,
                    'dest_location': move.location_dest_id.name,
                    'picking': move.picking_id.name if move.picking_id else None,
                }
                debug_info['stock_moves'].append(move_info)

        # Check pickings
        for picking in po.picking_ids:
            picking_info = {
                'id': picking.id,
                'name': picking.name,
                'state': picking.state,
                'moves_count': len(picking.move_ids),
                'backorder_exists': bool(picking.backorder_id),
            }
            debug_info['pickings'].append(picking_info)

        # Identify issues
        if po.state == 'purchase' and not po.picking_ids:
            debug_info['issues'].append("No pickings created for confirmed PO")

        for line in po.order_line:
            if line.product_id.type == 'product' and line.qty_received == 0:
                debug_info['issues'].append(f"Product {line.product_id.name} not received")

        self.debug_data = json.dumps(debug_info, indent=2, default=str)
        return True

    def debug_accounting_integration(self):
        """Debug accounting integration"""
        po = self.purchase_order_id
        debug_info = {
            'purchase_order': {
                'id': po.id,
                'name': po.name,
                'amount_total': po.amount_total,
                'currency': po.currency_id.name,
            },
            'invoices': [],
            'account_moves': [],
            'payments': [],
            'issues': [],
        }

        # Check invoices
        invoices = self.env['account.move'].search([
            ('purchase_id', '=', po.id)
        ])

        for invoice in invoices:
            invoice_info = {
                'id': invoice.id,
                'name': invoice.name,
                'state': invoice.state,
                'move_type': invoice.move_type,
                'amount_total': invoice.amount_total,
                'payment_state': invoice.payment_state,
            }
            debug_info['invoices'].append(invoice_info)

            # Check payment reconciliation
            for payment in invoice.payment_ids:
                payment_info = {
                    'id': payment.id,
                    'amount': payment.amount,
                    'state': payment.state,
                    'payment_date': payment.payment_date,
                }
                debug_info['payments'].append(payment_info)

        # Identify issues
        if po.state == 'done' and po.invoice_status != 'invoiced':
            debug_info['issues'].append("PO completed but not fully invoiced")

        for line in po.order_line:
            if line.qty_received > line.qty_invoiced:
                debug_info['issues'].append(
                    f"More received ({line.qty_received}) than invoiced ({line.qty_invoiced}) for {line.product_id.name}"
                )

        self.debug_data = json.dumps(debug_info, indent=2, default=str)
        return True

    def run_health_check(self):
        """Run comprehensive integration health check"""
        po = self.purchase_order_id

        health_status = {
            'overall_status': 'healthy',
            'checks': [],
            'recommendations': [],
        }

        # Check 1: Stock Integration
        stock_issues = []
        if po.state == 'purchase' and not po.picking_ids:
            stock_issues.append("No pickings created")

        if stock_issues:
            health_status['checks'].append({
                'type': 'stock',
                'status': 'error',
                'issues': stock_issues,
            })
            health_status['overall_status'] = 'warning'
        else:
            health_status['checks'].append({
                'type': 'stock',
                'status': 'ok',
                'message': 'Stock integration working correctly',
            })

        # Check 2: Accounting Integration
        accounting_issues = []
        if po.state == 'done' and po.invoice_status == 'no':
            accounting_issues.append("PO completed but no invoices created")

        if accounting_issues:
            health_status['checks'].append({
                'type': 'accounting',
                'status': 'error',
                'issues': accounting_issues,
            })
            health_status['overall_status'] = 'warning'
        else:
            health_status['checks'].append({
                'type': 'accounting',
                'status': 'ok',
                'message': 'Accounting integration working correctly',
            })

        # Check 3: Data Consistency
        consistency_issues = []
        total_po_qty = sum(po.order_line.mapped('product_qty'))
        total_received_qty = sum(po.order_line.mapped('qty_received'))

        if total_po_qty != total_received_qty and po.state == 'done':
            consistency_issues.append(f"Quantity mismatch: PO={total_po_qty}, Received={total_received_qty}")

        if consistency_issues:
            health_status['checks'].append({
                'type': 'consistency',
                'status': 'error',
                'issues': consistency_issues,
            })
            health_status['overall_status'] = 'warning'

        self.debug_data = json.dumps(health_status, indent=2, default=str)
        return True
```

---

**Next Steps**: Đọc [05_code_examples.md](05_code_examples.md) để xem practical implementation examples.