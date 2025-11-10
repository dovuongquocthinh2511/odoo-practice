# 🔗 Module Sales - Integration Patterns & Cross-Module Connectivity

## 🎯 Giới Thiệu

Tài liệu này mô tả chi tiết các patterns tích hợp của Sales module với các modules khác trong Odoo 18, bao gồm Inventory Management, Accounting, CRM, và các external systems. Các integration patterns này đảm bảo luồng dữ liệu liền mạch và tự động hóa các quy trình kinh doanh.

## 📊 Integration Architecture Overview

### Cross-Module Data Flow
```
┌─────────────────────────────────────────────────────────────────┐
│                     SALES MODULE INTEGRATION                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   CRM/Lead  │ →  │ Sales Order │ →  │ Inventory   │         │
│  │ Management  │    │ Creation    │    │ Management  │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│          ↓                   ↓                   ↓             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │ Opportunity │ →  │ Order       │ →  │ Stock       │         │
│  │ Management  │    │ Fulfillment  │    │ Movement    │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│          ↓                   ↓                   ↓             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │ Quotation   │ →  │ Invoice     │ →  │ Accounting   │         │
│  │ Processing  │    │ Generation  │    │ Integration  │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

## 🔄 CRM Integration Patterns

### 1. Lead to Sales Order Conversion

#### Lead Management Integration
```python
class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def action_new_quotation(self):
        """
        Tạo báo giá từ khách hàng tiềm năng
        - Tự động tạo partner nếu chưa có
        - Lưu thông tin marketing campaign
        - Tạo quote với thông tin từ lead
        """
        self.ensure_one()

        # Tạo hoặc sử dụng partner
        if not self.partner_id:
            self._handle_partner_assignment()

        # Tạo quotation với context từ lead
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'campaign_id': self.campaign_id.id,
            'medium_id': self.medium_id.id,
            'source_id': self.source_id.id,
            'team_id': self.team_id.id,
            'company_id': self.company_id.id,
        })

        # Tích hợp thông tin chi tiết từ lead
        if self.description:
            sale_order.note = self.description

        # Copy tags từ lead
        if self.tag_ids:
            sale_order.tag_ids = self.tag_ids

        return {
            'name': 'sale_order_form',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'type': 'ir.actions.act_window',
            'context': {'form_view_initial_mode': 'edit'},
        }

    def _create_customer_from_lead(self):
        """
        Tạo customer từ lead với thông tin đầy đủ
        """
        return self.env['res.partner'].create({
            'name': self.contact_name,
            'email': self.email_from,
            'phone': self.phone,
            'mobile': self.mobile,
            'street': self.street,
            'city': self.city,
            'state_id': self.state_id.id,
            'country_id': self.country_id.id,
            'function': self.function,
            'title': self.title.id,
            'company_type': self.company_type,
            'user_id': self.user_id.id,
            'team_id': self.team_id.id,
        })
```

#### Opportunity to Sales Order Integration
```python
class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def action_new_quotation(self):
        """
        Tạo quotation từ opportunity với thông tin chi tiết
        """
        self.ensure_one()

        # Tạo sales order với thông tin từ opportunity
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'campaign_id': self.campaign_id.id,
            'medium_id': self.medium_id.id,
            'source_id': self.source_id.id,
            'team_id': self.team_id.id,
            'company_id': self.company_id.id,
            'opportunity_id': self.id,
            'expected_revenue': self.expected_revenue,
            'probability': self.probability,
        })

        # Tự động thêm các sản phẩm liên quan đến opportunity
        self._add_recommended_products(sale_order)

        return {
            'name': 'sale_order_form',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'type': 'ir.actions.act_window',
        }

    def _add_recommended_products(self, sale_order):
        """
        Thêm sản phẩm được đề xuất dựa trên opportunity
        """
        # Logic để đề xuất sản phẩm dựa trên industry, size, etc.
        # Có thể tích hợp với AI recommendation engine
        pass
```

### 2. Customer Synchronization

#### Real-time Customer Data Sync
```python
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True,
        change_default=True
    )

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """
        Cập nhật thông tin tự động khi thay đổi customer
        - Load thông tin payment terms
        - Áp dụng pricing list
        - Cập nhật shipping address
        - Load lịch sử mua hàng
        """
        if self.partner_id:
            # Payment terms
            self.payment_term_id = self.partner_id.property_payment_term_id

            # Pricelist
            self.pricelist_id = self.partner_id.property_product_pricelist

            # Shipping address
            if self.partner_id.child_ids:
                delivery_addresses = self.partner_id.child_ids.filtered(
                    lambda p: p.type == 'delivery'
                )
                if delivery_addresses:
                    self.partner_shipping_id = delivery_addresses[0]
                else:
                    self.partner_shipping_id = self.partner_id
            else:
                self.partner_shipping_id = self.partner_id

            # Invoice address
            self.partner_invoice_id = self.partner_id

            # Load team
            if self.partner_id.team_id:
                self.team_id = self.partner_id.team_id

    @api.onchange('partner_shipping_id')
    def _onchange_partner_shipping_id(self):
        """
        Cập nhật thông tin khi thay đổi shipping address
        - Cập nhật fiscal position
        - Áp dụng taxes phù hợp
        """
        if self.partner_shipping_id:
            self.fiscal_position_id = self.env['account.fiscal.position'].get_fiscal_position(
                self.partner_id,
                self.partner_shipping_id
            )

            # Re-compute taxes and prices
            for line in self.order_line:
                line._onchange_product_id()
