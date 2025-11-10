# 🔄 Luồng Xử Lý Purchase Workflows - Business Processes và State Transitions

## 🎯 Giới Thiệu

Documentation chi tiết về các luồng xử lý nghiệp vụ trong module Purchase Odoo 18. Hướng dẫn này mô tả từng bước trong quy trình từ Request for Quotation (RFQ) đến khi hoàn thành thanh toán, bao gồm state transitions, business rules, và integration points.

## 📊 Tổng Quan Workflows

### Main Workflow Chain
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PURCHASE MAIN WORKFLOW                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  RFQ (Draft) → RFQ Sent → To Approve → Purchase Order → Receipt → Invoice  │
│      ↓             ↓           ↓              ↓            ↓         ↓        │
│   Gửi RFQ      Chờ phản hồi  Duyệt PO      Xác nhận    Nhận hàng  Thanh toán │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### State Machine Detail
```
    ┌────────────┐    ┌────────────┐    ┌──────────────┐    ┌────────────┐
    │    Draft   │    │    Sent    │    │ To Approve    │    │ Purchase   │
    │    (RFQ)   │───►│ (RFQ Sent) │───►│ (Validation)  │───►│   (Order)   │
    └────────────┘    └────────────┘    └──────────────┘    └────────────┘
         │                  │                  │                  │
         │                  │                  │                  │
         ▼                  │                  │                  │
    ┌────────────┐         │                  │                  │
    │  Cancel    │◄────────┘                  │                  │
    └────────────┘                            │                  │
                                              ▼                  ▼
                                          ┌────────────┐    ┌────────────┐
                                          │   Cancel    │    │    Done     │
                                          └────────────┘    │  (Locked)   │
                                                             └────────────┘
```

## 🔍 Workflow Chi Tiết

### 1. Request for Quotation (RFQ) Workflow

#### **State: `draft` (RFQ - Yêu Cầu Báo Giá)**

**Mục Đích**: Tạo RFQ mới để yêu cầu vendor báo giá

**Conditions**:
- User có quyền tạo Purchase Order
- Partner là vendor có `supplier_rank > 0`
- Có ít nhất một product line

**Business Rules**:
```python
# RFQ Creation Rules
@api.model
def create(self, vals):
    # 1. Validate partner is supplier
    if vals.get('partner_id'):
        partner = self.env['res.partner'].browse(vals['partner_id'])
        if not partner.supplier_rank:
            raise ValidationError("Partner phải là nhà cung cấp!")

    # 2. Set default currency
    if not vals.get('currency_id'):
        vals['currency_id'] = self.env.company.currency_id.id

    # 3. Generate PO number
    if not vals.get('name'):
        vals['name'] = self.env['ir.sequence'].next_by_code('purchase.order') or 'New'

    return super(PurchaseOrder, self).create(vals)
```

**Key Fields at Draft State**:
```python
{
    'state': 'draft',           # Trạng thái
    'partner_id': Vendor,       # Nhà cung cấp
    'date_order': now(),        # Ngày tạo RFQ
    'order_line': Lines[],      # Chi tiết sản phẩm
    'amount_total': 0,          # Tổng tiền (computed)
    'currency_id': Company CCY  # Tiền tệ
}
```

**Available Actions**:
- `action_rfq_send()`: Gửi RFQ cho vendor
- `button_confirm()`: Xác nhận và chuyển sang purchase order
- `button_cancel()`: Hủy RFQ

#### **Action: `action_rfq_send()` - Gửi RFQ**

**Purpose**: Gửi email RFQ cho vendor và chuyển state thành 'sent'

**Implementation**:
```python
def action_rfq_send(self):
    """
    Gửi RFQ cho vendor qua email
    """
    self.ensure_one()

    # 1. Check if email template exists
    template_id = self.env.ref('purchase.email_template_edi_purchase').id
    if not template_id:
        raise UserError("Không tìm thấy template email RFQ!")

    # 2. Check vendor has email
    if not self.partner_id.email:
        raise UserError(f"Vendor {self.partner_id.name} chưa có email!")

    # 3. Send email
    compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)

    ctx = dict(
        default_model='purchase.order',
        default_res_id=self.id,
        default_use_template=bool(template_id),
        default_template_id=template_id,
        default_composition_mode='comment',
        mark_invoice_as_sent=True,
        custom_layout="mail.mail_notification_paynow",
        model_description=self._description,
        force_email=True
    )

    # 4. Update state
    self.write({'state': 'sent'})

    # 5. Log activity
    self.message_post(
        body=_("RFQ đã được gửi cho %s") % self.partner_id.name,
        message_type='notification'
    )

    return {
        'type': 'ir.actions.act_window',
        'view_mode': 'form',
        'res_model': 'mail.compose.message',
        'views': [(compose_form.id, 'form')],
        'view_id': compose_form.id,
        'target': 'new',
        'context': ctx,
    }
```

