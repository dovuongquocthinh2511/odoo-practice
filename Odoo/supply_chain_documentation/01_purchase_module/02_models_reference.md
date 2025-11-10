# 📋 Model Reference Documentation

## 🎯 Giới Thiệu

Documentation chi tiết về các models, fields, và methods trong module Purchase Odoo 18. Đây là reference kỹ thuật cho developers khi customizing và extending functionality.

## 📊 Purchase Order Model (`purchase.order`)

### Model Definition

```python
class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ['portal.mixin', 'product.catalog.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Purchase Order"
    _rec_names_search = ['name', 'partner_ref']
    _order = 'priority desc, id desc'
```

### Field Specifications

#### 🏷️ Basic Information Fields

| Field | Type | Required | Default | Description | Vietnamese |
|-------|------|----------|---------|-------------|------------|
| `name` | Char | ✅ | `'New'` | Purchase Order reference | Mã đơn hàng |
| `partner_ref` | Char | ❌ | `False` | Vendor's reference number | Mã tham chiếu nhà cung cấp |
| `origin` | Char | ❌ | `False` | Source document reference | Nguồn tài liệu |
| `priority` | Selection | ❌ | `'0'` | Order priority (0=Normal, 1=Urgent) | Độ ưu tiên |
| `date_order` | Datetime | ✅ | `now()` | Order deadline/date | Hạn chót đơn hàng |
| `date_approve` | Datetime | ❌ | `False` | Confirmation date | Ngày xác nhận |

```python
priority = fields.Selection([
    ('0', 'Normal'),
    ('1', 'Urgent')
], 'Priority', default='0', index=True)
```

#### 🤝 Vendor & Partner Fields

| Field | Type | Required | Relation | Description | Vietnamese |
|-------|------|----------|----------|-------------|------------|
| `partner_id` | Many2one | ✅ | `res.partner` | Vendor/Supplier | Nhà cung cấp |
| `dest_address_id` | Many2one | ❌ | `res.partner` | Dropship delivery address | Địa chỉ giao hàng |
| `user_id` | Many2one | ❌ | `res.users` | Buyer/Purchasing contact | Người mua hàng |

```python
partner_id = fields.Many2one(
    'res.partner',
    string='Vendor',
    required=True,
    index=True,
    change_default=True,
    tracking=True,
    check_company=True,
    help="You can find a vendor by its Name, TIN, Email or Internal Reference."
)
```

#### 💰 Financial Fields

| Field | Type | Required | Computed | Description | Vietnamese |
|-------|------|----------|----------|-------------|------------|
| `currency_id` | Many2one | ✅ | ✅ | Currency for the order | Tiền tệ |
| `amount_untaxed` | Monetary | ❌ | ✅ | Total without taxes | Tổng chưa thuế |
| `amount_tax` | Monetary | ❌ | ✅ | Tax amount | Tiền thuế |
| `amount_total` | Monetary | ❌ | ✅ | Total with taxes | Tổng có thuế |
| `amount_total_cc` | Monetary | ❌ | ✅ | Total in company currency | Tổng theo tiền tệ công ty |

```python
@api.depends('order_line.price_subtotal', 'company_id', 'currency_id')
def _amount_all(self):
    AccountTax = self.env['account.tax']
    for order in self:
        order_lines = order.order_line.filtered(lambda x: not x.display_type)
        base_lines = [line._prepare_base_line_for_taxes_computation() for line in order_lines]
        AccountTax._add_tax_details_in_base_lines(base_lines, order.company_id)
        AccountTax._round_base_lines_tax_details(base_lines, order.company_id)
        tax_totals = AccountTax._get_tax_totals_summary(
            base_lines=base_lines,
            currency=order.currency_id or order.company_id.currency_id,
            company=order.company_id,
        )
        order.amount_untaxed = tax_totals['base_amount_currency']
        order.amount_tax = tax_totals['tax_amount_currency']
        order.amount_total = tax_totals['total_amount_currency']
        order.amount_total_cc = tax_totals['total_amount']
```

