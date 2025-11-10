# 📖 Tổng Quan Module Sales - Architecture và Components

## 🎯 Giới Thiệu

Module Sales trong Odoo 18 là một trong những modules quan trọng nhất của hệ thống ERP, chịu trách nhiệm quản lý toàn bộ quy trình bán hàng từ tiếp cận khách hàng đến khi giao hàng và thanh toán. Module này tích hợp chặt chẽ với Inventory, Accounting, Customer Management (CRM), và các modules khác.

## 🏗️ Module Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                      SALES MODULE                              │
├─────────────────────────────────────────────────────────────┤
│  Frontend (Web Interface)                                     │
│  ├── Sales Dashboard & Analytics                             │
│  ├── Quotation Management                                    │
│  ├── Sales Orders (Đơn Bán Hàng)                            │
│  ├── Customer Portal                                         │
│  └── POS Integration                                         │
├─────────────────────────────────────────────────────────────┤
│  Backend (Business Logic)                                    │
│  ├── Models (sale.order, sale.order.line)                   │
│  ├── CRM Integration                                        │
│  ├── Pricing Engine                                         │
│  ├── Workflow Automation                                    │
│  └── Security & Access Control                              │
├─────────────────────────────────────────────────────────────┤
│  Integration Layer                                          │
│  ├── Inventory Management (stock.picking)                   │
│  ├── Accounting (account.move)                              │
│  ├── Customer Management (res.partner)                      │
│  ├── E-commerce Integration                                 │
│  └── Reporting & Analytics                                  │
└─────────────────────────────────────────────────────────────┘
```

## 📊 Data Model Architecture

### 1. Sales Order Model (`sale.order`)

**Purpose**: Entity chính quản lý đơn bán hàng
**Table**: `sale_order`

#### Key Fields Overview
```python
class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Sales Order"
    _order = 'date_order desc, id desc'

    # Basic Information
    name = fields.Char('Order Reference', required=True, copy=False)  # SO number
    partner_id = fields.Many2one('res.partner', 'Customer', required=True)
    date_order = fields.Datetime('Order Date', required=True, default=fields.Datetime.now)
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, default='draft')

    # Order Details
    order_line = fields.One2many('sale.order.line', 'order_id', 'Order Lines')
    amount_total = fields.Monetary('Total', currency_field='currency_id')
    amount_untaxed = fields.Monetary('Untaxed Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', 'Currency', required=True)

    # Delivery Information
    commitment_date = fields.Date('Commitment Date')
    picking_policy = fields.Selection([
        ('direct', 'Deliver each product when available'),
        ('one', 'Deliver all products at once')
    ], string='Shipping Policy', default='direct')

    # Integration Fields
    invoice_ids = fields.One2many('account.move', 'invoice_origin', 'Invoices', copy=False)
    picking_ids = fields.One2many('stock.picking', 'sale_id', 'Transfers')
    procurement_group_id = fields.Many2one('procurement.group', 'Procurement Group')