**Validation Rules**:
- Vendor phải có email
- RFQ phải có ít nhất một line
- User phải có quyền gửi email
- Currency phải được xác định

#### **State: `sent` (RFQ Sent - Đã Gửi)**

**Purpose**: RFQ đã được gửi cho vendor, chờ phản hồi

**Business Logic**:
```python
# Auto-reminder functionality
def _check_rfq_reminders(self):
    """
    Tự động nhắc nhở vendor sau X ngày không phản hồi
    """
    reminder_days = self.env['ir.config_parameter'].sudo().get_param('purchase.rfq_reminder_days', default=7)
    reminder_date = fields.Datetime.now() - timedelta(days=int(reminder_days))

    rfqs_to_remind = self.search([
        ('state', '=', 'sent'),
        ('date_order', '<', reminder_date),
        ('partner_id.email', '!=', False)
    ])

    for rfq in rfqs_to_remind:
        # Send reminder email
        template = self.env.ref('purchase.email_template_rfq_reminder')
        if template:
            template.send_mail(rfq.id, force_send=True)
```

**Available Actions**:
- `print_quotation()`: In RFQ/Purchase Order
- `button_confirm()`: Xác nhận chuyển thành PO
- `button_cancel()`: Hủy RFQ

#### **Action: `button_confirm()` - Xác Nhận RFQ/PO**

**Purpose**: Chuyển từ RFQ sang Purchase Order

**Complex Workflow Logic**:
```python
def button_confirm(self):
    """
    Confirm RFQ và chuyển thành Purchase Order
    """
    self.ensure_one()

    # Phase 1: Validations
    self._confirm_validator()

    # Phase 2: Business Logic
    self._confirm_preparation()

    # Phase 3: State Transition
    self._confirm_state_update()

    # Phase 4: Post-Processing
    self._confirm_post_processing()

    return True

def _confirm_validator(self):
    """Validate trước khi confirm"""
    # 1. Validate vendor
    if not self.partner_id.supplier_rank:
        raise ValidationError("Partner phải là nhà cung cấp!")

    # 2. Validate lines
    if not self.order_line:
        raise ValidationError("PO phải có ít nhất một dòng sản phẩm!")

    # 3. Validate prices
    for line in self.order_line:
        if line.price_unit <= 0:
            raise ValidationError(f"Giá sản phẩm {line.product_id.name} phải lớn hơn 0!")

    # 4. Validate dates
    if self.date_order and self.date_planned:
        if self.date_order > self.date_planned:
            raise ValidationError("Ngày đặt hàng không thể sau ngày giao hàng dự kiến!")

def _confirm_preparation(self):
    """Chuẩn bị data trước khi confirm"""
    # 1. Add vendor to products if needed
    self._add_supplier_to_product()

    # 2. Check for inter-company transactions
    if self._is_inter_company():
        self._create_inter_company_transaction()

    # 3. Validate analytic distribution
    for line in self.order_line:
        if line.account_analytic_id and not line._validate_analytic_distribution():
            raise ValidationError("Phân phối analytic không hợp lệ!")

def _confirm_state_update(self):
    """Cập nhật state"""
    if self._approval_required():
        self.write({'state': 'to approve'})
        self._notify_approvers()
    else:
        self.write({'state': 'purchase'})
        self._execute_purchase_order()

def _add_supplier_to_product(self):
    """Thêm vendor vào danh sách supplier của sản phẩm"""
    for line in self.order_line:
        if line.product_id and line.price_unit > 0:
            # Check if supplier info exists
            existing_supplier = self.env['product.supplierinfo'].search([
                ('product_id', '=', line.product_id.id),
                ('name', '=', self.partner_id.id),
                ('price', '=', line.price_unit),
            ], limit=1)

            if not existing_supplier:
                # Create new supplier info
                self.env['product.supplierinfo'].create({
                    'product_id': line.product_id.id,
                    'name': self.partner_id.id,
                    'price': line.price_unit,
                    'currency_id': self.currency_id.id,
                    'min_qty': line.product_qty,
                    'delay': self.partner_id.property_supplier_payment_term_id.name or 0,
                })
```