#### 🔄 Workflow & Status Fields

| Field | Type | Required | Default | Values | Vietnamese |
|-------|------|----------|---------|--------|------------|
| `state` | Selection | ✅ | `'draft'` | RFQ workflow states | Trạng thái |
| `invoice_status` | Selection | ❌ | `'no'` | Billing status | Trạng thái thanh toán |

```python
state = fields.Selection([
    ('draft', 'RFQ'),
    ('sent', 'RFQ Sent'),
    ('to approve', 'To Approve'),
    ('purchase', 'Purchase Order'),
    ('done', 'Locked'),
    ('cancel', 'Cancelled')
], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)

invoice_status = fields.Selection([
    ('no', 'Nothing to Bill'),
    ('to invoice', 'Waiting Bills'),
    ('invoiced', 'Fully Billed'),
], string='Billing Status', compute='_get_invoiced', store=True, readonly=True, copy=False, default='no')
```

#### 📅 Planning & Dates Fields

| Field | Type | Required | Computed | Description | Vietnamese |
|-------|------|----------|----------|-------------|------------|
| `date_planned` | Datetime | ❌ | ✅ | Expected arrival date | Ngày nhận hàng dự kiến |
| `date_calendar_start` | Datetime | ❌ | ✅ | Calendar start date | Ngày bắt đầu lịch |

```python
@api.depends('order_line.date_planned')
def _compute_date_planned(self):
    """ date_planned = the earliest date_planned across all order lines. """
    for order in self:
        dates_list = order.order_line.filtered(lambda x: not x.display_type and x.date_planned).mapped('date_planned')
        if dates_list:
            order.date_planned = min(dates_list)
        else:
            order.date_planned = False
```

### Method Documentation

#### 🔄 Workflow Methods

##### `action_rfq_send()`
```python
def action_rfq_send(self):
    '''
    This function opens a window to compose an email, with the edi purchase template message loaded by default
    '''
    # Purpose: Gửi RFQ cho vendor qua email
    # Return: Dictionary defining email compose action
    # Usage: Called from RFQ form view
```

##### `button_confirm()`
```python
def button_confirm(self):
    """
    Confirm the RFQ and convert to Purchase Order
    """
    # Purpose: Xác nhận RFQ và chuyển thành Purchase Order
    # Logic:
    # 1. Validate analytic distribution
    # 2. Add vendor to product
    # 3. Check if approval is needed
    # 4. Update state appropriately
    # Returns: True
```

##### `button_approve(force=False)`
```python
def button_approve(self, force=False):
    """
    Approve the purchase order
    """
    # Purpose: Duyệt Purchase Order
    # Logic: Update state to 'purchase' and set approval date
    # Parameter force: Bypass approval restrictions
    # Returns: Empty dictionary
```

##### `button_cancel()`
```python
def button_cancel(self):
    """
    Cancel the purchase order
    """
    # Purpose: Hủy Purchase Order
    # Logic: Check for related invoices before canceling
    # Exception: UserError if invoices exist
```

#### 🔧 Business Logic Methods

##### `_add_supplier_to_product()`
```python
def _add_supplier_to_product(self):
    """
    Add the supplier to the product's supplier list
    """
    # Purpose: Thêm vendor vào danh sách nhà cung cấp của sản phẩm
    # Logic: Create/update supplierinfo records
```

##### `_approval_allowed()`
```python
def _approval_allowed(self):
    """
    Check if the current user can approve the order
    """
    # Purpose: Kiểm tra quyền duyệt đơn hàng
    # Returns: Boolean
    # Logic: Based on user groups and approval limits
```

##### `_prepare_supplier_info()`
```python
def _prepare_supplier_info(self, partner, line, price, currency):
    """
    Prepare supplierinfo data when adding a product
    """
    # Purpose: Chuẩn bị dữ liệu supplierinfo
    # Returns: Dictionary with supplierinfo fields
    # Usage: Called when adding vendors to products
```

#### 🔍 Search & Filtering Methods

