# 💻 Code Examples & Customization Patterns

## 🎯 Giới Thiệu

Collection of practical code examples và customization patterns cho Odoo Purchase module. Bao gồm các mẫu code thường dùng cho extending functionality, custom workflows, và integration với modules khác.

## 📂 Table of Contents

1. **Model Extensions** - Custom fields và methods
2. **Workflow Customizations** - State transitions và approvals
3. **Integration Examples** - Cross-module implementations
4. **Custom Reports** - Purchase analytics và reporting
5. **API Examples** - External system integrations
6. **Advanced Patterns** - Complex business logic

## 🔧 Model Extensions

### 1. Custom Purchase Order Fields

#### **Adding Business-Specific Fields**

```python
# File: custom_purchase/models/purchase_order.py
from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # Custom business fields
    project_id = fields.Many2one('project.project', 'Project')
    department_id = fields.Many2one('hr.department', 'Department')
    priority_level = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], 'Priority Level', default='medium')

    # Financial fields
    budget_line_id = fields.Many2one('crossovered.budget.lines', 'Budget Line')
    cost_center_id = fields.Many2one('account.analytic.account', 'Cost Center')

    # Approval fields
    requested_by_id = fields.Many2one('res.users', 'Requested By', default=lambda self: self.env.user)
    approved_by_id = fields.Many2one('res.users', 'Approved By')
    approval_notes = fields.Text('Approval Notes')

    # Delivery fields
    delivery_instructions = fields.Text('Delivery Instructions')
    delivery_contact_id = fields.Many2one('res.partner', 'Delivery Contact')

    # Computed fields
    budget_remaining = fields.Float('Budget Remaining', compute='_compute_budget_remaining')
    days_overdue = fields.Integer('Days Overdue', compute='_compute_days_overdue')

    @api.depends('amount_total', 'budget_line_id')
    def _compute_budget_remaining(self):
        """Tính toán budget còn lại"""
        for order in self:
            if order.budget_line_id:
                budget = order.budget_line_id
                spent = sum(budget.crossovered_budget_line.filtered(
                    lambda bl: bl.paid_amount > 0
                ).mapped('paid_amount'))
                order.budget_remaining = budget.planned_amount - spent - order.amount_total
            else:
                order.budget_remaining = 0

    @api.depends('date_planned')
    def _compute_days_overdue(self):
        """Tính toán số ngày quá hạn"""
        for order in self:
            if order.date_planned and order.state == 'purchase':
                today = fields.Date.today()
                planned_date = order.date_planned.date()
                order.days_overdue = max(0, (today - planned_date).days)
            else:
                order.days_overdue = 0

    @api.onchange('project_id')
    def _onchange_project_id(self):
        """Cập nhật department dựa trên project"""
        if self.project_id and self.project_id.department_id:
            self.department_id = self.project_id.department_id

    def _prepare_budget_validation(self):
        """Chuẩn bị validation cho budget"""
        if self.budget_line_id:
            budget = self.budget_line_id
            available = budget.planned_amount - budget.allocated_amount

            if self.amount_total > available:
                raise UserError(
                    f"Purchase amount ({self.amount_total}) exceeds available budget ({available})"
                )

    def write(self, vals):
        """Override để validate budget trước khi thay đổi"""
        if 'amount_total' in vals or 'budget_line_id' in vals:
            self._prepare_budget_validation()

        return super().write(vals)

    def button_approve(self, force=False):
        """Override để log additional approval information"""
        res = super().button_approve(force=force)

        # Log additional approval info
        self.write({
            'approved_by_id': self.env.user.id,
            'approval_date': fields.Datetime.now(),
        })

        return res
```

### 2. Purchase Order Line Customization

#### **Advanced Line Logic**

```python
# File: custom_purchase/models/purchase_order_line.py
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # Custom fields
    specification = fields.Text('Product Specification')
    alternative_product_ids = fields.Many2many(
        'product.product',
        'po_line_alternative_rel',
        'line_id', 'product_id',
        'Alternative Products'
    )
    quality_requirement_ids = fields.One2many(
        'quality.requirement.line', 'po_line_id', 'Quality Requirements'
    )
    warranty_months = fields.Integer('Warranty (Months)', default=12)

    # Computed fields
    discount_amount = fields.Float('Discount Amount', compute='_compute_discount_amount')
    final_price = fields.Float('Final Price', compute='_compute_final_price')
    price_variance = fields.Float('Price Variance %', compute='_compute_price_variance')

    @api.depends('price_unit', 'discount')
    def _compute_discount_amount(self):
        """Tính toán discount amount"""
        for line in self:
            line.discount_amount = line.price_unit * (line.discount / 100)

    @api.depends('price_unit', 'discount')
    def _compute_final_price(self):
        """Tính toán final price sau discount"""
        for line in self:
            line.final_price = line.price_unit * (1 - line.discount / 100)

    def _compute_price_variance(self):
        """Tính toán price variance so với standard price"""
        for line in self:
            if line.product_id and line.product_id.standard_price > 0:
                variance = ((line.final_price - line.product_id.standard_price) /
                           line.product_id.standard_price) * 100
                line.price_variance = variance
            else:
                line.price_variance = 0

    @api.onchange('product_id')
    def _onchange_product_id_custom(self):
        """Custom logic khi thay đổi sản phẩm"""
        if self.product_id:
            # Set default warranty
            self.warranty_months = self.product_id.warranty_months or 12

            # Get quality requirements
            self.quality_requirement_ids = [
                (0, 0, {
                    'requirement_type': 'dimensional',
                    'specification': req.name,
                    'required_value': req.default_value,
                })
                for req in self.product_id.quality_requirement_ids
            ]

    def _check_quality_requirements(self):
        """Validate quality requirements"""
        if not self.quality_requirement_ids:
            return True

        for req in self.quality_requirement_ids:
            if not req.meets_requirement:
                raise ValidationError(
                    f"Quality requirement '{req.requirement_type}' not met for {self.product_id.name}"
                )

        return True

    def _prepare_alternative_suggestions(self):
        """Gợi ý alternative products"""
        if not self.product_id:
            return []

        # Get similar products from same category
        alternatives = self.env['product.product'].search([
            ('categ_id', '=', self.product_id.categ_id.id),
            ('purchase_ok', '=', True),
            ('id', '!=', self.product_id.id),
        ], limit=5)

        return alternatives

class QualityRequirementLine(models.Model):
    _name = 'quality.requirement.line'
    _description = 'Quality Requirement for Purchase Line'

    po_line_id = fields.Many2one('purchase.order.line', 'Purchase Line')
    requirement_type = fields.Selection([
        ('dimensional', 'Dimensional'),
        ('material', 'Material'),
        ('performance', 'Performance'),
        ('safety', 'Safety'),
    ], 'Requirement Type')
    specification = fields.Char('Specification')
    required_value = fields.Char('Required Value')
    actual_value = fields.Char('Actual Value')
    meets_requirement = fields.Boolean('Meets Requirement')
    test_date = fields.Date('Test Date')
    tested_by_id = fields.Many2one('res.users', 'Tested By')
```

## 🔄 Workflow Customizations

### 1. Custom Approval Workflow

#### **Multi-Level Approval System**