### 2. Purchase Order Approval Workflow

#### **State: `to approve` (Chờ Duyệt)**

**Purpose**: PO cần approval từ manager theo company policy

**Approval Conditions**:
```python
def _approval_required(self):
    """
    Kiểm tra PO có cần approval không
    """
    company = self.company_id

    # Rule 1: Amount threshold
    if self.amount_total > company.po_double_validation_amount:
        return True

    # Rule 2: Specific product approval
    approval_products = company.po_double_validation_product_ids
    if approval_products and self.order_line.product_id.filtered(
        lambda p: p in approval_products
    ):
        return True

    # Rule 3: Vendor category approval
    if self.partner_id.category_id.filtered(
        lambda c: c in company.po_double_validation_vendor_category_ids
    ):
        return True

    # Rule 4: Department approval matrix
    if self.department_id and self.department_id.po_approval_required:
        return True

    return False

def _approval_allowed(self):
    """
    Kiểm tra user hiện tại có quyền duyệt không
    """
    user = self.env.user

    # Rule 1: Is Purchase Manager
    if user.has_group('purchase.group_purchase_manager'):
        return True

    # Rule 2: Department head approval
    if self.department_id and user == self.department_id.manager_id:
        return user.has_group('purchase.group_purchase_user')

    # Rule 3: Amount-based approval limits
    if user.has_group('purchase.group_purchase_user'):
        approval_limit = user.company_id.po_approval_limit or 0
        return self.amount_total <= approval_limit

    return False
```

**Approval Workflow**:
```python
def button_approve(self, force=False):
    """
    Duyệt Purchase Order
    """
    self.ensure_one()

    if not force and not self._approval_allowed():
        raise UserError("Bạn không có quyền duyệt PO này!")

    # Update approval date and user
    self.write({
        'state': 'purchase',
        'date_approve': fields.Datetime.now(),
    })

    # Log approval
    self.message_post(
        body=_("PO đã được duyệt bởi %s") % self.env.user.name,
        message_type='notification'
    )

    # Execute purchase order
    self._execute_purchase_order()

    return True

def button_cancel(self):
    """
    Hủy Purchase Order (tại state to approve)
    """
    if self.state == 'to approve':
        self.write({'state': 'cancel'})
        self.message_post(body=_("PO đã bị hủy"))

        # Notify creator
        if self.create_uid != self.env.user:
            self.message_post(
                body=_("PO của bạn đã bị hủy bởi %s") % self.env.user.name,
                partner_ids=[self.create_uid.partner_id.id]
            )
```

### 3. Purchase Order Execution Workflow

#### **State: `purchase` (Purchase Order)**

**Purpose**: PO đã được xác nhận, ready để execute