##### `name_search()`
```python
def name_search(self, name='', args=None, operator='ilike', limit=100):
    """
    Enhanced name search for purchase orders
    """
    # Purpose: Tìm kiếm nâng cao theo tên PO và partner_ref
    # Returns: List of matching record IDs
```

##### `read_group()`
```python
def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
    """
    Optimized read_group for purchase analytics
    """
    # Purpose: Đọc và nhóm dữ liệu cho analytics
    # Performance: Optimized queries for dashboard
```

## 📝 Purchase Order Line Model (`purchase.order.line`)

### Model Definition

```python
class PurchaseOrderLine(models.Model):
    _name = 'purchase.order.line'
    _inherit = 'analytic.mixin'
    _description = 'Purchase Order Line'
    _order = 'order_id, sequence, id'
```

### Field Specifications

#### 📦 Product Information Fields

| Field | Type | Required | Description | Vietnamese |
|-------|------|----------|-------------|------------|
| `product_id` | Many2one | ❌ | Product reference | Sản phẩm |
| `name` | Text | ✅ | Product description | Mô tả |
| `product_qty` | Float | ✅ | Quantity to order | Số lượng |
| `product_uom` | Many2one | ❌ | Unit of measure | Đơn vị tính |
| `product_uom_qty` | Float | ❌ | Quantity in UoM | Số lượng theo ĐVT |

```python
product_id = fields.Many2one(
    'product.product',
    string='Product',
    domain=[('purchase_ok', '=', True)],
    change_default=True,
    index='btree_not_null',
    ondelete='restrict'
)
```

#### 💰 Pricing Fields

| Field | Type | Required | Computed | Description | Vietnamese |
|-------|------|----------|----------|-------------|------------|
| `price_unit` | Float | ✅ | ✅ | Unit price | Đơn giá |
| `discount` | Float | ❌ | ✅ | Discount percentage | Chiết khấu |
| `price_subtotal` | Monetary | ❌ | ✅ | Line subtotal | Thành tiền |
| `price_total` | Monetary | ❌ | ✅ | Line total with tax | Tổng cộng |
| `price_tax` | Float | ❌ | ✅ | Tax amount | Thuế |

```python
@api.depends('product_qty', 'price_unit', 'taxes_id', 'discount')
def _compute_amount(self):
    for line in self:
        base_line = line._prepare_base_line_for_taxes_computation()
        self.env['account.tax']._add_tax_details_in_base_line(base_line, line.company_id)
        line.price_subtotal = base_line['tax_details']['raw_total_excluded_currency']
        line.price_total = base_line['tax_details']['raw_total_included_currency']
        line.price_tax = line.price_total - line.price_subtotal
```

#### 📊 Quantity & Status Fields

| Field | Type | Computed | Description | Vietnamese |
|-------|------|----------|-------------|------------|
| `qty_received` | Float | ✅ | Quantity received | Số lượng đã nhận |
| `qty_invoiced` | Float | ✅ | Quantity invoiced | Số lượng đã xuất hóa đơn |
| `qty_to_invoice` | Float | ✅ | Quantity to invoice | Số lượng cần xuất hóa đơn |
| `qty_received_manual` | Float | ❌ | Manual received quantity | Số lượng nhận thủ công |

#### 🔗 Relation Fields

| Field | Type | Description | Vietnamese |
|-------|------|-------------|------------|
| `order_id` | Many2one | Reference to purchase order | Đơn hàng mua |
| `invoice_lines` | One2many | Related invoice lines | Chi tiết hóa đơn |
| `taxes_id` | Many2many | Applicable taxes | Thuế áp dụng |

### Method Documentation

#### 💰 Pricing Methods

##### `_compute_amount()`
```python
@api.depends('product_qty', 'price_unit', 'taxes_id', 'discount')
def _compute_amount(self):
    """
    Compute the subtotal, tax, and total amounts for the line
    """
    # Purpose: Tính toán tiền cho line
    # Logic:
    # 1. Prepare base line for tax computation
    # 2. Add tax details
    # 3. Calculate subtotal, tax, total
```