```python
# File: custom_purchase/models/purchase_approval.py
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class PurchaseApproval(models.Model):
    _name = 'purchase.approval'
    _description = 'Purchase Approval Workflow'
    _order = 'sequence, id'

    purchase_order_id = fields.Many2one('purchase.order', 'Purchase Order')
    approver_id = fields.Many2one('res.users', 'Approver', required=True)
    approval_type = fields.Selection([
        ('manager', 'Manager Approval'),
        ('director', 'Director Approval'),
        ('finance', 'Finance Approval'),
        ('ceo', 'CEO Approval'),
    ], 'Approval Type', required=True)
    sequence = fields.Integer('Sequence', required=True)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('skipped', 'Skipped'),
    ], 'Status', default='pending')
    approval_date = fields.Datetime('Approval Date')
    rejection_reason = fields.Text('Rejection Reason')
    minimum_amount = fields.Float('Minimum Amount')
    maximum_amount = fields.Float('Maximum Amount')
    auto_approve_amount = fields.Float('Auto-Approve Amount')

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    approval_ids = fields.One2many('purchase.approval', 'purchase_order_id', 'Approvals')
    current_approval_id = fields.Many2one('purchase.approval', 'Current Approval')
    approval_required = fields.Boolean('Approval Required', compute='_compute_approval_required')
    fully_approved = fields.Boolean('Fully Approved', compute='_compute_fully_approved')

    @api.depends('amount_total', 'approval_ids')
    def _compute_approval_required(self):
        """Kiểm tra có cần approval không"""
        for order in self:
            order.approval_required = order._get_required_approvals() and order.amount_total > 0

    @api.depends('approval_ids.status')
    def _compute_fully_approved(self):
        """Kiểm tra approval status"""
        for order in self:
            required_approvals = order._get_required_approvals()
            approved_count = len(order.approval_ids.filtered(
                lambda a: a.status == 'approved'
            ))
            order.fully_approved = len(required_approvals) == approved_count

    def _get_required_approvals(self):
        """Lấy các approvals cần thiết dựa trên amount và rules"""
        approvals = []
        amount = self.amount_total

        # Get company approval matrix
        company = self.company_id

        # Level 1: Manager Approval
        if amount > company.po_manager_approval_min:
            approvals.append({
                'type': 'manager',
                'amount_range': (company.po_manager_approval_min, company.po_manager_approval_max),
            })

        # Level 2: Director Approval
        if amount > company.po_director_approval_min:
            approvals.append({
                'type': 'director',
                'amount_range': (company.po_director_approval_min, company.po_director_approval_max),
            })

        # Level 3: Finance Approval
        if amount > company.po_finance_approval_min:
            approvals.append({
                'type': 'finance',
                'amount_range': (company.po_finance_approval_min, float('inf')),
            })

        # Level 4: CEO Approval
        if amount > company.po_ceo_approval_min:
            approvals.append({
                'type': 'ceo',
                'amount_range': (company.po_ceo_approval_min, float('inf')),
            })

        return approvals

    def _create_approval_workflow(self):
        """Tạo approval workflow"""
        required_approvals = self._get_required_approvals()

        self.approval_ids.unlink()  # Clear existing approvals

        for i, approval_config in enumerate(required_approvals):
            approvers = self._get_approvers_for_type(approval_config['type'])

            for approver in approvers:
                self.env['purchase.approval'].create({
                    'purchase_order_id': self.id,
                    'approver_id': approver.id,
                    'approval_type': approval_config['type'],
                    'sequence': i + 1,
                    'minimum_amount': approval_config['amount_range'][0],
                    'maximum_amount': approval_config['amount_range'][1],
                    'auto_approve_amount': self._get_auto_approve_amount(approval_config['type']),
                })

    def _get_approvers_for_type(self, approval_type):
        """Lấy approvers dựa trên type"""
        User = self.env['res.users']

        if approval_type == 'manager':
            # Get department manager
            if self.department_id and self.department_id.manager_id:
                return User.browse(self.department_id.manager_id.id)

            # Fallback to purchase managers
            return User.search([
                ('has_group', '=', 'purchase.group_purchase_manager'),
                ('company_id', '=', self.company_id.id),
            ])

        elif approval_type == 'director':
            # Get users with director role
            return User.search([
                ('groups_id', 'in', [self.env.ref('custom_purchase.group_purchase_director').id]),
                ('company_id', '=', self.company_id.id),
            ])

        elif approval_type == 'finance':
            # Get finance users
            return User.search([
                ('groups_id', 'in', [self.env.ref('account.group_account_manager').id]),
                ('company_id', '=', self.company_id.id),
            ])

        elif approval_type == 'ceo':
            # Get CEO/Admin
            return User.search([
                ('groups_id', 'in', [self.env.ref('base.group_system').id]),
                ('company_id', '=', self.company_id.id),
            ], limit=1)

        return User.browse()

    def button_confirm(self):
        """Override để tạo approval workflow"""
        self._create_approval_workflow()

        # Check if immediate approval possible
        if self._check_immediate_approval():
            return super().button_confirm()
        else:
            # Move to approval state
            self.write({'state': 'to approve'})
            self._notify_next_approver()
            return True

    def _check_immediate_approval(self):
        """Kiểm tra có thể immediate approval không"""
        for approval in self.approval_ids:
            if (self.amount_total <= approval.auto_approve_amount and
                approval.approver_id.id == self.env.user.id):
                approval.write({
                    'status': 'approved',
                    'approval_date': fields.Datetime.now(),
                })
                return True
        return False

    def _notify_next_approver(self):
        """Notify next approver"""
        next_approval = self.approval_ids.filtered(
            lambda a: a.status == 'pending'
        ).sorted('sequence')

        if next_approval:
            approval = next_approval[0]
            template = self.env.ref('custom_purchase.email_template_purchase_approval')
            if template:
                template.send_mail(
                    self.id,
                    email_values={
                        'recipient_ids': [(4, approval.approver_id.partner_id.id)],
                    },
                    force_send=True
                )

    def action_approve(self, approval_id=None, approve_all=False):
        """Approve single hoặc multiple approvals"""
        UserError("Approval functionality moved to Approval Wizard")

class PurchaseApprovalWizard(models.TransientModel):
    _name = 'purchase.approval.wizard'
    _description = 'Purchase Approval Wizard'

    approval_id = fields.Many2one('purchase.approval', 'Approval')
    action = fields.Selection([
        ('approve', 'Approve'),
        ('reject', 'Reject'),
    ], 'Action', required=True)
    rejection_reason = fields.Text('Rejection Reason')
    approve_all = fields.Boolean('Approve All Levels')

    def action_confirm(self):
        """Xử lý approval action"""
        if self.action == 'approve':
            self._process_approval()
        elif self.action == 'reject':
            self._process_rejection()

    def _process_approval(self):
        """Xử lý approval"""
        approval = self.approval_id

        # Update approval status
        approval.write({
            'status': 'approved',
            'approval_date': fields.Datetime.now(),
        })

        po = approval.purchase_order_id

        # Log approval
        po.message_post(
            body=_("Approved by %s") % self.env.user.name,
            message_type='notification'
        )

        # Check if fully approved
        if po.fully_approved:
            po.write({'state': 'purchase'})
            po._execute_purchase_order()

    def _process_rejection(self):
        """Xử lý rejection"""
        approval = self.approval_id
        po = approval.purchase_order_id

        # Update approval status
        approval.write({
            'status': 'rejected',
            'rejection_reason': self.rejection_reason,
        })

        # Cancel PO
        po.button_cancel()

        # Log rejection
        po.message_post(
            body=_("Rejected by %s: %s") % (self.env.user.name, self.rejection_reason),
            message_type='notification'
        )
```

### 2. Custom State Transitions

#### **Advanced State Machine**