**Key Execution Tasks**:
```python
def _execute_purchase_order(self):
    """
    Thực thi Purchase Order sau khi được duyệt
    """
    # 1. Create pickings if needed
    if self._should_create_picking():
        self._create_picking()

    # 2. Update product supplier info
    self._update_product_supplier_info()

    # 3. Check for reorder point triggers
    self._trigger_reorder_rules()

    # 4. Update product availability
    self._update_product_availability()

def _should_create_picking(self):
    """
    Kiểm tra có nên tạo picking không
    """
    # Rule 1: Stockable products
    stockable_lines = self.order_line.filtered(
        lambda l: l.product_id.type in ['product', 'consu']
    )

    # Rule 2: Not dropshipping
    if self.dest_address_id:
        return False

    # Rule 3: MRP needs
    if self.order_line.mapped('product_id').filtered(
        lambda p: p.produce_delay and p.bom_count
    ):
        return True

    return bool(stockable_lines)

def _create_picking(self):
    """
    Tạo Stock Picking cho receipt
    """
    # Get picking type
    picking_type = self.picking_type_id or self.env['stock.picking.type'].search([
        ('code', '=', 'incoming'),
        ('warehouse_id', '=', self.picking_type_id.warehouse_id.id),
    ], limit=1)

    # Create picking
    picking = self.env['stock.picking'].create({
        'partner_id': self.partner_id.id,
        'picking_type_id': picking_type.id,
        'origin': self.name,
        'location_id': picking_type.default_location_src_id.id,
        'location_dest_id': picking_type.default_location_dest_id.id,
        'company_id': self.company_id.id,
        'move_ids_without_package': self._prepare_stock_moves(),
    })

    self.picking_ids = [(4, picking.id)]

    # Confirm picking
    picking.action_confirm()

    return picking

def _prepare_stock_moves(self):
    """
    Chuẩn bị Stock Moves cho picking
    """
    moves = []
    for line in self.order_line.filtered(lambda l: l.product_id.type in ['product', 'consu']):
        move_vals = {
            'name': self.name,
            'product_id': line.product_id.id,
            'product_uom': line.product_uom.id,
            'product_uom_qty': line.product_qty,
            'date': line.date_planned or self.date_order,
            'date_expected': line.date_planned or self.date_order,
            'location_id': self.picking_type_id.default_location_src_id.id,
            'location_dest_id': self.picking_type_id.default_location_dest_id.id,
            'picking_type_id': self.picking_type_id.id,
            'group_id': self.group_id.id,
            'origin': self.name,
            'procure_method': line._get_procure_method(),
            'company_id': self.company_id.id,
        }
        moves.append((0, 0, move_vals))

    return moves
```

### 4. Receipt Processing Workflow

#### **Receipt Creation Process**

**Trigger**: PO confirmed with stockable products

**Integration with Stock Module**:
```python
# Stock Picking Integration
class StockPicking(models.Model):
    _inherit = 'stock.picking'

    purchase_id = fields.Many2one('purchase.order', 'Purchase Order')

    def action_done(self):
        """
        Override để cập nhật PO khi receipt done
        """
        res = super().action_done()

        # Update PO line quantities
        for move in self.move_ids:
            if move.purchase_line_id:
                move.purchase_line_id._update_received_quantity()

        # Update PO invoice status
        if self.purchase_id:
            self.purchase_id._compute_invoiced()

        return res

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _update_received_quantity(self):
        """
        Cập nhật số lượng đã nhận từ stock moves
        """
        for line in self:
            # Get done quantities from stock moves
            moves = line.move_ids.filtered(
                lambda m: m.state == 'done' and m.location_dest_id.usage == 'internal'
            )

            total_received = sum(moves.mapped('product_uom_qty'))

            if line.qty_received != total_received:
                line.qty_received = total_received

            # Auto-invoice if configured
            if line._should_auto_invoice():
                line._create_invoice_line()

def _should_auto_invoice(self):
    """
    Kiểm tra có nên tự động tạo invoice line không
    """
    company = self.order_id.company_id

    # Rule 1: Auto-invoice policy
    if company.po_auto_invoice != 'ordered':
        return False

    # Rule 2: Fully received
    if self.qty_received >= self.product_qty:
        return True

    # Rule 3: Partial receipt allowed
    if company.po_auto_invoice_partial and self.qty_received > 0:
        return True

    return False
```

#### **Quality Control Integration**

**Quality Check Workflow**:
```python
def _create_quality_check(self):
    """
    Tạo Quality Check cho receipt
    """
    quality_points = self.env['quality.point'].search([
        ('product_id', '=', self.product_id.id),
        ('picking_type_id', '=', self.picking_id.picking_type_id.id),
    ])

    quality_checks = []
    for point in quality_points:
        check_vals = {
            'point_id': point.id,
            'product_id': self.product_id.id,
            'picking_id': self.picking_id.id,
            'company_id': self.company_id.id,
            'user_id': self.env.user.id,
            'quality_state': 'none',
        }
        quality_checks.append((0, 0, check_vals))

    if quality_checks:
        self.env['quality.check'].create(quality_checks)
```

### 5. Invoice Validation Workflow

#### **Three-Way Matching Process**