##### `_prepare_base_line_for_taxes_computation()`
```python
def _prepare_base_line_for_taxes_computation(self):
    """
    Prepare line data for tax computation
    """
    # Purpose: Chuẩn bị dữ liệu để tính thuế
    # Returns: Dictionary with line information
    # Usage: Called by tax calculation methods
```

#### 📊 Quantity Methods

##### `_compute_qty_received()`
```python
def _compute_qty_received(self):
    """
    Compute the quantity received from stock moves
    """
    # Purpose: Tính số lượng đã nhận từ stock moves
    # Logic: Sum quantities from related pickings
```

##### `_compute_qty_invoiced()`
```python
def _compute_qty_invoiced(self):
    """
    Compute the quantity invoiced from invoice lines
    """
    # Purpose: Tính số lượng đã xuất hóa đơn
    # Logic: Sum quantities from related invoices
```

##### `_inverse_qty_received()`
```python
def _inverse_qty_received(self):
    """
    Handle manual input of received quantity
    """
    # Purpose: Xử lý nhập thủ công số lượng nhận
    # Logic: Update manual received quantity field
```

#### 🔧 Product Management Methods

##### `_get_date_planned()`
```python
def _get_date_planned(self, seller, po=False):
    """
    Get the planned delivery date based on seller information
    """
    # Purpose: Lấy ngày giao hàng dự kiến
    # Parameters:
    #   - seller: Supplier information
    #   - po: Purchase order context
    # Returns: Datetime for planned delivery
```

##### `onchange_product_id()`
```python
@api.onchange('product_id')
def onchange_product_id(self):
    """
    Update line when product is changed
    """
    # Purpose: Cập nhật line khi thay đổi sản phẩm
    # Logic: Update description, UoM, price, etc.
```

## 🔗 Integration Models

### Account Move Integration (`account.move`)

#### Additional Fields for Purchase

```python
class AccountMove(models.Model):
    _inherit = 'account.move'

    purchase_vendor_bill_id = fields.Many2one('purchase.bill.union')
    purchase_id = fields.Many2one('purchase.order')
    purchase_order_count = fields.Integer(compute="_compute_origin_po_count")
    is_purchase_matched = fields.Boolean(compute='_compute_is_purchase_matched')
```

#### Key Integration Methods

##### `_onchange_purchase_auto_complete()`
```python
@api.onchange('purchase_vendor_bill_id', 'purchase_id')
def _onchange_purchase_auto_complete(self):
    """
    Auto-complete invoice from purchase order
    """
    # Purpose: Tự động điền thông tin hóa đơn từ PO
    # Logic: Load lines and amounts from related PO
```

## 🔒 Security & Access Control

### Access Rights Structure

```csv
id,name,model_id/id,group_id/id,perm_read,perm_write,perm_create,perm_unlink
access_purchase_order_user,purchase.order.user,model_purchase_order,base.group_user,1,1,1,0
access_purchase_order_manager,purchase.order.manager,model_purchase_order,purchase.group_purchase_manager,1,1,1,1
access_purchase_order_line_user,purchase.order.line.user,model_purchase_order_line,base.group_user,1,1,1,0
access_purchase_order_line_manager,purchase.order.line.manager,model_purchase_order_line,purchase.group_purchase_manager,1,1,1,1
```

### Record Rules

```xml
<record id="purchase_order_rule_user" model="ir.rule">
    <field name="name">Purchase Order: User can see their orders</field>
    <field name="model_id" ref="model_purchase_order"/>
    <field name="domain_force">[('create_uid', '=', user.id)]</field>
    <field name="groups" eval="[(4, ref('base.group_user'))]"/>
</record>
```

### Field Access Controls

```python
# Readonly fields based on state
readonly_fields = {
    'done': ['date_approve', 'partner_id', 'order_line'],
    'cancel': ['order_line'],
    'purchase': ['date_approve'],
}
```

## 🔍 SQL Constraints & Validations

### Purchase Order Constraints