```

## 🏭 Inventory Integration Patterns

### 1. Stock Management Integration

#### Automatic Stock Reservation
```python
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """
        Xác nhận đơn hàng và xử lý inventory
        - Check stock availability
        - Reserve stock
        - Create delivery orders
        - Update forecasts
        """
        # Kiểm tra stock availability
        self._check_stock_availability()

        # Reserve stock
        self._reserve_stock()

        # Tạo delivery orders
        pickings = self._create_picking()

        # Update stock forecasts
        self._update_forecast()

        return super(SaleOrder, self).action_confirm()

    def _check_stock_availability(self):
        """
        Kiểm tra tính khả dụng của stock cho tất cả lines
        """
        for line in self.order_line:
            if line.product_id.type in ['product', 'consu']:
                available_qty = line._get_available_quantity()
                if line.product_uom_qty > available_qty:
                    # Xử lý trường hợp không đủ stock
                    self._handle_insufficient_stock(line, available_qty)

    def _reserve_stock(self):
        """
        Reserve stock cho confirmed orders
        """
        for line in self.order_line:
            if line.product_id.type in ['product', 'consu']:
                line._reserve_stock()

    def _create_picking(self):
        """
        Tạo delivery orders
        """
        pickings = self.env['stock.picking']

        for order in self:
            if order.state not in ['draft', 'sent', 'cancel']:
                # Create picking cho từng line
                for line in order.order_line:
                    if line.product_id.type in ['product', 'consu']:
                        picking = line._create_picking()
                        pickings |= picking

        return pickings

    def _update_forecast(self):
        """
        Cập nhật stock forecast sau khi xác nhận đơn hàng
        """
        for line in self.order_line:
            if line.product_id.type == 'product':
                # Update virtual stock
                self.env['stock.quant']._update_available_quantity(
                    line.product_id,
                    line.warehouse_id.lot_stock_id,
                    -line.product_uom_qty
                )
```

#### Multi-Warehouse Integration
```python
class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        related='order_id.warehouse_id',
        store=True,
        readonly=True
    )

    def _get_stock_move_values(self, picking_id, group_id):
        """
        Tạo stock move values với warehouse-specific logic
        """
        self.ensure_one()
        return {
            'name': self.name[:100] if self.name else '/',
            'product_id': self.product_id.id,
            'product_uom_qty': self.product_uom_qty,
            'product_uom': self.product_uom.id,
            'date_expected': self.order_id.commitment_date or self.order_id.date_order,
            'location_id': self.order_id.warehouse_id.lot_stock_id.id,
            'location_dest_id': self.order_id.partner_shipping_id.property_stock_customer.id,
            'picking_id': picking_id,
            'partner_id': self.order_id.partner_id.id,
            'state': 'draft',
            'group_id': group_id,
            'sale_line_id': self.id,
            'origin': self.order_id.name,
            'company_id': self.order_id.company_id.id,
        }

    def _get_available_quantity(self):
        """
        Lấy available quantity từ correct warehouse
        """
        if self.warehouse_id:
            location = self.warehouse_id.lot_stock_id
        else:
            location = self.env['stock.warehouse']._get_default_warehouse().lot_stock_id

        return self.env['stock.quant']._get_available_quantity(
            self.product_id,
            location,
            lot_id=self.lot_id,
            owner_id=self.order_id.partner_id,
            package_id=self.package_id
        )
```

### 2. Stock Movement Integration

#### Real-time Stock Updates
```python
class StockPicking(models.Model):
    _inherit = 'stock.picking'

    sale_id = fields.Many2one('sale.order', string='Sales Order', ondelete='cascade')

    def button_validate(self):
        """
        Validate picking và cập nhật sales order
        - Update delivered quantities
        - Create invoice if needed
        - Update stock values
        """
        result = super(StockPicking, self).button_validate()

        # Update sales order line delivered quantities
        self._update_sale_order_lines()

        # Auto create invoice if configured
        if self.sale_id and self.sale_id.invoice_shipping_on_delivery:
            self.sale_id._create_invoices(grouped=False, final=False)

        return result

    def _update_sale_order_lines(self):
        """
        Cập nhật delivered quantities trên sale order lines
        """
        for move in self.move_lines:
            if move.sale_line_id:
                # Update delivered quantity
                delivered_qty = move.sale_line_id.qty_delivered + move.product_uom_qty
                move.sale_line_id.qty_delivered = delivered_qty

                # Update line status
                if delivered_qty >= move.sale_line_id.product_uom_qty:
                    move.sale_line_id.state = 'done'
                elif delivered_qty > 0:
                    move.sale_line_id.state = 'sale'

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    qty_delivered = fields.Float(
        string='Delivered',
        compute='_compute_qty_delivered',
        store=True,
        copy=False
    )

    @api.depends('move_ids.state', 'move_ids.product_uom_qty', 'move_ids.product_uom')
    def _compute_qty_delivered(self):
        """
        Tính delivered quantity từ stock moves
        """
        for line in self:
            delivered_qty = 0.0
            for move in line.move_ids:
                if move.state == 'done':
                    if move.product_uom == line.product_uom:
                        delivered_qty += move.product_uom_qty
                    else:
                        delivered_qty += move.product_uom._compute_quantity(
                            move.product_uom_qty,
                            line.product_uom
                        )
            line.qty_delivered = delivered_qty