**Matching Logic**:
```python
def _validate_invoice_matching(self):
    """
    Thực hiện Three-way matching
    """
    # 1. PO <-> Invoice Quantity Matching
    quantity_match = self._check_quantity_match()

    # 2. PO <-> Invoice Price Matching
    price_match = self._check_price_match()

    # 3. Receipt <-> Invoice Quantity Matching
    receipt_match = self._check_receipt_match()

    return {
        'quantity_match': quantity_match,
        'price_match': price_match,
        'receipt_match': receipt_match,
        'overall_match': quantity_match and price_match and receipt_match
    }

def _check_quantity_match(self):
    """
    Kiểm tra khớp số lượng PO và Invoice
    """
    tolerance = self.company_id.po_match_tolerance or 0

    for line in self.order_line:
        invoiced_qty = sum(line.invoice_lines.mapped('quantity'))

        if abs(invoiced_qty - line.product_qty) > tolerance:
            return False

    return True

def _check_price_match(self):
    """
    Kiểm tra khớp giá PO và Invoice
    """
    tolerance = self.company_id.po_price_tolerance or 0

    for line in self.order_line:
        invoiced_price = line.invoice_lines[0].price_unit if line.invoice_lines else 0

        if invoiced_price > 0:
            price_diff = abs(invoiced_price - line.price_unit) / line.price_unit
            if price_diff > tolerance:
                return False

    return True

def _check_receipt_match(self):
    """
    Kiểm tra khớp số lượng Receipt và Invoice
    """
    tolerance = self.company_id.po_receipt_tolerance or 0

    for line in self.order_line:
        invoiced_qty = sum(line.invoice_lines.mapped('quantity'))

        if abs(invoiced_qty - line.qty_received) > tolerance:
            return False

    return True
```

#### **Invoice Status Workflow**

**State Management**:
```python
@api.depends('invoice_ids', 'order_line.invoice_lines', 'order_line.qty_received')
def _get_invoiced(self):
    """
    Tính toán trạng thái hóa đơn của PO
    """
    for order in self:
        # Rule 1: No invoices yet
        if not order.invoice_ids and not order.order_line.invoice_lines:
            order.invoice_status = 'no'
            continue

        # Rule 2: Check if fully invoiced
        total_qty = sum(order.order_line.mapped('product_qty'))
        total_invoiced = sum(order.order_line.mapped('qty_invoiced'))

        if total_invoiced >= total_qty:
            order.invoice_status = 'invoiced'
        else:
            order.invoice_status = 'to invoice'
```

### 6. Completion Workflow

#### **State: `done` (Locked)**

**Conditions for Completion**:
```python
def _check_completion_conditions(self):
    """
    Kiểm tra điều kiện để chuyển sang done state
    """
    # Rule 1: All receipts must be done
    if self.picking_ids.filtered(lambda p: p.state != 'done'):
        return False, "Vẫn còn receipt chưa hoàn thành!"

    # Rule 2: All quantities must be received or cancelled
    for line in self.order_line:
        if line.product_qty > line.qty_received and line.product_qty > 0:
            return False, f"Sản phẩm {line.name} chưa nhận đủ số lượng!"

    # Rule 3: All invoices must be validated (if configured)
    if self.company_id.po_done_require_invoice:
        if self.invoice_status != 'invoiced':
            return False, "Cần hoàn thành invoice trước khi lock PO!"

    return True, "Đáp ứng điều kiện hoàn thành"

def button_done(self):
    """
    Lock Purchase Order khi hoàn thành
    """
    self.ensure_one()

    # Check completion conditions
    can_complete, message = self._check_completion_conditions()
    if not can_complete:
        raise UserError(message)

    # Update state
    self.write({'state': 'done'})

    # Log completion
    self.message_post(
        body=_("PO đã được lock (hoàn thành)"),
        message_type='notification'
    )

    # Trigger post-completion processes
    self._post_completion_processes()

def _post_completion_processes(self):
    """
    Các process sau khi hoàn thành PO
    """
    # 1. Update vendor performance
    self._update_vendor_performance()

    # 2. Update cost accounting
    self._update_standard_price()

    # 3. Check for reorder points
    self._update_reorder_rules()

    # 4. Archive old POs (policy)
    if self.company_id.po_auto_archive_days:
        self._schedule_archiving()

def _update_vendor_performance(self):
    """
    Cập nhật performance metrics cho vendor
    """
    if not self.partner_id.supplier_rank:
        return

    # Update delivery performance
    if self.date_order and self.date_approve:
        delivery_days = (self.date_approve - self.date_order).days
        self.partner_id.write({
            'delivery_rating': self._calculate_delivery_rating(delivery_days)
        })

    # Update quality performance
    quality_issues = sum(
        self.picking_ids.mapped('quality_check_ids').mapped(
            lambda q: 1 if q.quality_state == 'fail' else 0
        )
    )

    if self.order_line:
        quality_score = max(0, 5 - quality_issues)
        self.partner_id.write({'quality_rating': quality_score})
```