```python
_sql_constraints = [
    ('name_uniq', 'unique(name, company_id)', 'Order Reference must be unique per company!'),
    ('date_order_check', 'check(date_order <= date_approve)', 'Order date must be before approval date!'),
]
```

### Purchase Order Line Constraints

```python
_sql_constraints = [
    ('accountable_required_fields',
     "CHECK(display_type IS NOT NULL OR is_downpayment OR (product_id IS NOT NULL AND product_uom IS NOT NULL AND date_planned IS NOT NULL))",
     "Missing required fields on accountable purchase order line."),
    ('non_accountable_null_fields',
     "CHECK(display_type IS NULL OR (product_id IS NULL AND price_unit = 0 AND product_uom_qty = 0 AND product_uom IS NULL AND date_planned is NULL))",
     "Forbidden values on non-accountable purchase order line"),
]
```

### Business Validation Methods

```python
@api.constrains('company_id', 'order_line')
def _check_order_line_company_id(self):
    """
    Validate that all products belong to accessible companies
    """
    for order in self:
        invalid_companies = order.order_line.product_id.company_id.filtered(
            lambda c: order.company_id not in c._accessible_branches()
        )
        if invalid_companies:
            raise ValidationError(_(
                "Your quotation contains products from company %(product_company)s "
                "whereas your quotation belongs to company %(quote_company)s.",
                product_company=', '.join(invalid_companies.sudo().mapped('display_name')),
                quote_company=order.company_id.display_name,
            ))
```

## 📊 Database Schema Overview

### Tables Structure

```sql
-- Purchase Orders
CREATE TABLE purchase_order (
    id INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL,
    partner_id INTEGER REFERENCES res_partner(id),
    state VARCHAR DEFAULT 'draft',
    date_order TIMESTAMP,
    date_approve TIMESTAMP,
    amount_total DECIMAL,
    company_id INTEGER REFERENCES res_company(id)
);

-- Purchase Order Lines
CREATE TABLE purchase_order_line (
    id INTEGER PRIMARY KEY,
    order_id INTEGER REFERENCES purchase_order(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES product_product(id),
    product_qty DECIMAL,
    price_unit DECIMAL,
    price_total DECIMAL,
    qty_received DECIMAL,
    qty_invoiced DECIMAL
);
```

### Indexes

```sql
-- Performance indexes
CREATE INDEX idx_purchase_order_name ON purchase_order(name);
CREATE INDEX idx_purchase_order_partner ON purchase_order(partner_id);
CREATE INDEX idx_purchase_order_state ON purchase_order(state);
CREATE INDEX idx_purchase_order_date ON purchase_order(date_order);
CREATE INDEX idx_pol_order_id ON purchase_order_line(order_id);
CREATE INDEX idx_pol_product_id ON purchase_order_line(product_id);
```

## 🔧 Extending Models

### Custom Field Addition

```python
class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    custom_field = fields.Char('Custom Field')
    custom_date = fields.Date('Custom Date')

    @api.depends('custom_field')
    def _compute_custom_logic(self):
        # Custom computation logic
        pass
```

### Custom Validation

```python
@api.constrains('custom_field')
def _check_custom_field(self):
    for order in self:
        if order.custom_field and len(order.custom_field) < 3:
            raise ValidationError('Custom field must be at least 3 characters!')
```

### Custom Workflow

```python
def custom_workflow_action(self):
    """
    Custom workflow action
    """
    self.write({'state': 'custom_state'})
    # Custom logic here
    return True
```

## 📈 Performance Optimizations

### Computed Fields Optimization

```python
# Use store=True for expensive computations
@api.depends('order_line.price_total')
def _compute_total_amount(self):
    # Optimized calculation
    pass
```

### Query Optimization

```python
# Use prefetch_related and select_related
orders = self.env['purchase.order'].search([
    ('state', '=', 'purchase')
]).with_context(prefetch_fields=False)
```

---

**Next Steps**: Đọc [03_workflows_guide.md](03_workflows_guide.md) để hiểu detailed workflow implementations.