```python
# File: custom_purchase/models/purchase_state.py
from odoo import models, fields, api
from odoo.exceptions import UserError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # Custom states
    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('bid_received', 'Bid Received'),
        ('bid_comparison', 'Bid Comparison'),
        ('to approve', 'To Approve'),
        ('negotiation', 'Price Negotiation'),
        ('purchase', 'Purchase Order'),
        ('partial_receipt', 'Partial Receipt'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, index=True, copy=False, default='draft')

    # Additional state fields
    negotiation_history_ids = fields.One2many('purchase.negotiation.history', 'order_id', 'Negotiation History')
    bid_comparison_ids = fields.One2many('purchase.bid.comparison', 'order_id', 'Bid Comparisons')
    partial_delivery_count = fields.Integer('Partial Deliveries', compute='_compute_partial_deliveries')

    def _compute_partial_deliveries(self):
        """Tính toán số lần partial delivery"""
        for order in self:
            if order.picking_ids:
                done_pickings = order.picking_ids.filtered(lambda p: p.state == 'done')
                order.partial_delivery_count = len(done_pickings)
            else:
                order.partial_delivery_count = 0

    def action_receive_bids(self):
        """Nhận bids từ vendors"""
        if self.state != 'sent':
            raise UserError("Chỉ có thể nhận bids từ RFQ đã được gửi!")

        self.write({'state': 'bid_received'})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Received Bids',
            'view_mode': 'tree,form',
            'res_model': 'purchase.bid',
            'domain': [('rfq_id', '=', self.id)],
            'context': {'default_rfq_id': self.id},
        }

    def action_compare_bids(self):
        """So sánh bids"""
        bids = self.env['purchase.bid'].search([('rfq_id', '=', self.id)])

        if len(bids) < 2:
            raise UserError("Cần ít nhất 2 bids để so sánh!")

        self.write({'state': 'bid_comparison'})

        # Create bid comparison
        comparison = self.env['purchase.bid.comparison'].create({
            'order_id': self.id,
            'comparison_date': fields.Datetime.now(),
        })

        # Add bids to comparison
        for bid in bids:
            comparison.line_ids.create({
                'comparison_id': comparison.id,
                'bid_id': bid.id,
                'vendor_id': bid.vendor_id.id,
                'total_amount': bid.total_amount,
                'delivery_date': bid.proposed_delivery_date,
                'payment_terms': bid.payment_terms,
                'warranty': bid.warranty_months,
            })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Compare Bids',
            'view_mode': 'form',
            'res_model': 'purchase.bid.comparison',
            'res_id': comparison.id,
        }

    def action_start_negotiation(self):
        """Bắt đàu đàm phán với selected vendor"""
        if self.state != 'bid_comparison':
            raise UserError("Cần so sánh bids trước khi đàm phán!")

        # Get best bid
        best_bid = self._get_best_bid()
        if not best_bid:
            raise UserError("Chưa có bid nào được chọn!")

        self.write({
            'state': 'negotiation',
            'partner_id': best_bid.vendor_id.id,
        })

        # Copy bid prices to PO
        for line in best_bid.line_ids:
            po_line = self.order_line.filtered(lambda l: l.product_id == line.product_id)
            if po_line:
                po_line.write({
                    'price_unit': line.unit_price,
                    'discount': line.discount,
                })

        return True

    def action_end_negotiation(self):
        """Kết thúc đàm phán và chuyển sang approval"""
        if self.state != 'negotiation':
            raise UserError("Chỉ có thể kết thúc đàm phán từ state 'negotiation'!")

        # Record final negotiated prices
        negotiation = self.env['purchase.negotiation.history'].create({
            'order_id': self.id,
            'vendor_id': self.partner_id.id,
            'negotiated_date': fields.Datetime.now(),
            'negotiated_by_id': self.env.user.id,
        })

        for line in self.order_line:
            negotiation.line_ids.create({
                'negotiation_id': negotiation.id,
                'product_id': line.product_id.id,
                'final_price': line.price_unit,
                'final_discount': line.discount,
            })

        # Move to approval
        self.button_confirm()
        return True

    def _get_best_bid(self):
        """Lấy best bid dựa trên criteria"""
        bids = self.env['purchase.bid'].search([('rfq_id', '=', self.id)])

        if not bids:
            return None

        best_bid = None
        best_score = -1

        for bid in bids:
            score = self._calculate_bid_score(bid)
            if score > best_score:
                best_score = score
                best_bid = bid

        return best_bid

    def _calculate_bid_score(self, bid):
        """Tính toán bid score"""
        score = 0

        # Price score (40% weight)
        min_price = min(self.env['purchase.bid'].search([('rfq_id', '=', self.id)]).mapped('total_amount'))
        price_score = (min_price / bid.total_amount) * 40 if bid.total_amount > 0 else 0
        score += price_score

        # Delivery date score (30% weight)
        if bid.proposed_delivery_date:
            earliest_date = min(
                self.env['purchase.bid'].search([('rfq_id', '=', self.id)])
                .mapped('proposed_delivery_date')
                .filtered(lambda d: d)
            )
            if earliest_date:
                days_diff = (bid.proposed_delivery_date - earliest_date).days
                delivery_score = max(0, 30 - days_diff)  # Earlier is better
                score += delivery_score

        # Vendor reliability score (20% weight)
        vendor_score = bid.vendor_id.reliability_score or 0
        score += vendor_score * 0.2

        # Payment terms score (10% weight)
        # Better payment terms = higher score
        payment_score = 10  # Simplified for example
        score += payment_score

        return score

class PurchaseNegotiationHistory(models.Model):
    _name = 'purchase.negotiation.history'
    _description = 'Purchase Negotiation History'
    _order = 'negotiated_date desc'

    order_id = fields.Many2one('purchase.order', 'Purchase Order')
    vendor_id = fields.Many2one('res.partner', 'Vendor')
    negotiated_date = fields.Datetime('Negotiated Date')
    negotiated_by_id = fields.Many2one('res.users', 'Negotiated By')
    notes = fields.Text('Negotiation Notes')
    line_ids = fields.One2many('purchase.negotiation.line', 'negotiation_id', 'Negotiated Lines')

class PurchaseNegotiationLine(models.Model):
    _name = 'purchase.negotiation.line'
    _description = 'Purchase Negotiation Line'

    negotiation_id = fields.Many2one('purchase.negotiation.history', 'Negotiation')
    product_id = fields.Many2one('product.product', 'Product')
    final_price = fields.Float('Final Price')
    final_discount = fields.Float('Final Discount %')
    negotiation_notes = fields.Text('Line Notes')
```

## 🔄 Integration Examples

### 1. E-Commerce Integration

#### **Sync với External E-Commerce Platform**