## 🎯 Business Rules và Validations

### Multi-Level Approval Matrix

**Approval Rules**:
```python
def _get_approval_matrix(self):
    """
    Lấy ma trận duyệt cho PO
    """
    matrix = []
    amount = self.amount_total

    # Level 1: User Level (< company.po_approval_limit)
    if amount <= self.company_id.po_approval_limit:
        matrix.append({
            'level': 1,
            'approvers': self.env['res.users'].search([
                ('has_group', '=', 'purchase.group_purchase_manager')
            ]),
            'required': False,
            'auto_approve': True
        })

    # Level 2: Manager Level (limit < amount < double_validation)
    elif amount <= self.company_id.po_double_validation_amount:
        matrix.append({
            'level': 2,
            'approvers': self.env['res.users'].search([
                ('has_group', '=', 'purchase.group_purchase_manager')
            ]),
            'required': True,
            'auto_approve': False
        })

    # Level 3: Director Level (amount > double_validation)
    else:
        matrix.append({
            'level': 3,
            'approvers': self.env['res.users'].search([
                ('company_id', '=', self.company_id.id),
                ('has_group', '=', 'base.group_system')
            ]),
            'required': True,
            'auto_approve': False
        })

    return matrix
```

### Currency và Price Controls

**Price Validation Rules**:
```python
@api.constrains('currency_id', 'order_line.price_unit')
def _check_currency_consistency(self):
    """
    Kiểm tra tính nhất quán của currency và price
    """
    for order in self:
        for line in order.order_line:
            if line.price_unit <= 0:
                raise ValidationError(f"Giá của {line.product_id.name} phải lớn hơn 0!")

            # Check price vs supplier pricelist
            supplier_pricelist = order.partner_id.property_product_pricelist
            if supplier_pricelist:
                pricelist_price = supplier_pricelist.get_product_price(
                    line.product_id, line.product_qty, order.partner_id
                )

                price_variance = abs(line.price_unit - pricelist_price) / pricelist_price
                max_variance = order.company_id.po_price_variance_tolerance or 0.2

                if price_variance > max_variance:
                    raise ValidationError(
                        f"Giá của {line.product_id.name} vượt quá {max_variance*100}% "
                        f"so với supplier pricelist!"
                    )

@api.onchange('partner_id')
def _onchange_partner_currency(self):
    """
    Cập nhật currency khi thay đổi partner
    """
    if self.partner_id:
        # Get vendor's default currency
        vendor_currency = self.partner_id.property_purchase_currency_id

        if vendor_currency and vendor_currency != self.currency_id:
            self.currency_id = vendor_currency

            # Convert existing lines to new currency
            for line in self.order_line:
                if line.price_unit > 0:
                    # Convert price from old currency to new currency
                    old_rate = self.env['res.currency'].browse(
                        self._origin.currency_id.id
                    ).rate
                    new_rate = vendor_currency.rate

                    line.price_unit = (line.price_unit * new_rate) / old_rate
```

### Date và Deadline Controls