```

## 💰 Accounting Integration Patterns

### 1. Invoice Generation Integration

#### Automatic Invoice Creation
```python
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    invoice_ids = fields.One2many(
        'account.move',
        'invoice_origin',
        string='Invoices',
        copy=False
    )

    def _create_invoices(self, grouped=False, final=False):
        """
        Tạo invoices từ sales orders với business rules
        - Handle multiple picking scenarios
        - Apply correct fiscal positions
        - Calculate taxes correctly
        - Handle advance payments
        """
        moves = self.order_line._get_moves_to_invoice(final)
        if not moves:
            return self.env['account.move']

        # Create invoices from moves
        invoices = moves._action_done()._create_invoices(final)

        # Update invoice information
        for invoice in invoices:
            # Link to sales order
            invoice.invoice_origin = self.name
            invoice.partner_id = self.partner_id.id
            invoice.payment_reference = self.client_order_ref or self.name

            # Set fiscal position
            invoice.fiscal_position_id = self.fiscal_position_id

            # Set payment terms
            invoice.invoice_payment_term_id = self.payment_term_id.id

            # Add sales team information
            invoice.team_id = self.team_id.id

        return invoices

    def action_invoice_create(self, grouped=False, final=False):
        """
        Action method for invoice creation
        """
        invoices = self._create_invoices(grouped, final)

        # Post invoices if configured
        if self.company_id.invoice_auto_post:
            invoices.action_post()

        return {
            'name': 'account_invoice_action_customer_form',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': invoices[0].id if invoices else False,
            'type': 'ir.actions.act_window',
        }

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _get_moves_to_invoice(self, final):
        """
        Lấy stock moves để tạo invoice
        """
        # Logic để xác định哪些 moves cần invoice
        # Consider order policy (order/shipping)
        # Consider final billing
        # Consider partial invoicing
        moves = self.env['stock.move']

        for move in self.move_ids:
            if self.order_id.invoice_policy == 'order':
                # Invoice based on order
                if not final or move.state == 'done':
                    moves |= move
            else:  # shipping
                # Invoice based on shipping
                if move.state == 'done':
                    moves |= move

        return moves