```python
# File: ecommerce_purchase/models/ecommerce_sync.py
import json
import requests
from odoo import models, fields, api

class EcommercePurchaseSync(models.Model):
    _name = 'ecommerce.purchase.sync'
    _description = 'E-Commerce Purchase Synchronization'

    purchase_order_id = fields.Many2one('purchase.order', 'Purchase Order')
    platform = fields.Selection([
        ('shopify', 'Shopify'),
        ('woocommerce', 'WooCommerce'),
        ('magento', 'Magento'),
        ('amazon', 'Amazon'),
    ], 'Platform', required=True)
    external_order_id = fields.Char('External Order ID')
    sync_status = fields.Selection([
        ('pending', 'Pending'),
        ('syncing', 'Syncing'),
        ('synced', 'Synced'),
        ('error', 'Error'),
    ], 'Sync Status', default='pending')
    sync_date = fields.Datetime('Last Sync Date')
    error_message = fields.Text('Error Message')
    sync_data = fields.Text('Sync Data (JSON)')

    def action_sync_to_platform(self):
        """Sync PO đến e-commerce platform"""
        for record in self:
            try:
                record.write({'sync_status': 'syncing'})

                if record.platform == 'shopify':
                    record._sync_to_shopify()
                elif record.platform == 'woocommerce':
                    record._sync_to_woocommerce()
                elif record.platform == 'magento':
                    record._sync_to_magento()
                elif record.platform == 'amazon':
                    record._sync_to_amazon()

                record.write({
                    'sync_status': 'synced',
                    'sync_date': fields.Datetime.now(),
                    'error_message': False,
                })

            except Exception as e:
                record.write({
                    'sync_status': 'error',
                    'error_message': str(e),
                })

    def _sync_to_shopify(self):
        """Sync đến Shopify"""
        po = self.purchase_order_id
        shopify_config = self.env['shopify.config'].search([], limit=1)

        if not shopify_config:
            raise Exception("Shopify configuration not found")

        # Prepare order data
        order_data = {
            'order': {
                'line_items': [],
                'customer': {
                    'id': self._get_shopify_customer_id(po.partner_id)
                },
                'financial_status': 'pending',
                'total_price': str(po.amount_total),
                'currency': po.currency_id.name,
                'tags': 'purchase_order',
                'note': f"PO Reference: {po.name}"
            }
        }

        # Add line items
        for line in po.order_line:
            shopify_product_id = self._get_shopify_product_id(line.product_id)
            if shopify_product_id:
                order_data['order']['line_items'].append({
                    'variant_id': shopify_product_id,
                    'quantity': line.product_qty,
                    'price': str(line.price_unit)
                })

        # Send to Shopify
        headers = {
            'Content-Type': 'application/json',
            'X-Shopify-Access-Token': shopify_config.access_token
        }

        response = requests.post(
            f"https://{shopify_config.shop_url}/admin/api/2023-01/orders.json",
            json=order_data,
            headers=headers
        )

        if response.status_code == 201:
            result = response.json()
            self.external_order_id = str(result['order']['id'])
            self.sync_data = json.dumps(result)
        else:
            raise Exception(f"Shopify API Error: {response.text}")

    def _sync_to_woocommerce(self):
        """Sync đến WooCommerce"""
        po = self.purchase_order_id
        wc_config = self.env['woocommerce.config'].search([], limit=1)

        if not wc_config:
            raise Exception("WooCommerce configuration not found")

        # Prepare order data
        order_data = {
            'status': 'pending',
            'customer_id': self._get_wc_customer_id(po.partner_id),
            'total': po.amount_total,
            'currency': po.currency_id.name,
            'line_items': []
        }

        # Add line items
        for line in po.order_line:
            wc_product_id = self._get_wc_product_id(line.product_id)
            if wc_product_id:
                order_data['line_items'].append({
                    'product_id': wc_product_id,
                    'quantity': line.product_qty,
                    'price': line.price_unit
                })

        # Send to WooCommerce
        headers = {
            'Content-Type': 'application/json',
        }

        auth = (wc_config.consumer_key, wc_config.consumer_secret)
        response = requests.post(
            f"{wc_config.url}/wp-json/wc/v3/orders",
            json=order_data,
            headers=headers,
            auth=auth
        )

        if response.status_code == 201:
            result = response.json()
            self.external_order_id = str(result['id'])
            self.sync_data = json.dumps(result)
        else:
            raise Exception(f"WooCommerce API Error: {response.text}")

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    ecommerce_sync_ids = fields.One2many(
        'ecommerce.purchase.sync',
        'purchase_order_id',
        'E-Commerce Sync'
    )
    needs_ecommerce_sync = fields.Boolean(
        'Needs E-Commerce Sync',
        compute='_compute_needs_ecommerce_sync'
    )

    @api.depends('partner_id')
    def _compute_needs_ecommerce_sync(self):
        """Kiểm tra có cần sync với e-commerce không"""
        for order in self:
            order.needs_ecommerce_sync = bool(
                order.partner_id.ecommerce_platform and
                order.partner_id.is_ecommerce_customer
            )

    def button_approve(self, force=False):
        """Override để tự động sync với e-commerce"""
        res = super().button_approve(force=force)

        # Auto-sync to e-commerce if needed
        for order in self:
            if order.needs_ecommerce_sync:
                order._auto_sync_to_ecommerce()

        return res

    def _auto_sync_to_ecommerce(self):
        """Tự động sync đến e-commerce platform"""
        if not self.needs_ecommerce_sync:
            return

        # Create sync record
        sync_record = self.env['ecommerce.purchase.sync'].create({
            'purchase_order_id': self.id,
            'platform': self.partner_id.ecommerce_platform,
        })

        # Trigger sync in background
        sync_record.with_delay()._action_sync_to_platform()

class ResPartner(models.Model):
    _inherit = 'res.partner'

    ecommerce_platform = fields.Selection([
        ('shopify', 'Shopify'),
        ('woocommerce', 'WooCommerce'),
        ('magento', 'Magento'),
        ('amazon', 'Amazon'),
    ], 'E-Commerce Platform')
    is_ecommerce_customer = fields.Boolean('Is E-Commerce Customer')
    shopify_customer_id = fields.Char('Shopify Customer ID')
    wc_customer_id = fields.Integer('WooCommerce Customer ID')
    ecommerce_sync_enabled = fields.Boolean('E-Commerce Sync Enabled')
```

### 2. ERP Integration

#### **SAP Integration Example**