**Date Validation**:
```python
@api.constrains('date_order', 'date_planned')
def _check_date_consistency(self):
    """
    Kiểm tra tính hợp lệ của dates
    """
    for order in self:
        if order.date_order and order.date_planned:
            # Order date cannot be after planned date
            if order.date_order > order.date_planned:
                raise ValidationError(
                    "Ngày đặt hàng không thể sau ngày giao hàng dự kiến!"
                )

            # Check lead time constraints
            min_lead_time = order.company_id.po_min_lead_time or 1
            max_lead_time = order.company_id.po_max_lead_time or 365

            lead_time_days = (order.date_planned - order.date_order).days

            if lead_time_days < min_lead_time:
                raise ValidationError(
                    f"Lead time tối thiểu là {min_lead_time} ngày!"
                )

            if lead_time_days > max_lead_time:
                raise ValidationError(
                    f"Lead time không thể vượt quá {max_lead_time} ngày!"
                )

def _compute_expected_arrival(self):
    """
    Tính toán ngày đến dự kiến dựa trên supplier lead time
    """
    for order in self:
        if order.date_order and order.partner_id:
            # Get vendor's average lead time
            avg_lead_time = order.partner_id.property_supplier_delay or 7

            # Add buffer days from company policy
            buffer_days = order.company_id.po_lead_time_buffer or 2

            # Calculate expected arrival
            order.date_planned = order.date_order + timedelta(
                days=avg_lead_time + buffer_days
            )
```

## 🔗 Integration Points

### Inventory Integration Workflows

**Stock Movement Creation**:
```python
def _create_stock_moves(self):
    """
    Tạo stock moves cho receipt
    """
    StockMove = self.env['stock.move']

    for line in self.order_line:
        # Skip non-stockable products
        if line.product_id.type not in ['product', 'consu']:
            continue

        # Get procurement method
        procure_method = line._get_procure_method()

        move_vals = {
            'name': self.name,
            'product_id': line.product_id.id,
            'product_uom_qty': line.product_qty,
            'product_uom': line.product_uom.id,
            'date': line.date_planned or self.date_order,
            'date_expected': line.date_planned or self.date_order,
            'partner_id': self.partner_id.id,
            'location_id': self._get_source_location().id,
            'location_dest_id': self._get_destination_location().id,
            'procure_method': procure_method,
            'origin': self.name,
            'company_id': self.company_id.id,
            'purchase_line_id': line.id,
            'group_id': self.group_id.id,
        }

        StockMove.create(move_vals)

def _get_source_location(self):
    """
    Lấy source location cho stock move
    """
    if self.dest_address_id:
        # Dropshipping
        return self.env.ref('stock.stock_location_suppliers')
    else:
        # Standard receipt
        return self.picking_type_id.default_location_src_id

def _get_destination_location(self):
    """
    Lấy destination location cho stock move
    """
    if self.dest_address_id:
        # Dropshipping to customer address
        customer_location = self.env['stock.location'].search([
            ('usage', '=', 'customer'),
            ('partner_id', '=', self.dest_address_id.id)
        ], limit=1)
        return customer_location or self.env.ref('stock.stock_location_customers')
    else:
        # Standard receipt to stock
        return self.picking_type_id.default_location_dest_id
```

### Accounting Integration Workflows

**Invoice Generation Automation**:
```python
def _create_vendor_bills(self):
    """
    Tự động tạo vendor bills
    """
    AccountMove = self.env['account.move']

    for order in self:
        # Check auto-invoice policy
        if order.company_id.po_auto_invoice == 'never':
            continue

        # Check if conditions met
        if not order._should_create_invoice():
            continue

        # Create vendor bill
        bill_vals = {
            'move_type': 'in_invoice',
            'partner_id': order.partner_id.id,
            'purchase_id': order.id,
            'invoice_date': fields.Date.today(),
            'currency_id': order.currency_id.id,
            'company_id': order.company_id.id,
            'journal_id': order.partner_id.property_purchase_journal_id.id,
            'invoice_line_ids': order._prepare_invoice_lines(),
        }

        bill = AccountMove.create(bill_vals)

        # Post bill if configured
        if order.company_id.po_auto_post_invoice:
            bill.action_post()

        # Link to PO
        order.invoice_ids = [(4, bill.id)]

def _should_create_invoice(self):
    """
    Kiểm tra điều kiện tạo invoice
    """
    # Policy check
    if self.company_id.po_auto_invoice == 'ordered':
        return True
    elif self.company_id.po_auto_invoice == 'delivered':
        return self._all_delivered()

    return False

def _all_delivered(self):
    """
    Kiểm tra tất cả products đã được delivered
    """
    for line in self.order_line:
        if line.product_id.type in ['product', 'consu']:
            if line.qty_received < line.product_qty:
                return False
    return True
```

### Vendor Management Integration