```

### 2. Sales Order Line Model (`sale.order.line`)

**Purpose**: Chi tiết các sản phẩm trong đơn bán hàng
**Table**: `sale_order_line`

#### Key Fields
```python
class SaleOrderLine(models.Model):
    _name = "sale.order.line"
    _description = "Sales Order Line"

    # Basic Information
    order_id = fields.Many2one('sale.order', 'Order Reference', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    name = fields.Text('Description')
    product_uom_qty = fields.Float('Quantity', default=1.0)
    product_uom = fields.Many2one('uom.uom', 'Unit of Measure')

    # Pricing
    price_unit = fields.Float('Unit Price', digits='Product Price')
    discount = fields.Float('Discount (%)', digits='Discount')
    price_subtotal = fields.Monetary('Subtotal', currency_field='currency_id')
    price_tax = fields.Float('Tax', digits='Account')
    price_total = fields.Monetary('Total', currency_field='currency_id')

    # Status and Delivery
    qty_delivered = fields.Float('Delivered', copy=False)
    qty_to_deliver = fields.Float('To Deliver', compute='_compute_qty_to_deliver')
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sale', 'Sales Order'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', related='order_id.state', store=True)
```

## 🔄 Workflow Architecture

### Sales Order State Machine

```
┌─────────────┐
│   Draft     │ (Quotation)
├─────────────┤
│   Sent      │ (Quotation Sent)
├─────────────┤
│   Sale      │ (Sales Order)
├─────────────┤
│   Done      │ (Locked/Archived)
├─────────────┤
│  Cancel     │ (Cancelled)
└─────────────┘
```

#### State Transitions
1. **Draft → Sent**: Gửi báo giá cho khách hàng
2. **Sent → Sale**: Khách hàng xác nhận báo giá → Đơn bán hàng
3. **Sale → Done**: Giao hàng hoàn tất, hóa đơn đã tạo
4. **Sale → Cancel**: Hủy đơn hàng
5. **Any State → Draft**: Tạo báo giá mới từ đơn có sẵn

## 🎨 Frontend Architecture

### 1. Sales Dashboard

**Components**:
- **KPI Widgets**: Doanh thu, số đơn, tỷ lệ chuyển đổi
- **Sales Pipeline**: Trạng thái cơ hội bán hàng
- **Activity Stream**: Lịch sử hoạt động bán hàng
- **Quick Actions**: Tạo báo giá, đơn hàng mới

**Technical Implementation**:
```javascript
// Frontend JavaScript cho Sales Dashboard
odoo.define('sales.sales_dashboard', function (require) {
    'use strict';

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var _t = core._t;

    var SalesDashboard = AbstractAction.extend({
        template: 'sales.SalesDashboard',

        init: function(parent, context) {
            this._super(parent, context);
            this.kpi_data = {};
            this.pipeline_data = [];
        },

        willStart: function() {
            var self = this;
            return $.when(
                this._fetchKPIData(),
                this._fetchPipelineData()
            );
        },

        _fetchKPIData: function() {
            var self = this;
            return this._rpc({
                model: 'sale.order',
                method: 'get_kpi_data',
                args: [],
            }).then(function(result) {
                self.kpi_data = result;
            });
        },

        _fetchPipelineData: function() {
            var self = this;
            return this._rpc({
                model: 'sale.order',
                method: 'get_pipeline_data',
                args: [],
            }).then(function(result) {
                self.pipeline_data = result;
            });
        }
    });

    return SalesDashboard;
});
```

### 2. Quotation/Sales Order Form

**Key Features**:
- **Dynamic Line Management**: Thêm/xóa sản phẩm động
- **Real-time Pricing**: Tính giá tự động khi thay đổi
- **Tax Calculation**: Tính thuế tự động theo quy định
- **Stock Availability**: Kiểm tra tồn kho real-time
- **Customer Information**: Tích hợp CRM và lịch sử mua hàng

## 📈 Integration Patterns

### 1. Inventory Integration

**Purpose**: Quản lý tồn kho và giao hàng
**Key Integration Points**:

```python
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """Xác nhận đơn hàng và tạo giao hàng"""
        res = super(SaleOrder, self).action_confirm()

        # Tạo stock picking cho giao hàng
        self._create_picking()

        # Cập nhật dự báo tồn kho
        self._update_forecast()

        return res

    def _create_picking(self):
        """Tạo phiếu giao hàng tự động"""
        for order in self:
            # Tạo procurement group
            if not order.procurement_group_id:
                order.procurement_group_id = self.env['procurement.group'].create({
                    'name': order.name,
                    'sale_id': order.id,
                }).id

            # Tạo picking cho mỗi dòng sản phẩm
            for line in order.order_line:
                if line.product_id.type in ['product', 'consu']:
                    self.env['stock.picking']._create_picking_from_sale_order_line(line)
```

### 2. Accounting Integration

**Purpose**: Tự động tạo hóa đơn khi giao hàng
**Implementation**:

```python
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _create_invoices(self, grouped=False, final=False):
        """Tạo hóa đơn từ đơn hàng"""
        moves = self.order_line._get_moves_to_invoice(final)
        if not moves:
            return self.env['account.move']

        # Tạo hóa đơn
        invoices = moves._action_done()._create_invoices(final)

        # Cập nhật thông tin hóa đơn
        for invoice in invoices:
            invoice.write({
                'invoice_origin': self.name,
                'partner_id': self.partner_id.id,
                'payment_reference': self.reference,
            })

        return invoices
```

### 3. CRM Integration

**Purpose**: Quản lý khách hàng và cơ hội bán hàng
**Key Features**:

```python
class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def action_new_quotation(self):
        """Tạo báo giá từ khách hàng tiềm năng"""
        self.ensure_one()

        # Tạo partner nếu chưa có
        if not self.partner_id:
            self._handle_partner_assignment()

        # Tạo báo giá
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'campaign_id': self.campaign_id.id,
            'medium_id': self.medium_id.id,
            'source_id': self.source_id.id,
        })

        return {
            'name': 'sale_order_form',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'type': 'ir.actions.act_window',
        }
```

## 🔧 Technical Features

### 1. Pricing Engine

**Dynamic Pricing Configuration**:
```python
class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('product_id', 'product_uom_qty', 'product_uom', 'discount')
    def _compute_amount(self):
        """Tính giá tự động với thuế và chiết khấu"""
        for line in self:
            price = line._get_display_price()

            # Áp dụng chiết khấu
            if line.discount:
                price = price * (1 - line.discount / 100)

            # Tính thuế
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
```

### 2. Multi-Channel Support

**Sales Channel Management**:
```python
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    team_id = fields.Many2one('crm.team', 'Sales Team', default=lambda self: self.env['crm.team']._get_default_team_id())
    channel_id = fields.Many2one('sale.channel', 'Sales Channel')
    source_id = fields.Many2one('utm.source', 'Source')

    def _compute_website_order_line(self):
        """Tính toán cho đơn hàng website"""
        for order in self:
            if order.website_id:
                # Áp dụng pricing cho website
                order._apply_website_pricing()

    def _apply_website_pricing(self):
        """Áp dụng pricing riêng cho website"""
        for line in self.order_line:
            # Lấy pricing list cho website
            pricelist = self.website_id.pricelist_id
            if pricelist:
                line.price_unit = pricelist._get_product_price(
                    line.product_id,
                    line.product_uom_qty,
                    self.partner_id
                )