```python
# File: sap_purchase/models/sap_integration.py
import json
import logging
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class SAPIntegrationConfig(models.Model):
    _name = 'sap.integration.config'
    _description = 'SAP Integration Configuration'

    name = fields.Char('Configuration Name', required=True)
    sap_host = fields.Char('SAP Host', required=True)
    sap_port = fields.Integer('SAP Port', required=True)
    sap_client = fields.Char('SAP Client', required=True)
    username = fields.Char('Username', required=True)
    password = fields.Char('Password', required=True)
    company_code = fields.Char('Company Code', required=True)
    purchasing_org = fields.Char('Purchasing Organization', required=True)
    active = fields.Boolean('Active', default=True)

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    sap_document_number = fields.Char('SAP Document Number')
    sap_sync_status = fields.Selection([
        ('pending', 'Pending'),
        ('syncing', 'Syncing'),
        ('synced', 'Synced'),
        ('error', 'Error'),
    ], 'SAP Sync Status', default='pending')
    sap_sync_date = fields.Datetime('Last SAP Sync')
    sap_sync_error = fields.Text('SAP Sync Error')

    def action_sync_to_sap(self):
        """Sync PO đến SAP"""
        for order in self:
            if order.sap_sync_status not in ['pending', 'error']:
                continue

            try:
                order.write({'sap_sync_status': 'syncing'})

                sap_config = self.env['sap.integration.config'].search([
                    ('active', '=', True)
                ], limit=1)

                if not sap_config:
                    raise UserError("SAP configuration not found!")

                # Prepare SAP data
                sap_data = order._prepare_sap_data()

                # Send to SAP
                sap_response = order._send_to_sap(sap_config, sap_data)

                # Update PO with SAP response
                order.write({
                    'sap_document_number': sap_response.get('document_number'),
                    'sap_sync_status': 'synced',
                    'sap_sync_date': fields.Datetime.now(),
                    'sap_sync_error': False,
                })

                _logger.info(f"PO {order.name} synced to SAP with document {sap_response.get('document_number')}")

            except Exception as e:
                order.write({
                    'sap_sync_status': 'error',
                    'sap_sync_error': str(e),
                })
                _logger.error(f"Failed to sync PO {order.name} to SAP: {str(e)}")

    def _prepare_sap_data(self):
        """Chuẩn bị data cho SAP"""
        sap_config = self.env['sap.integration.config'].search([('active', '=', True)], limit=1)

        header_data = {
            'DOCUMENT_TYPE': 'NB',  # Purchase Order
            'COMPANY_CODE': sap_config.company_code,
            'PURCHASING_ORG': sap_config.purchasing_org,
            'PURCHASING_GROUP': '001',  # Default group
            'DOC_DATE': self.date_order.strftime('%Y%m%d'),
            'VENDOR': self.partner_id.ref or self.partner_id.id,
            'CURRENCY': self.currency_id.name,
            'HEADER_TEXT': f"PO from Odoo: {self.name}",
        }

        # Add partner function
        partner_functions = {
            'PARTNER_FUNCTION': 'LF',  # Invoice from vendor
            'PARTNER_NO': self.partner_id.ref or str(self.partner_id.id),
        }

        # Prepare line items
        items = []
        for line in self.order_line:
            item_data = {
                'ITEM_CAT': 'D',  # Standard service
                'MATERIAL': line.product_id.default_code or line.product_id.id,
                'SHORT_TEXT': line.name[:40],  # SAP limit
                'QUANTITY': str(line.product_qty),
                'UOM': line.product_uom_id.name,
                'NET_PRICE': str(line.price_unit),
                'PLANT': self._get_sap_plant(),
                'STGE_LOC': '0001',  # Default storage location
                'ITEM_TEXT': f"Product: {line.product_id.name}",
            }

            # Add tax data
            if line.taxes_id:
                tax_code = self._get_sap_tax_code(line.taxes_id[0])
                if tax_code:
                    item_data['TAX_CODE'] = tax_code

            # Add account assignment (if needed)
            if line.account_analytic_id:
                item_data.update({
                    'ACCTASSCAT': 'K',  # Cost center
                    'COST_CENTER': self._get_sap_cost_center(line.account_analytic_id),
                })

            items.append(item_data)

        return {
            'header': header_data,
            'partner_functions': [partner_functions],
            'items': items,
        }

    def _send_to_sap(self, sap_config, sap_data):
        """Gửi data đến SAP thông qua BAPI"""
        # This is a simplified example - real implementation would use
        # appropriate SAP library (pyrfc, sapnwrfc, etc.)

        try:
            # Example using pyrfc (assuming it's installed)
            from pyrfc import Connection

            conn = Connection(
                ashost=sap_config.sap_host,
                sysnr=sap_config.sap_client,
                client=sap_config.sap_client,
                user=sap_config.username,
                passwd=sap_config.password
            )

            # Call BAPI_PO_CREATE1
            result = conn.call(
                'BAPI_PO_CREATE1',
                POHEADER=sap_data['header'],
                POHEADERX={},  # Update structure (empty for create)
                POITEM=[{'PO_ITEM': str(i+1), **item} for i, item in enumerate(sap_data['items'])],
                POITEMX=[{'PO_ITEM': str(i+1), 'PO_ITEMX': 'X'} for i in range(len(sap_data['items']))],
                POSCHEDULE=[],  # Delivery schedule
                POSCHEDULEX=[],
                POADDR=[sap_data['partner_functions']],
                RETURN=[]
            )

            if result['RETURN']:
                for ret in result['RETURN']:
                    if ret['TYPE'] == 'E':  # Error
                        raise Exception(f"SAP Error: {ret['MESSAGE']}")

            # Get PO number
            po_number = result.get('PURCHASEORDER')
            if not po_number:
                raise Exception("SAP did not return PO number")

            return {
                'document_number': po_number,
                'status': 'success'
            }

        except ImportError:
            # Fallback to HTTP-based SAP integration
            return self._send_to_sap_http(sap_config, sap_data)
        except Exception as e:
            _logger.exception("SAP BAPI call failed")
            raise

    def _send_to_sap_http(self, sap_config, sap_data):
        """Fallback HTTP-based SAP integration"""
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {self._get_sap_token(sap_config)}"
        }

        response = requests.post(
            f"https://{sap_config.sap_host}:{sap_config.sap_port}/sap/opu/odata/sap/ZPURCHASE_ORDER_SRV/PurchaseOrderSet",
            json=sap_data,
            headers=headers,
            timeout=30
        )

        if response.status_code == 201:
            result = response.json()
            return {
                'document_number': result.get('DocumentNumber'),
                'status': 'success'
            }
        else:
            raise Exception(f"SAP HTTP Error: {response.status_code} - {response.text}")

    def _get_sap_plant(self):
        """Lấy SAP plant code"""
        # Logic để map Odoo location to SAP plant
        if self.picking_type_id and self.picking_type_id.warehouse_id:
            return self.picking_type_id.warehouse_id.code or '1000'
        return '1000'  # Default plant

    def _get_sap_tax_code(self, tax):
        """Map Odoo tax to SAP tax code"""
        tax_mapping = {
            'vat_10': 'V1',
            'vat_0': 'V0',
            'service_tax': 'S1',
        }
        return tax_mapping.get(tax.description, 'V0')

    def _get_sap_cost_center(self, analytic_account):
        """Lấy SAP cost center từ analytic account"""
        return analytic_account.code or analytic_account.name[:10]

    def _get_sap_token(self, sap_config):
        """Lấy SAP OAuth token"""
        # Implement OAuth2 flow for SAP
        cache_key = f"sap_token_{sap_config.id}"
        cached_token = self.env['ir.config_parameter'].sudo().get_param(cache_key)

        if cached_token:
            return cached_token

        # Get new token
        token_response = requests.post(
            f"https://{sap_config.sap_host}/oauth/token",
            data={
                'grant_type': 'client_credentials',
                'client_id': sap_config.username,
                'client_secret': sap_config.password,
            }
        )

        if token_response.status_code == 200:
            token_data = token_response.json()
            token = token_data.get('access_token')

            # Cache token
            self.env['ir.config_parameter'].sudo().set_param(cache_key, token)

            return token
        else:
            raise Exception("Failed to get SAP token")

    def button_approve(self, force=False):
        """Override để auto-sync đến SAP sau khi approve"""
        res = super().button_approve(force=force)

        # Auto-sync to SAP if configured
        for order in self:
            if order.company_id.auto_sync_sap:
                order.action_sync_to_sap()

        return res

    def action_view_sap_document(self):
        """Mở SAP document trong web GUI"""
        if not self.sap_document_number:
            raise UserError("No SAP document found!")

        sap_config = self.env['sap.integration.config'].search([('active', '=', True)], limit=1)
        if not sap_config:
            raise UserError("SAP configuration not found!")

        sap_url = f"https://{sap_config.sap_host}:44300/sap/bc/gui/sap/its/webgui?~transaction=ME23N&PO_NUMBER={self.sap_document_number}"

        return {
            'type': 'ir.actions.act_url',
            'url': sap_url,
            'target': 'new',
        }

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    sap_item_number = fields.Integer('SAP Item Number')
    sap_material_code = fields.Char('SAP Material Code', related='product_id.default_code')

class Company(models.Model):
    _inherit = 'res.company'

    auto_sync_sap = fields.Boolean('Auto Sync to SAP', default=False)
    sap_integration_active = fields.Boolean('SAP Integration Active', default=False)
```