**Performance Tracking**:
```python
def _update_vendor_metrics(self):
    """
    Cập nhật metrics cho vendor
    """
    vendor = self.partner_id

    # Get all orders from this vendor
    vendor_orders = self.search([
        ('partner_id', '=', vendor.id),
        ('state', 'in', ['purchase', 'done'])
    ])

    # Calculate metrics
    total_orders = len(vendor_orders)
    total_amount = sum(vendor_orders.mapped('amount_total'))
    avg_delivery_days = self._calculate_avg_delivery_time(vendor_orders)
    on_time_delivery_rate = self._calculate_on_time_rate(vendor_orders)
    quality_score = self._calculate_quality_score(vendor_orders)

    # Update vendor
    vendor.write({
        'total_po_count': total_orders,
        'total_po_amount': total_amount,
        'avg_delivery_days': avg_delivery_days,
        'on_time_delivery_rate': on_time_delivery_rate,
        'quality_rating': quality_score,
        'last_order_date': self.date_order,
    })

def _calculate_on_time_rate(self, orders):
    """
    Tính toán tỷ lệ giao hàng đúng hạn
    """
    on_time_count = 0
    total_count = 0

    for order in orders:
        if order.date_planned and order.picking_ids:
            # Check if all pickings done on time
            on_time = True
            for picking in order.picking_ids:
                if picking.state == 'done':
                    if picking.date_done > order.date_planned:
                        on_time = False
                        break
                else:
                    on_time = False
                    break

            total_count += 1
            if on_time:
                on_time_count += 1

    return (on_time_count / total_count * 100) if total_count > 0 else 0
```

## 📊 Performance Monitoring

### Workflow Metrics

**Key Performance Indicators**:
```python
def _get_workflow_metrics(self):
    """
    Lấy metrics cho workflow performance
    """
    return {
        'approval_time': self._calculate_approval_time(),
        'processing_time': self._calculate_processing_time(),
        'vendor_response_time': self._calculate_vendor_response_time(),
        'delivery_accuracy': self._calculate_delivery_accuracy(),
        'invoice_processing_time': self._calculate_invoice_time(),
        'workflow_completion_rate': self._calculate_completion_rate(),
    }

def _calculate_approval_time(self):
    """
    Tính thời gian approval trung bình
    """
    approved_orders = self.search([
        ('state', 'in', ['purchase', 'done']),
        ('date_approve', '!=', False),
        ('date_order', '!=', False),
    ])

    if not approved_orders:
        return 0

    total_time = sum([
            (order.date_approve - order.date_order).total_seconds()
            for order in approved_orders
        ])

    avg_seconds = total_time / len(approved_orders)
    return avg_seconds / 3600  # Convert to hours

def _calculate_completion_rate(self):
    """
    Tính tỷ lệ hoàn thành workflow
    """
    total_orders = self.search([
        ('date_order', '>=', fields.Date.today() - timedelta(days=30))
    ])

    if not total_orders:
        return 0

    completed_orders = total_orders.filtered(
        lambda o: o.state in ['done', 'cancel']
    )

    return len(completed_orders) / len(total_orders) * 100
```

## 🔄 Workflow Optimization

### Automation Rules

**Auto-Action Configuration**:
```python
def _apply_workflow_automation(self):
    """
    Áp dụng automation rules cho workflow
    """
    # Rule 1: Auto-approval for small amounts
    if self.amount_total <= self.company_id.po_auto_approve_limit:
        if self._approval_allowed():
            self.button_approve(force=True)

    # Rule 2: Auto-confirmation for trusted vendors
    if self.partner_id in self.company_id.trusted_vendor_ids:
        self.button_confirm()

    # Rule 3: Auto-invoice for regular products
    if self._is_regular_purchase():
        self._create_vendor_bills()

    # Rule 4: Auto-archive old completed orders
    if self.state == 'done' and self._should_auto_archive():
        self._archive_order()

def _is_regular_purchase(self):
    """
    Kiểm tra có phải là regular purchase không
    """
    # All products are regular (no custom, no MRP)
    regular_lines = self.order_line.filtered(
        lambda l: l.product_id.type == 'product' and
        not l.product_id.bom_ids and
        not l.product_id.customization
    )

    return len(regular_lines) == len(self.order_line)
```

---

**Next Steps**: Đọc [04_integration_patterns.md](04_integration_patterns.md) để hiểu detailed integration examples.