```

## 📊 Performance Optimization

### Database Indexes
```sql
-- Index cho sales queries
CREATE INDEX idx_sale_order_partner_date ON sale_order(partner_id, date_order);
CREATE INDEX idx_sale_order_state ON sale_order(state);
CREATE INDEX idx_sale_order_line_product ON sale_order_line(product_id);
CREATE INDEX idx_sale_order_line_order ON sale_order_line(order_id);
```

### Query Optimization
```python
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False):
        """Optimized read group cho dashboard"""
        # Pre-fetch related records để reduce queries
        if 'partner_id' in groupby:
            self = self.with_context(prefetch_fields=['partner_id'])

        return super(SaleOrder, self).read_group(
            domain, fields, groupby, offset, limit, orderby
        )
```

## 🌐 Multi-Language Support

### Vietnamese Localization
```python
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _get_report_base_filename(self):
        """Tên file report cho tiếng Việt"""
        self.ensure_one()
        return 'DON_BAN_HANG_%s.pdf' % (self.name.replace('/', '_'))

    def _get_report_values(self):
        """Custom report values cho tiếng Việt"""
        values = super(SaleOrder, self)._get_report_values()

        # Vietnamese field labels
        values.update({
            'doc_title': 'ĐƠN BÁN HÀNG',
            'customer_label': 'Khách Hàng',
            'date_label': 'Ngày Đặt Hàng',
            'total_label': 'Tổng Cộng',
        })

        return values
```

## 📚 Best Practices Overview

### 1. Performance Best Practices
- Sử dụng `@api.depends` cho computed fields
- Implement proper database indexes
- Use `with_context(prefetch_fields)` cho batch operations
- Optimize queries với proper domain filters

### 2. Security Best Practices
- Implement proper record rules
- Use field-level security cho sensitive data
- Validate user permissions trong workflow transitions
- Audit trail cho critical operations

### 3. Integration Best Practices
- Use standardized API endpoints
- Implement proper error handling
- Use transactions cho data consistency
- Async processing cho heavy operations

## 🔮 Advanced Features

### 1. Subscription Management
```python
class SaleSubscription(models.Model):
    _name = 'sale.subscription'
    _description = 'Sales Subscription'

    recurring_rule_type = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ], string='Recurrence')
    recurring_interval = fields.Integer('Repeat Every', default=1)

    def _create_recurring_invoice(self):
        """Tạo hóa đơn định kỳ"""
        # Logic cho subscription billing
        pass
```

### 2. Rental Management
```python
class SaleOrderRental(models.Model):
    _name = 'sale.order.rental'
    _description = 'Sales Order Rental'

    start_date = fields.Datetime('Start Date', required=True)
    end_date = fields.Datetime('End Date', required=True)
    rental_price = fields.Monetary('Rental Price')

    def _compute_rental_days(self):
        """Tính số ngày thuê"""
        for record in self:
            if record.start_date and record.end_date:
                delta = record.end_date - record.start_date
                record.rental_days = delta.days
```

## 📈 Analytics và Reporting

### Sales Analytics
- **Pipeline Analysis**: Theo dõi hiệu suất chuỗi bán hàng
- **Customer Lifetime Value**: Tính toán giá trị khách hàng dài hạn
- **Sales Forecasting**: Dự báo doanh thu dựa trên trend
- **Product Performance**: Phân tích hiệu quả sản phẩm

### Custom Reports
```python
class SalesReport(models.Model):
    _name = 'sales.report'
    _description = 'Sales Analytics Report'

    @api.model
    def get_sales_by_region(self):
        """Báo cáo doanh thu theo khu vực"""
        # SQL query optimized cho performance
        query = """
            SELECT r.name as region,
                   SUM(so.amount_total) as total_revenue,
                   COUNT(so.id) as order_count
            FROM sale_order so
            JOIN res_partner p ON so.partner_id = p.id
            JOIN res_country_state r ON p.state_id = r.id
            WHERE so.state = 'sale'
            AND so.date_order >= %s
            GROUP BY r.name
            ORDER BY total_revenue DESC
        """

        self.env.cr.execute(query, (fields.Date.today().replace(year=fields.Date.today().year - 1),))
        return self.env.cr.dictfetchall()
```

---

**File Size**: 3,500+ words
**Language**: Vietnamese
**Target Audience**: Developers, Business Analysts, Sales Teams
**Complexity**: Advanced - Enterprise Implementation