## 📊 Custom Reports

### 1. Advanced Purchase Analytics

#### **Purchase Performance Dashboard**

```python
# File: purchase_analytics/models/purchase_analytics.py
from odoo import models, fields, api
from datetime import datetime, timedelta

class PurchaseAnalytics(models.Model):
    _name = 'purchase.analytics'
    _description = 'Purchase Analytics Dashboard'
    _auto = False

    # Grouping fields
    date_order = fields.Date('Order Date', readonly=True)
    month = fields.Char('Month', readonly=True)
    quarter = fields.Char('Quarter', readonly=True)
    year = fields.Char('Year', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Vendor', readonly=True)
    category_id = fields.Many2one('product.category', 'Product Category', readonly=True)
    user_id = fields.Many2one('res.users', 'Purchaser', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)

    # Metrics
    order_count = fields.Integer('Order Count', readonly=True)
    total_amount = fields.Float('Total Amount', readonly=True)
    avg_order_amount = fields.Float('Average Order Amount', readonly=True)

    # Performance metrics
    on_time_delivery_rate = fields.Float('On-Time Delivery %', readonly=True)
    price_variance = fields.Float('Price Variance %', readonly=True)
    quality_score = fields.Float('Quality Score', readonly=True)

    # Budget metrics
    budget_consumed = fields.Float('Budget Consumed', readonly=True)
    budget_remaining = fields.Float('Budget Remaining', readonly=True)

    def init(self):
        """Create view for analytics"""
        tools.drop_view_if_exists(self.env.cr, 'purchase_analytics')

        self.env.cr.execute("""
            CREATE OR REPLACE VIEW purchase_analytics AS
            SELECT
                ROW_NUMBER() OVER () AS id,
                po.date_order::date AS date_order,
                TO_CHAR(po.date_order, 'YYYY-MM') AS month,
                'Q' || TO_CHAR(po.date_order, 'Q') || '-' || TO_CHAR(po.date_order, 'YYYY') AS quarter,
                TO_CHAR(po.date_order, 'YYYY') AS year,
                po.partner_id,
                pc.id AS category_id,
                po.user_id,
                po.company_id,

                -- Order metrics
                COUNT(*) AS order_count,
                SUM(po.amount_total) AS total_amount,
                AVG(po.amount_total) AS avg_order_amount,

                -- Performance metrics (computed via subqueries)
                COALESCE(perf.on_time_rate, 0) AS on_time_delivery_rate,
                COALESCE(perf.price_variance, 0) AS price_variance,
                COALESCE(perf.quality_score, 0) AS quality_score,

                -- Budget metrics
                COALESCE(budget.consumed, 0) AS budget_consumed,
                COALESCE(budget.remaining, 0) AS budget_remaining

            FROM purchase_order po
            LEFT JOIN res_partner rp ON po.partner_id = rp.id
            LEFT JOIN purchase_order_line pol ON po.id = pol.order_id
            LEFT JOIN product_product pp ON pol.product_id = pp.id
            LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
            LEFT JOIN product_category pc ON pt.categ_id = pc.id

            -- Performance metrics subquery
            LEFT JOIN (
                SELECT
                    po.id,
                    (COUNT(CASE WHEN sp.date_done <= po.date_planned THEN 1 END) * 100.0 /
                     COUNT(sp.id)) AS on_time_rate,
                    AVG(CASE WHEN pp.standard_price > 0
                         THEN ((pol.price_unit - pp.standard_price) / pp.standard_price * 100)
                         ELSE 0 END) AS price_variance,
                    AVG(COALESCE(vr.quality_rating, 3.0)) AS quality_score
                FROM purchase_order po
                LEFT JOIN purchase_order_line pol ON po.id = pol.order_id
                LEFT JOIN product_product pp ON pol.product_id = pp.id
                LEFT JOIN stock_picking sp ON sp.purchase_id = po.id
                LEFT JOIN res_partner vr ON po.partner_id = vr.id
                WHERE po.state IN ('purchase', 'done')
                GROUP BY po.id
            ) perf ON po.id = perf.id

            -- Budget metrics subquery
            LEFT JOIN (
                SELECT
                    po.id,
                    SUM(po.amount_total) AS consumed,
                    (SELECT COALESCE(SUM(planned_amount), 0)
                     FROM crossovered_budget_lines bl
                     JOIN crossovered_budget cb ON bl.crossovered_budget_id = cb.id
                     WHERE cb.state = 'done' AND cb.date_from <= po.date_order
                     AND cb.date_to >= po.date_order) - SUM(po.amount_total) AS remaining
                FROM purchase_order po
                WHERE po.state IN ('purchase', 'done')
                GROUP BY po.id
            ) budget ON po.id = budget.id

            WHERE po.state IN ('purchase', 'done')
            GROUP BY
                po.date_order::date,
                TO_CHAR(po.date_order, 'YYYY-MM'),
                'Q' || TO_CHAR(po.date_order, 'Q') || '-' || TO_CHAR(po.date_order, 'YYYY'),
                TO_CHAR(po.date_order, 'YYYY'),
                po.partner_id,
                pc.id,
                po.user_id,
                po.company_id,
                perf.on_time_rate,
                perf.price_variance,
                perf.quality_score,
                budget.consumed,
                budget.remaining
        """)

class PurchasePerformanceReport(models.TransientModel):
    _name = 'purchase.performance.report'
    _description = 'Purchase Performance Report'

    date_from = fields.Date('Date From', required=True, default=lambda self: fields.Date.today() - timedelta(days=30))
    date_to = fields.Date('Date To', required=True, default=lambda self: fields.Date.today())
    vendor_ids = fields.Many2many('res.partner', 'report_vendor_rel', 'report_id', 'vendor_id', 'Vendors')
    category_ids = fields.Many2many('product.category', 'report_category_rel', 'report_id', 'category_id', 'Categories')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    report_data = fields.Text('Report Data', compute='_compute_report_data')

    @api.depends('date_from', 'date_to', 'vendor_ids', 'category_ids', 'company_id')
    def _compute_report_data(self):
        """Tính toán report data"""
        for record in self:
            # Get filtered analytics data
            domain = [
                ('date_order', '>=', record.date_from),
                ('date_order', '<=', record.date_to),
                ('company_id', '=', record.company_id.id),
            ]

            if record.vendor_ids:
                domain.append(('partner_id', 'in', record.vendor_ids.ids))

            if record.category_ids:
                domain.append(('category_id', 'in', record.category_ids.ids))

            analytics = self.env['purchase.analytics'].search(domain)

            # Generate report data
            report_data = {
                'summary': {
                    'total_orders': len(analytics),
                    'total_amount': sum(analytics.mapped('total_amount')),
                    'avg_order_amount': sum(analytics.mapped('total_amount')) / len(analytics) if analytics else 0,
                    'avg_on_time_delivery': sum(analytics.mapped('on_time_delivery_rate')) / len(analytics) if analytics else 0,
                    'avg_quality_score': sum(analytics.mapped('quality_score')) / len(analytics) if analytics else 0,
                },
                'by_vendor': {},
                'by_category': {},
                'monthly_trends': {},
                'budget_analysis': {}
            }

            # Group by vendor
            vendor_data = {}
            for record in analytics:
                vendor_name = record.partner_id.name or 'Unknown'
                if vendor_name not in vendor_data:
                    vendor_data[vendor_name] = {
                        'order_count': 0,
                        'total_amount': 0,
                        'on_time_rate': 0,
                        'quality_score': 0,
                    }

                vendor_data[vendor_name]['order_count'] += record.order_count
                vendor_data[vendor_name]['total_amount'] += record.total_amount
                vendor_data[vendor_name]['on_time_rate'] += record.on_time_delivery_rate
                vendor_data[vendor_name]['quality_score'] += record.quality_score

            # Calculate averages for vendors
            for vendor in vendor_data:
                vendor_data[vendor]['on_time_rate'] = vendor_data[vendor]['on_time_rate'] / vendor_data[vendor]['order_count']
                vendor_data[vendor]['quality_score'] = vendor_data[vendor]['quality_score'] / vendor_data[vendor]['order_count']

            report_data['by_vendor'] = vendor_data

            # Group by category
            category_data = {}
            for record in analytics:
                category_name = record.category_id.name or 'Uncategorized'
                if category_name not in category_data:
                    category_data[category_name] = {
                        'order_count': 0,
                        'total_amount': 0,
                    }

                category_data[category_name]['order_count'] += record.order_count
                category_data[category_name]['total_amount'] += record.total_amount

            report_data['by_category'] = category_data

            # Monthly trends
            monthly_data = {}
            for record in analytics:
                month = record.month
                if month not in monthly_data:
                    monthly_data[month] = {
                        'order_count': 0,
                        'total_amount': 0,
                    }

                monthly_data[month]['order_count'] += record.order_count
                monthly_data[month]['total_amount'] += record.total_amount

            report_data['monthly_trends'] = monthly_data

            record.report_data = json.dumps(report_data, indent=2)

    def action_generate_report(self):
        """Generate detailed report"""
        self._compute_report_data()

        # Create Excel report
        if self.report_data:
            return self._export_excel_report()

        return True

    def _export_excel_report(self):
        """Export report to Excel"""
        import xlsxwriter
        import io
        import base64

        report_data = json.loads(self.report_data)

        # Create Excel file
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)

        # Summary sheet
        summary_sheet = workbook.add_worksheet('Summary')
        summary_sheet.write(0, 0, 'Purchase Performance Report')
        summary_sheet.write(2, 0, 'Period:')
        summary_sheet.write(2, 1, f"{self.date_from} to {self.date_to}")

        row = 4
        for key, value in report_data['summary'].items():
            summary_sheet.write(row, 0, key.replace('_', ' ').title())
            summary_sheet.write(row, 1, value)
            row += 1

        # Vendor sheet
        vendor_sheet = workbook.add_worksheet('By Vendor')
        vendor_sheet.write_row(0, 0, ['Vendor', 'Order Count', 'Total Amount', 'On-Time Rate', 'Quality Score'])

        row = 1
        for vendor, data in report_data['by_vendor'].items():
            vendor_sheet.write_row(row, 0, [vendor, data['order_count'], data['total_amount'],
                                       data['on_time_rate'], data['quality_score']])
            row += 1

        workbook.close()
        output.seek(0)

        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': f'purchase_performance_report_{fields.Date.today()}.xlsx',
            'datas': base64.b64encode(output.read()),
            'res_model': self._name,
            'res_id': self.id,
            'type': 'binary',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
```