```

#### Tax Integration
```python
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.depends('order_line.price_total', 'order_line.tax_id')
    def _compute_amount(self):
        """
        Tính totals với proper tax calculation
        """
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax

            order.amount_untaxed = amount_untaxed
            order.amount_tax = amount_tax
            order.amount_total = amount_untaxed + amount_tax

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Tính line amounts với proper tax calculation
        """
        for line in self:
            price = line._get_display_price()

            # Apply discount
            if line.discount:
                price = price * (1 - line.discount / 100.0)

            # Calculate taxes
            taxes = line.tax_id.compute_all(
                price,
                line.product_uom_qty,
                line.product_id,
                line.order_id.partner_id
            )

            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    def _get_display_price(self):
        """
        Get display price with pricelist logic
        """
        if self.order_id.pricelist_id and self.product_id:
            # Get price from pricelist
            price = self.order_id.pricelist_id._get_product_price(
                self.product_id,
                self.product_uom_qty,
                self.order_id.partner_id,
                self.product_uom,
                self.order_id.date_order
            )
        else:
            # Get standard price
            price = self.product_id.lst_price

        return price
```

### 2. Payment Integration

#### Payment Term Integration
```python
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    payment_term_id = fields.Many2one(
        'account.payment.term',
        string='Payment Terms',
        domain=[('discount', '=', False)],
        default=lambda self: self.env['res.company']._get_default_company_id().default_sale_payment_term_id
    )

    @api.onchange('partner_id')
    def _onchange_partner_payment_term(self):
        """
        Update payment terms when partner changes
        """
        if self.partner_id:
            self.payment_term_id = self.partner_id.property_supplier_payment_term_id

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def action_validate_invoice_payment(self):
        """
        Validate payment và update sales order status
        """
        result = super(AccountPayment, self).action_validate_invoice_payment()

        # Update sales order when payment is validated
        for invoice in self.invoice_ids:
            if invoice.invoice_origin:
                # Find related sales orders
                orders = self.env['sale.order'].search([
                    ('name', '=', invoice.invoice_origin)
                ])

                # Update order status if all invoices are paid
                for order in orders:
                    if order._is_fully_paid():
                        order.write({'state': 'sale'})

        return result
```

## 🌐 External System Integration

### 1. E-commerce Integration

#### Website Integration
```python
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    website_id = fields.Many2one('website', string='Website')
    cart_quantity = fields.Integer(compute='_compute_cart_quantity')

    def _compute_cart_quantity(self):
        """
        Tính số lượng sản phẩm trong giỏ hàng
        """
        for order in self:
            order.cart_quantity = sum(order.order_line.mapped('product_uom_qty'))

    @api.model
    def _get_sales_order(self, order_id=None, access_token=None):
        """
        Lấy sales order cho website với security
        """
        domain = []
        if order_id:
            domain.append(('id', '=', order_id))
        if access_token:
            domain.append(('access_token', '=', access_token))

        return self.search(domain, limit=1)

    def action_confirm_order_frontend(self):
        """
        Confirm order từ frontend
        """
        # Additional validation for frontend orders
        self._validate_frontend_order()

        # Create payment if configured
        if self.website_id.payment_acquirer_id:
            payment = self._create_website_payment()

        return self.action_confirm()

    def _validate_frontend_order(self):
        """
        Validation logic cho frontend orders
        """
        # Validate stock availability
        # Validate payment method
        # Validate shipping method
        # Validate customer information
        pass

    def _create_website_payment(self):
        """
        Tạo payment transaction cho website orders
        """
        return self.env['payment.transaction'].create({
            'acquirer_id': self.website_id.payment_acquirer_id.id,
            'type': 'form',
            'amount': self.amount_total,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'sale_order_id': self.id,
            'state': 'draft',
        })
```

### 2. API Integration

#### REST API Endpoints
```python
from odoo import http
from odoo.http import request, JsonRequest, Response
import json

class SaleAPIController(http.Controller):

    @http.route('/api/sales/orders', type='json', auth='user', methods=['POST'])
    def create_sales_order(self, **kwargs):
        """
        API endpoint để tạo sales order
        """
        try:
            # Validate input
            self._validate_order_data(kwargs)

            # Create sales order
            order = request.env['sale.order'].sudo().create(kwargs)

            # Optional: Auto-confirm order
            if kwargs.get('auto_confirm', False):
                order.action_confirm()

            return {
                'status': 'success',
                'order_id': order.id,
                'order_reference': order.name,
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
            }

    @http.route('/api/sales/orders/<int:order_id>', type='json', auth='user', methods=['GET'])
    def get_sales_order(self, order_id, **kwargs):
        """
        API endpoint để lấy sales order information
        """
        try:
            order = request.env['sale.order'].sudo().browse(order_id)

            if not order.exists():
                return {
                    'status': 'error',
                    'message': 'Order not found',
                }

            return {
                'status': 'success',
                'order': self._serialize_order(order),
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
            }

    def _validate_order_data(self, data):
        """
        Validate sales order data
        """
        required_fields = ['partner_id', 'order_line']

        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

    def _serialize_order(self, order):
        """
        Serialize sales order data for API response
        """
        return {
            'id': order.id,
            'name': order.name,
            'state': order.state,
            'partner_id': order.partner_id.id,
            'partner_name': order.partner_id.name,
            'amount_total': order.amount_total,
            'date_order': order.date_order.isoformat(),
            'order_line': [
                {
                    'product_id': line.product_id.id,
                    'product_name': line.product_id.name,
                    'quantity': line.product_uom_qty,
                    'price_unit': line.price_unit,
                    'price_total': line.price_total,
                }
                for line in order.order_line
            ],
        }

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def create_from_api(self, order_data):
        """
        Create sales order from API data with proper validation
        """
        # Validate partner
        partner = self.env['res.partner'].browse(order_data.get('partner_id'))
        if not partner.exists():
            raise ValueError('Invalid partner ID')

        # Validate products
        for line_data in order_data.get('order_line', []):
            product = self.env['product.product'].browse(line_data.get('product_id'))
            if not product.exists():
                raise ValueError(f'Invalid product ID: {line_data.get("product_id")}')

        # Create order
        return self.create(order_data)
```

### 3. EDI Integration

#### Electronic Data Interchange
```python
class EDIIntegration(models.AbstractModel):
    _name = 'edi.integration.base'
    _description = 'EDI Integration Base'

    def generate_edi_order(self, sale_order):
        """
        Generate EDI 850 Purchase Order format
        """
        edi_data = {
            'transaction_set': '850',
            'control_number': self._generate_control_number(),
            'date': fields.Date.today().strftime('%Y%m%d'),
            'time': fields.Datetime.now().strftime('%H%M'),
            'sender': self.env.company.edi_identifier,
            'receiver': sale_order.partner_id.edi_identifier,
            'order': {
                'po_number': sale_order.client_order_ref or sale_order.name,
                'order_date': sale_order.date_order.strftime('%Y%m%d'),
                'partner': {
                    'name': sale_order.partner_id.name,
                    'address': self._format_address(sale_order.partner_shipping_id),
                },
                'lines': [
                    self._format_line_edi(line)
                    for line in sale_order.order_line
                ],
                'totals': {
                    'subtotal': sale_order.amount_untaxed,
                    'tax': sale_order.amount_tax,
                    'total': sale_order.amount_total,
                },
            }
        }

        return self._format_edi_message(edi_data)

    def _format_line_edi(self, line):
        """
        Format order line for EDI
        """
        return {
            'line_number': line.sequence,
            'product': {
                'sku': line.product_id.default_code,
                'description': line.name,
                'quantity': line.product_uom_qty,
                'uom': line.product_uom.name,
                'unit_price': line.price_unit,
            },
            'pricing': {
                'subtotal': line.price_subtotal,
                'tax': line.price_tax,
                'total': line.price_total,
            },
        }

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_send_edi(self):
        """
        Gửi EDI message cho partner
        """
        for order in self:
            if order.partner_id.edi_enabled:
                edi_message = self.env['edi.integration.base'].generate_edi_order(order)
                self._send_edi_via_ftp(edi_message, order.partner_id)

    def _send_edi_via_ftp(self, message, partner):
        """
        Send EDI message via FTP
        """
        # Implementation cho FTP/SFTP transfer
        pass
```

## 🔧 Advanced Integration Patterns

### 1. Event-Driven Architecture

#### Event Bus Integration
```python
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def write(self, vals):
        """
        Override write để trigger events
        """
        old_state = self.state
        result = super(SaleOrder, self).write(vals)

        # Trigger state change events
        if 'state' in vals and vals['state'] != old_state:
            self._trigger_state_change_event(old_state, vals['state'])

        return result

    def _trigger_state_change_event(self, old_state, new_state):
        """
        Trigger events cho các modules khác
        """
        event_data = {
            'order_id': self.id,
            'old_state': old_state,
            'new_state': new_state,
            'partner_id': self.partner_id.id,
            'amount_total': self.amount_total,
            'timestamp': fields.Datetime.now(),
        }

        # Publish event to bus
        self.env['bus.bus']._sendone(
            'sale_order',
            'state_changed',
            event_data
        )

        # Trigger specific actions based on state
        if new_state == 'sale':
            self._trigger_order_confirmed()
        elif new_state == 'done':
            self._trigger_order_completed()

    def _trigger_order_confirmed(self):
        """
        Actions khi order được xác nhận
        """
        # Notify inventory system
        self.env['bus.bus']._sendone(
            'inventory',
            'reserve_stock',
            {
                'order_id': self.id,
                'lines': [
                    {
                        'product_id': line.product_id.id,
                        'quantity': line.product_uom_qty,
                        'warehouse': self.warehouse_id.id,
                    }
                    for line in self.order_line
                    if line.product_id.type == 'product'
                ]
            }
        )

        # Notify accounting system
        self.env['bus.bus']._sendone(
            'accounting',
            'prepare_billing',
            {
                'order_id': self.id,
                'partner_id': self.partner_id.id,
                'amount': self.amount_total,
                'terms': self.payment_term_id.id,
            }
        )
```

### 2. Multi-Company Integration

#### Cross-Company Order Processing
```python
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    def action_confirm(self):
        """
        Xử lý multi-company scenarios
        """
        if self._is_intercompany_order():
            return self._process_intercompany_order()
        else:
            return super(SaleOrder, self).action_confirm()

    def _is_intercompany_order(self):
        """
        Kiểm tra có phải inter-company order
        """
        # Logic để xác định inter-company orders
        return False

    def _process_intercompany_order(self):
        """
        Xử lý inter-company orders
        - Tạo purchase order ở company khác
        - Sync inventory giữa companies
        - Handle cross-company accounting
        """
        # Tạo purchase order ở target company
        target_company = self._get_target_company()

        purchase_order = self.env['purchase.order'].sudo().with_company(target_company).create({
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'company_id': target_company.id,
            'order_line': [
                (0, 0, {
                    'product_id': line.product_id.id,
                    'product_qty': line.product_uom_qty,
                    'price_unit': line.price_unit,
                    'name': line.name,
                })
                for line in self.order_line
            ],
        })

        purchase_order.sudo().button_confirm()

        # Link orders
        self.inter_company_purchase_id = purchase_order
        purchase_order.inter_company_sale_id = self

        return True
```

### 3. Real-time Synchronization

#### WebSocket Integration
```python
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """
        Real-time synchronization khi xác nhận order
        """
        result = super(SaleOrder, self).action_confirm()

        # Send real-time updates
        self._send_realtime_updates()

        return result

    def _send_realtime_updates(self):
        """
        Gửi real-time updates qua WebSocket
        """
        # Update inventory in real-time
        self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'sale.order.confirmed',
            {
                'order_id': self.id,
                'order_reference': self.name,
                'customer': self.partner_id.name,
                'amount': self.amount_total,
                'timestamp': fields.Datetime.now().isoformat(),
            }
        )

        # Update sales dashboard
        self.env['bus.bus']._sendone(
            'dashboard',
            'sales.update',
            {
                'type': 'order_confirmed',
                'order_id': self.id,
                'amount': self.amount_total,
                'customer': self.partner_id.name,
            }
        )

        # Notify inventory team
        self.env['bus.bus']._sendone(
            'inventory_team',
            'new_order',
            {
                'order_id': self.id,
                'warehouse': self.warehouse_id.name,
                'lines': [
                    {
                        'product': line.product_id.name,
                        'quantity': line.product_uom_qty,
                        'availability': line._get_available_quantity(),
                    }
                    for line in self.order_line
                    if line.product_id.type == 'product'
                ],
            }
        )
```

## 📊 Integration Monitoring & Analytics

### 1. Performance Monitoring

#### Integration Performance Metrics
```python
class IntegrationMetrics(models.Model):
    _name = 'sale.integration.metrics'
    _description = 'Sales Integration Performance Metrics'

    order_id = fields.Many2one('sale.order', string='Sales Order')
    integration_type = fields.Selection([
        ('inventory', 'Inventory'),
        ('accounting', 'Accounting'),
        ('crm', 'CRM'),
        ('external', 'External System'),
    ], string='Integration Type')

    start_time = fields.Datetime(string='Start Time')
    end_time = fields.Datetime(string='End Time')
    duration = fields.Float(string='Duration (seconds)', compute='_compute_duration')
    status = fields.Selection([
        ('success', 'Success'),
        ('error', 'Error'),
        'timeout', 'Timeout'),
    ], string='Status')

    error_message = fields.Text(string='Error Message')
    data_volume = fields.Integer(string='Data Volume (records)')

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        """
        Tính duration của integration
        """
        for metric in self:
            if metric.start_time and metric.end_time:
                metric.duration = (metric.end_time - metric.start_time).total_seconds()

    @api.model
    def create_metrics(self, order_id, integration_type, start_time, end_time, status, error_message=None, data_volume=0):
        """
        Tạo metrics record
        """
        return self.create({
            'order_id': order_id,
            'integration_type': integration_type,
            'start_time': start_time,
            'end_time': end_time,
            'status': status,
            'error_message': error_message,
            'data_volume': data_volume,
        })

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """
        Monitor integration performance
        """
        start_time = fields.Datetime.now()

        try:
            result = super(SaleOrder, self).action_confirm()
            end_time = fields.Datetime.now()

            # Record inventory integration metrics
            self.env['sale.integration.metrics'].create_metrics(
                self.id, 'inventory', start_time, end_time, 'success', data_volume=len(self.order_line)
            )

            return result

        except Exception as e:
            end_time = fields.Datetime.now()

            # Record error metrics
            self.env['sale.integration.metrics'].create_metrics(
                self.id, 'inventory', start_time, end_time, 'error', str(e)
            )

            raise
```

### 2. Data Quality Monitoring

#### Integration Data Validation
```python
class IntegrationValidator(models.AbstractModel):
    _name = 'integration.validator.base'
    _description = 'Integration Data Validator'

    def validate_sales_order_data(self, order_data):
        """
        Validate sales order data trước khi integration
        """
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': [],
        }

        # Validate required fields
        required_fields = ['partner_id', 'order_line']
        for field in required_fields:
            if field not in order_data or not order_data[field]:
                validation_results['errors'].append(f"Missing required field: {field}")
                validation_results['valid'] = False

        # Validate partner
        if 'partner_id' in order_data:
            partner = self.env['res.partner'].browse(order_data['partner_id'])
            if not partner.exists():
                validation_results['errors'].append("Invalid partner ID")
                validation_results['valid'] = False

        # Validate order lines
        if 'order_line' in order_data:
            for line in order_data['order_line']:
                if 'product_id' not in line or not line['product_id']:
                    validation_results['errors'].append("Missing product_id in order line")
                    validation_results['valid'] = False
                    continue

                product = self.env['product.product'].browse(line['product_id'])
                if not product.exists():
                    validation_results['errors'].append(f"Invalid product ID: {line['product_id']}")
                    validation_results['valid'] = False

        # Business rule validations
        validation_results['warnings'].extend(self._validate_business_rules(order_data))

        return validation_results

    def _validate_business_rules(self, order_data):
        """
        Validate business rules
        """
        warnings = []

        # Check minimum order amount
        if 'amount_total' in order_data:
            min_amount = self.env.company.minimum_order_amount or 0
            if order_data['amount_total'] < min_amount:
                warnings.append(f"Order amount below minimum: {min_amount}")

        # Check credit limit
        if 'partner_id' in order_data:
            partner = self.env['res.partner'].browse(order_data['partner_id'])
            if partner.credit_limit and 'amount_total' in order_data:
                available_credit = partner.credit_limit - partner.credit
                if order_data['amount_total'] > available_credit:
                    warnings.append("Order exceeds available credit")

        return warnings

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def validate_for_integration(self):
        """
        Validate order data cho external integration
        """
        validator = self.env['integration.validator.base']

        order_data = {
            'partner_id': self.partner_id.id,
            'order_line': [
                {
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_uom_qty,
                    'price_unit': line.price_unit,
                }
                for line in self.order_line
            ],
            'amount_total': self.amount_total,
        }

        validation_result = validator.validate_sales_order_data(order_data)

        if not validation_result['valid']:
            raise ValidationError('\n'.join(validation_result['errors']))

        if validation_result['warnings']:
            # Log warnings
            _logger.warning(f"Integration warnings for order {self.name}: {validation_result['warnings']}")

        return True
```

## 🎯 Best Practices for Integration

### 1. Error Handling & Recovery

#### Robust Error Handling
```python
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """
        Enhanced error handling với recovery mechanisms
        """
        try:
            return super(SaleOrder, self).action_confirm()

        except Exception as e:
            # Log error details
            self._log_integration_error('order_confirmation', str(e))

            # Attempt recovery
            if self._can_recover_from_error(e):
                return self._attempt_recovery()
            else:
                # Notify admin
                self._notify_admin_error(e)
                raise

    def _log_integration_error(self, operation, error_message):
        """
        Log integration errors với detailed context
        """
        self.env['integration.error.log'].create({
            'model': 'sale.order',
            'res_id': self.id,
            'operation': operation,
            'error_message': error_message,
            'context': {
                'order_name': self.name,
                'partner_id': self.partner_id.id,
                'amount_total': self.amount_total,
                'user_id': self.env.user.id,
            },
        })

    def _can_recover_from_error(self, error):
        """
        Determine if error is recoverable
        """
        recoverable_errors = [
            'stock_insufficient',
            'pricelist_not_found',
            'temporarily_unavailable',
        ]

        return any(err in str(error).lower() for err in recoverable_errors)

    def _attempt_recovery(self):
        """
        Attempt automatic recovery from errors
        """
        # Recovery logic based on error type
        pass
```

### 2. Transaction Management

#### Atomic Operations
```python
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """
        Ensure transaction integrity cho complex operations
        """
        with self.env.cr.savepoint():
            try:
                # Perform all operations in single transaction
                self._reserve_stock_atomic()
                self._create_picking_atomic()
                self._update_forecasts_atomic()
                self._notify_stakeholders_atomic()

                # Commit transaction
                self.env.cr.commit()

            except Exception as e:
                # Rollback transaction
                self.env.cr.rollback()
                raise

    def _reserve_stock_atomic(self):
        """
        Atomic stock reservation
        """
        for line in self.order_line:
            if line.product_id.type == 'product':
                # Create stock reservation record
                self.env['stock.reservation'].create({
                    'product_id': line.product_id.id,
                    'quantity': line.product_uom_qty,
                    'location_id': self.warehouse_id.lot_stock_id.id,
                    'sale_order_line_id': line.id,
                    'state': 'confirmed',
                })

    def _create_picking_atomic(self):
        """
        Atomic picking creation
        """
        picking_vals = self._prepare_picking_vals()
        picking = self.env['stock.picking'].create(picking_vals)

        # Create moves
        move_vals_list = []
        for line in self.order_line:
            move_vals = line._prepare_stock_move_vals(picking)
            move_vals_list.append((0, 0, move_vals))

        picking.write({'move_lines': move_vals_list})
        picking.action_confirm()
```

### 3. Performance Optimization

#### Batch Processing
```python
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def batch_confirm_orders(self, order_ids, batch_size=100):
        """
        Batch confirm orders để improve performance
        """
        orders = self.browse(order_ids)

        for i in range(0, len(orders), batch_size):
            batch = orders[i:i + batch_size]
            self._process_order_batch(batch)

    def _process_order_batch(self, orders):
        """
        Process batch của orders với optimized queries
        """
        # Pre-fetch related records
        orders.read(['partner_id', 'warehouse_id', 'pricelist_id'])
        orders.mapped('order_line').read(['product_id', 'product_uom_qty'])

        # Process orders
        for order in orders:
            try:
                order.action_confirm()
            except Exception as e:
                _logger.error(f"Failed to confirm order {order.name}: {str(e)}")
                continue

    @api.model
    def _prefetch_related_data(self, orders):
        """
        Prefetch related data để reduce queries
        """
        # Prefetch partners
        partners = orders.mapped('partner_id')
        partners.read(['name', 'email', 'phone', 'payment_term_id'])

        # Prefetch products
        products = orders.mapped('order_line.product_id')
        products.read(['name', 'default_code', 'type'])

        # Prefetch warehouses
        warehouses = orders.mapped('warehouse_id')
        warehouses.read(['name', 'lot_stock_id'])
```

## 📚 Integration Testing

### 1. Integration Test Framework

#### Automated Integration Tests
```python
from odoo.tests.common import TransactionCase

class SaleIntegrationTestCase(TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'test@example.com',
        })

        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'type': 'product',
            'default_code': 'TEST001',
        })

    def test_inventory_integration(self):
        """
        Test inventory integration
        """
        # Create sales order
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 10,
                'price_unit': 100,
            })],
        })

        # Confirm order
        order.action_confirm()

        # Check if picking was created
        self.assertTrue(order.picking_ids, "Picking should be created")

        # Check if stock was reserved
        picking = order.picking_ids[0]
        self.assertEqual(picking.state, 'confirmed', "Picking should be confirmed")

        # Check stock reservation
        reservation = self.env['stock.reservation'].search([
            ('sale_order_line_id', 'in', order.order_line.ids)
        ])
        self.assertEqual(len(reservation), 1, "Stock reservation should be created")

    def test_accounting_integration(self):
        """
        Test accounting integration
        """
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 5,
                'price_unit': 100,
            })],
        })

        # Confirm and deliver
        order.action_confirm()
        order.picking_ids[0].move_lines[0].quantity_done = 5
        order.picking_ids[0].button_validate()

        # Create invoice
        invoice = order._create_invoices()[0]

        # Check invoice details
        self.assertEqual(invoice.partner_id, order.partner_id)
        self.assertEqual(invoice.amount_total, 500)
        self.assertEqual(invoice.invoice_origin, order.name)

    def test_api_integration(self):
        """
        Test API integration
        """
        # Test order creation via API
        order_data = {
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 3,
                'price_unit': 100,
            })],
        }

        order = self.env['sale.order'].create_from_api(order_data)

        self.assertEqual(order.partner_id, self.partner)
        self.assertEqual(len(order.order_line), 1)
        self.assertEqual(order.order_line[0].product_uom_qty, 3)
```

### 2. Performance Testing

#### Load Testing
```python
class SalePerformanceTestCase(TransactionCase):

    def test_bulk_order_processing(self):
        """
        Test bulk order processing performance
        """
        import time

        # Create test data
        partners = self._create_test_partners(100)
        products = self._create_test_products(50)

        # Create orders
        start_time = time.time()
        orders = []

        for i in range(1000):
            order = self.env['sale.order'].create({
                'partner_id': partners[i % 100].id,
                'order_line': [(0, 0, {
                    'product_id': products[i % 50].id,
                    'product_uom_qty': 1,
                    'price_unit': 100,
                })],
            })
            orders.append(order)

        creation_time = time.time() - start_time

        # Confirm orders
        start_time = time.time()

        for order in orders:
            order.action_confirm()

        confirmation_time = time.time() - start_time

        # Performance assertions
        self.assertLess(creation_time, 30, "Order creation should take less than 30 seconds")
        self.assertLess(confirmation_time, 60, "Order confirmation should take less than 60 seconds")

        _logger.info(f"Created 1000 orders in {creation_time:.2f} seconds")
        _logger.info(f"Confirmed 1000 orders in {confirmation_time:.2f} seconds")

    def _create_test_partners(self, count):
        """
        Create test partners
        """
        partners = []
        for i in range(count):
            partner = self.env['res.partner'].create({
                'name': f'Test Partner {i}',
                'email': f'test{i}@example.com',
            })
            partners.append(partner)
        return partners

    def _create_test_products(self, count):
        """
        Create test products
        """
        products = []
        for i in range(count):
            product = self.env['product.product'].create({
                'name': f'Test Product {i}',
                'type': 'product',
                'default_code': f'TEST{i:03d}',
            })
            products.append(product)
        return products
```

## 🔍 Troubleshooting Integration Issues

### 1. Common Integration Problems

#### Problem Diagnosis Framework
```python
class IntegrationDiagnostic(models.Model):
    _name = 'integration.diagnostic'
    _description = 'Integration Diagnostic Tool'

    @api.model
    def diagnose_sales_integration(self, order_id):
        """
        Comprehensive diagnostic cho sales integration
        """
        order = self.env['sale.order'].browse(order_id)

        diagnostic_result = {
            'order_id': order_id,
            'order_reference': order.name,
            'timestamp': fields.Datetime.now(),
            'checks': {},
            'recommendations': [],
        }

        # Check inventory integration
        diagnostic_result['checks']['inventory'] = self._check_inventory_integration(order)

        # Check accounting integration
        diagnostic_result['checks']['accounting'] = self._check_accounting_integration(order)

        # Check API integration
        diagnostic_result['checks']['api'] = self._check_api_integration(order)

        # Check data consistency
        diagnostic_result['checks']['data_consistency'] = self._check_data_consistency(order)

        # Generate recommendations
        diagnostic_result['recommendations'] = self._generate_recommendations(diagnostic_result['checks'])

        return diagnostic_result

    def _check_inventory_integration(self, order):
        """
        Check inventory integration status
        """
        result = {
            'status': 'unknown',
            'issues': [],
            'metrics': {},
        }

        # Check picking creation
        if not order.picking_ids:
            result['issues'].append('No picking created')
        else:
            result['metrics']['picking_count'] = len(order.picking_ids)

            # Check picking status
            for picking in order.picking_ids:
                if picking.state != 'confirmed':
                    result['issues'].append(f'Picking {picking.name} not confirmed')

        # Check stock availability
        for line in order.order_line:
            if line.product_id.type == 'product':
                available_qty = line._get_available_quantity()
                if available_qty < line.product_uom_qty:
                    result['issues'].append(
                        f'Insufficient stock for {line.product_id.name}: '
                        f'available {available_qty}, required {line.product_uom_qty}'
                    )

        result['status'] = 'passed' if not result['issues'] else 'failed'
        return result

    def _check_accounting_integration(self, order):
        """
        Check accounting integration status
        """
        result = {
            'status': 'unknown',
            'issues': [],
            'metrics': {},
        }

        # Check invoice creation
        if not order.invoice_ids:
            result['issues'].append('No invoices created')
        else:
            result['metrics']['invoice_count'] = len(order.invoice_ids)

            # Check invoice status
            for invoice in order.invoice_ids:
                if invoice.state != 'posted':
                    result['issues'].append(f'Invoice {invoice.number} not posted')

        # Check payment status
        result['metrics']['payment_status'] = order.invoice_ids.mapped('payment_state')

        result['status'] = 'passed' if not result['issues'] else 'failed'
        return result

    def _generate_recommendations(self, checks):
        """
        Generate recommendations based on diagnostic results
        """
        recommendations = []

        for check_type, check_result in checks.items():
            if check_result['status'] == 'failed':
                recommendations.extend([
                    f"Issue in {check_type}: {issue}"
                    for issue in check_result['issues']
                ])

        return recommendations
```

## 📈 Conclusion

### Integration Success Criteria

1. **Data Consistency**: ✅ Data synchronization across modules
2. **Performance**: ✅ Efficient processing with minimal latency
3. **Reliability**: ✅ Robust error handling and recovery
4. **Scalability**: ✅ Handle growing order volumes
5. **Maintainability**: ✅ Clean, well-documented integration code

### Key Takeaways

1. **Comprehensive Integration**: Sales module integrates seamlessly with CRM, Inventory, Accounting, and external systems
2. **Event-Driven Architecture**: Real-time updates and notifications improve operational efficiency
3. **Robust Error Handling**: Comprehensive error management ensures system reliability
4. **Performance Optimization**: Batch processing and prefetching improve scalability
5. **Testing Framework**: Comprehensive testing ensures integration quality

---

**File Size**: 3,800+ words
**Language**: Vietnamese
**Target Audience**: Developers, Integration Specialists, System Architects
**Complexity**: Advanced - Enterprise Implementation