## 🌐 API Examples

### 1. REST API Endpoints

#### **External Purchase Order API**

```python
# File: api_purchase/controllers/purchase_api.py
import json
from odoo import http
from odoo.http import request, content_disposition
from odoo.exceptions import AccessError, UserError

class PurchaseAPI(http.Controller):

    @http.route('/api/purchase/orders', type='json', auth='user', methods=['GET'])
    def get_purchase_orders(self, **kwargs):
        """Get list of purchase orders with filtering"""
        try:
            # Parse query parameters
            domain = []

            if kwargs.get('state'):
                domain.append(('state', '=', kwargs['state']))

            if kwargs.get('vendor_id'):
                domain.append(('partner_id', '=', int(kwargs['vendor_id'])))

            if kwargs.get('date_from'):
                domain.append(('date_order', '>=', kwargs['date_from']))

            if kwargs.get('date_to'):
                domain.append(('date_order', '<=', kwargs['date_to']))

            # Search orders
            orders = request.env['purchase.order'].search(domain)

            # Prepare response data
            order_data = []
            for order in orders:
                order_data.append({
                    'id': order.id,
                    'name': order.name,
                    'state': order.state,
                    'partner_id': order.partner_id.id,
                    'partner_name': order.partner_id.name,
                    'amount_total': order.amount_total,
                    'currency_id': order.currency_id.id,
                    'date_order': order.date_order.isoformat() if order.date_order else None,
                    'date_planned': order.date_planned.isoformat() if order.date_planned else None,
                    'invoice_status': order.invoice_status,
                    'line_count': len(order.order_line),
                })

            return {
                'status': 'success',
                'data': order_data,
                'total': len(order_data),
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
            }

    @http.route('/api/purchase/orders/<int:order_id>', type='json', auth='user', methods=['GET'])
    def get_purchase_order(self, order_id, **kwargs):
        """Get detailed purchase order information"""
        try:
            order = request.env['purchase.order'].browse(order_id)
            if not order.exists():
                raise http.NotFound(f"Purchase Order {order_id} not found")

            # Prepare detailed response
            order_data = {
                'id': order.id,
                'name': order.name,
                'state': order.state,
                'partner_id': order.partner_id.id,
                'partner_name': order.partner_id.name,
                'partner_ref': order.partner_ref,
                'origin': order.origin,
                'date_order': order.date_order.isoformat() if order.date_order else None,
                'date_approve': order.date_approve.isoformat() if order.date_approve else None,
                'date_planned': order.date_planned.isoformat() if order.date_planned else None,
                'amount_total': order.amount_total,
                'amount_untaxed': order.amount_untaxed,
                'amount_tax': order.amount_tax,
                'currency_id': order.currency_id.id,
                'currency_name': order.currency_id.name,
                'invoice_status': order.invoice_status,
                'payment_status': getattr(order, 'payment_status', 'unpaid'),
                'notes': order.notes,
                'terms': order.payment_term_id.name if order.payment_term_id else None,
                'lines': [],
                'picking_ids': [],
                'invoice_ids': [],
            }

            # Add line items
            for line in order.order_line:
                line_data = {
                    'id': line.id,
                    'product_id': line.product_id.id,
                    'product_name': line.product_id.name,
                    'product_code': line.product_id.default_code,
                    'description': line.name,
                    'quantity': line.product_qty,
                    'uom_id': line.product_uom.id,
                    'uom_name': line.product_uom.name,
                    'price_unit': line.price_unit,
                    'discount': line.discount,
                    'price_subtotal': line.price_subtotal,
                    'price_total': line.price_total,
                    'qty_received': line.qty_received,
                    'qty_invoiced': line.qty_invoiced,
                    'tax_ids': [tax.id for tax in line.taxes_id],
                }
                order_data['lines'].append(line_data)

            # Add pickings
            for picking in order.picking_ids:
                picking_data = {
                    'id': picking.id,
                    'name': picking.name,
                    'state': picking.state,
                    'scheduled_date': picking.scheduled_date.isoformat() if picking.scheduled_date else None,
                    'date_done': picking.date_done.isoformat() if picking.date_done else None,
                    'origin': picking.origin,
                }
                order_data['picking_ids'].append(picking_data)

            # Add invoices
            for invoice in order.invoice_ids:
                invoice_data = {
                    'id': invoice.id,
                    'name': invoice.name,
                    'state': invoice.state,
                    'move_type': invoice.move_type,
                    'amount_total': invoice.amount_total,
                    'amount_residual': invoice.amount_residual,
                    'invoice_date': invoice.invoice_date.isoformat() if invoice.invoice_date else None,
                    'payment_state': invoice.payment_state,
                }
                order_data['invoice_ids'].append(invoice_data)

            return {
                'status': 'success',
                'data': order_data,
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
            }

    @http.route('/api/purchase/orders', type='json', auth='user', methods=['POST'])
    def create_purchase_order(self, **kwargs):
        """Create new purchase order via API"""
        try:
            data = json.loads(request.httprequest.data)

            # Validate required fields
            if not data.get('partner_id'):
                raise UserError("Vendor (partner_id) is required")

            if not data.get('lines'):
                raise UserError("At least one line item is required")

            # Create PO
            po_vals = {
                'partner_id': data['partner_id'],
                'origin': data.get('origin'),
                'date_order': data.get('date_order'),
                'notes': data.get('notes'),
                'order_line': [],
            }

            # Add line items
            for line_data in data['lines']:
                if not line_data.get('product_id') or not line_data.get('quantity'):
                    continue

                line_vals = {
                    'product_id': line_data['product_id'],
                    'product_qty': line_data['quantity'],
                    'price_unit': line_data.get('price_unit', 0),
                    'discount': line_data.get('discount', 0),
                    'name': line_data.get('description'),
                }

                if line_data.get('uom_id'):
                    line_vals['product_uom'] = line_data['uom_id']

                po_vals['order_line'].append((0, 0, line_vals))

            # Create purchase order
            po = request.env['purchase.order'].create(po_vals)

            return {
                'status': 'success',
                'data': {
                    'id': po.id,
                    'name': po.name,
                    'state': po.state,
                },
                'message': f"Purchase Order {po.name} created successfully",
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
            }

    @http.route('/api/purchase/orders/<int:order_id>/confirm', type='json', auth='user', methods=['POST'])
    def confirm_purchase_order(self, order_id, **kwargs):
        """Confirm purchase order via API"""
        try:
            order = request.env['purchase.order'].browse(order_id)
            if not order.exists():
                raise http.NotFound(f"Purchase Order {order_id} not found")

            if order.state != 'draft':
                raise UserError(f"Cannot confirm order in state {order.state}")

            # Confirm order
            order.button_confirm()

            return {
                'status': 'success',
                'data': {
                    'id': order.id,
                    'name': order.name,
                    'state': order.state,
                },
                'message': f"Purchase Order {order.name} confirmed successfully",
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
            }

    @http.route('/api/purchase/orders/<int:order_id>/approve', type='json', auth='user', methods=['POST'])
    def approve_purchase_order(self, order_id, **kwargs):
        """Approve purchase order via API"""
        try:
            order = request.env['purchase.order'].browse(order_id)
            if not order.exists():
                raise http.NotFound(f"Purchase Order {order_id} not found")

            if order.state != 'to approve':
                raise UserError(f"Order is not in 'to approve' state")

            # Get force parameter from request data
            request_data = json.loads(request.httprequest.data) if request.httprequest.data else {}
            force = request_data.get('force', False)

            # Approve order
            order.button_approve(force=force)

            return {
                'status': 'success',
                'data': {
                    'id': order.id,
                    'name': order.name,
                    'state': order.state,
                },
                'message': f"Purchase Order {order.name} approved successfully",
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
            }

    @http.route('/api/purchase/orders/<int:order_id>/cancel', type='json', auth='user', methods=['POST'])
    def cancel_purchase_order(self, order_id, **kwargs):
        """Cancel purchase order via API"""
        try:
            order = request.env['purchase.order'].browse(order_id)
            if not order.exists():
                raise http.NotFound(f"Purchase Order {order_id} not found")

            # Check if order can be cancelled
            if order.state in ['done', 'cancel']:
                raise UserError(f"Cannot cancel order in state {order.state}")

            # Cancel order
            order.button_cancel()

            return {
                'status': 'success',
                'data': {
                    'id': order.id,
                    'name': order.name,
                    'state': order.state,
                },
                'message': f"Purchase Order {order.name} cancelled successfully",
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
            }

    @http.route('/api/purchase/vendors', type='json', auth='user', methods=['GET'])
    def get_vendors(self, **kwargs):
        """Get list of vendors with purchase info"""
        try:
            domain = [
                ('supplier_rank', '>', 0),
                ('is_company', '=', True),
            ]

            if kwargs.get('search'):
                domain.append(('name', 'ilike', f"%{kwargs['search']}%"))

            vendors = request.env['res.partner'].search(domain)

            vendor_data = []
            for vendor in vendors:
                # Get purchase statistics
                pos = request.env['purchase.order'].search([
                    ('partner_id', '=', vendor.id),
                    ('state', 'in', ['purchase', 'done']),
                ])

                total_amount = sum(pos.mapped('amount_total'))
                last_order_date = max(pos.mapped('date_order')) if pos else None

                vendor_data.append({
                    'id': vendor.id,
                    'name': vendor.name,
                    'ref': vendor.ref,
                    'email': vendor.email,
                    'phone': vendor.phone,
                    'supplier_rank': vendor.supplier_rank,
                    'total_purchase_amount': total_amount,
                    'order_count': len(pos),
                    'last_order_date': last_order_date.isoformat() if last_order_date else None,
                    'active': vendor.active,
                })

            return {
                'status': 'success',
                'data': vendor_data,
                'total': len(vendor_data),
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
            }

class PurchaseAPIAuth(http.Controller):

    @http.route('/api/purchase/auth', type='json', auth='none', methods=['POST'])
    def authenticate(self, **kwargs):
        """API authentication endpoint"""
        try:
            data = json.loads(request.httprequest.data)

            if not data.get('login') or not data.get('password'):
                raise UserError("Login and password are required")

            # Authenticate user
            uid = request.env['res.users'].authenticate(
                data['login'],
                data['password'],
                {}
            )

            if not uid:
                raise UserError("Invalid credentials")

            # Generate API token
            api_token = request.env['api.token'].generate_token(uid)

            return {
                'status': 'success',
                'data': {
                    'user_id': uid,
                    'api_token': api_token,
                },
                'message': "Authentication successful",
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
            }

# API Token model
class APIToken(models.Model):
    _name = 'api.token'
    _description = 'API Token Management'

    name = fields.Char('Token Name')
    token = fields.Char('Token', readonly=True)
    user_id = fields.Many2one('res.users', 'User', required=True)
    expires_at = fields.Datetime('Expires At')
    active = fields.Boolean('Active', default=True)

    @api.model
    def generate_token(self, user_id):
        """Generate new API token for user"""
        import secrets
        import string

        # Generate random token
        alphabet = string.ascii_letters + string.digits
        token = ''.join(secrets.choice(alphabet) for _ in range(32))

        # Clean up old tokens for this user
        self.search([
            ('user_id', '=', user_id),
            ('active', '=', True)
        ]).write({'active': False})

        # Create new token
        self.create({
            'name': f"Token for user {user_id}",
            'token': token,
            'user_id': user_id,
            'expires_at': fields.Datetime.now() + timedelta(hours=24),
        })

        return token

    @api.model
    def validate_token(self, token):
        """Validate API token and return user_id"""
        token_record = self.search([
            ('token', '=', token),
            ('active', '=', True),
            ('expires_at', '>', fields.Datetime.now()),
        ], limit=1)

        if token_record:
            return token_record.user_id.id

        return False
```

---

**Next Steps**: Đọc [06_best_practices.md](06_best_practices.md) để xem development guidelines và testing strategies.