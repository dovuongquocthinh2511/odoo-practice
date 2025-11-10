# 📚 Best Practices & Testing Strategies - Odoo Purchase Module

## 🎯 Giới Thiệu

Hướng dẫn toàn diện về best practices, testing strategies, và deployment considerations cho việc phát triển và customization module Purchase trong Odoo 18.

## 🏗️ Development Best Practices

### 1. Code Organization & Structure

#### ✅ Directory Structure Standards
```
custom_purchase/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── purchase_order.py          # Extensions to purchase.order
│   ├── purchase_order_line.py     # Extensions to purchase.order.line
│   └── custom_models.py          # New custom models
├── views/
│   ├── purchase_views.xml        # Form/List/Search views
│   ├── purchase_reports.xml      # Report views
│   └── custom_views.xml          # Custom interface views
├── security/
│   ├── ir.model.access.csv       # Access rights
│   └── purchase_security.xml     # Record rules
├── data/
│   └── purchase_data.xml         # Default data
├── demo/
│   └── purchase_demo.xml         # Demo data
├── static/
│   ├── src/
│   │   ├── js/
│   │   ├── css/
│   │   └── xml/
│   └── description/
├── tests/
│   ├── __init__.py
│   ├── test_purchase_order.py
│   ├── test_workflows.py
│   └── test_integration.py
├── wizards/
│   ├── __init__.py
│   └── purchase_wizard.py
├── reports/
│   ├── __init__.py
│   └── purchase_reports.py
└── controllers/
    ├── __init__.py
    └── purchase_controller.py
```

#### ✅ Model Extension Patterns
```python
# models/purchase_order.py
from odoo import models, fields, api, _

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # Custom fields follow naming conventions
    x_approval_required = fields.Boolean(
        string='Yêu cầu duyệt',
        default=False,
        help="Đánh dấu nếu đơn hàng cần duyệt bổ sung"
    )

    x_approver_id = fields.Many2one(
        'res.users',
        string='Người duyệt',
        tracking=True
    )

    x_priority_level = fields.Selection([
        ('low', 'Thấp'),
        ('medium', 'Trung bình'),
        ('high', 'Cao'),
        ('urgent', 'Khẩn cấp')
    ], string='Mức độ ưu tiên', default='medium')

    # Computed fields with proper dependencies
    x_total_weight = fields.Float(
        string='Tổng trọng lượng',
        compute='_compute_total_weight',
        store=True,
        help="Tổng trọng lượng của tất cả các sản phẩm"
    )

    @api.depends('order_line.product_id', 'order_line.product_qty')
    def _compute_total_weight(self):
        for order in self:
            total_weight = 0.0
            for line in order.order_line:
                if line.product_id and line.product_id.weight:
                    total_weight += line.product_id.weight * line.product_qty
            order.x_total_weight = total_weight
```

#### ✅ Method Override Best Practices
```python
# Override existing methods with super() call
def button_confirm(self):
    """Override confirm with additional validation"""
    # Pre-validation logic
    for order in self:
        if order.x_approval_required and not order.x_approver_id:
            raise UserError(_("Đơn hàng cần duyệt trước khi xác nhận!"))

        # Business logic validation
        if order.amount_total > 10000000 and not order.user_id.has_group('purchase.group_purchase_manager'):
            raise UserError(_("Đơn hàng > 10M cần quyền Manager!"))

    # Call parent method
    result = super(PurchaseOrder, self).button_confirm()

    # Post-processing
    for order in self:
        order._send_approval_notification()

    return result

@api.model
def create(self, vals):
    """Override create with additional logic"""
    # Auto-set priority based on amount
    if vals.get('amount_total', 0) > 5000000:
        vals['x_priority_level'] = 'high'

    # Call parent create
    purchase = super(PurchaseOrder, self).create(vals)

    # Post-create actions
    purchase._auto_assign_category()

    return purchase
```

### 2. Performance Optimization

#### ✅ Database Query Optimization
```python
# ❌ BAD - N+1 queries
def get_vendor_performance_bad(self):
    vendors = self.env['res.partner'].search([('supplier_rank', '>', 0)])
    performance_data = []

    for vendor in vendors:  # N+1 query problem
        orders = self.env['purchase.order'].search([
            ('partner_id', '=', vendor.id)
        ])

        total_amount = sum(orders.mapped('amount_total'))
        performance_data.append({
            'vendor': vendor.name,
            'total_orders': len(orders),
            'total_amount': total_amount
        })

    return performance_data

# ✅ GOOD - Optimized with read_group
def get_vendor_performance_optimized(self):
    performance_data = self.env['purchase.order'].read_group(
        domain=[('state', '=', 'purchase')],
        fields=['partner_id', 'amount_total:sum', 'id:count'],
        groupby=['partner_id'],
        orderby='amount_total_sum desc'
    )

    result = []
    for data in performance_data:
        if data['partner_id']:
            result.append({
                'vendor': data['partner_id'][1],  # partner display name
                'total_orders': data['partner_id_count'],
                'total_amount': data['amount_total_sum']
            })

    return result

# ✅ EVEN BETTER - With prefetch and batch operations
def get_vendor_performance_advanced(self):
    # Get all relevant orders in one query
    orders = self.env['purchase.order'].search([
        ('state', '=', 'purchase')
    ]).with_context(prefetch_fields=False)

    # Prefetch related partners to avoid additional queries
    partners = orders.mapped('partner_id')

    # Group data in Python (faster than read_group for complex logic)
    vendor_data = {}
    for order in orders:
        vendor_id = order.partner_id.id
        if vendor_id not in vendor_data:
            vendor_data[vendor_id] = {
                'vendor': order.partner_id.name,
                'total_orders': 0,
                'total_amount': 0.0,
                'orders': []
            }

        vendor_data[vendor_id]['total_orders'] += 1
        vendor_data[vendor_id]['total_amount'] += order.amount_total
        vendor_data[vendor_id]['orders'].append(order)

    return list(vendor_data.values())
```

#### ✅ Computed Fields Optimization
```python
class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # ❌ BAD - Computed without store (recalculates every access)
    x_expensive_calculation = fields.Float(
        compute='_compute_expensive',
        string='Expensive Calculation'
    )

    # ✅ GOOD - Stored computed field
    x_total_weight = fields.Float(
        compute='_compute_total_weight',
        store=True,
        string='Tổng trọng lượng'
    )

    # ✅ BETTER - Multi-level compute with proper dependencies
    x_total_delivery_cost = fields.Float(
        compute='_compute_delivery_cost',
        store=True,
        compute_sudo=True,  # Compute with admin rights for performance
        string='Tổng chi phí vận chuyển'
    )

    @api.depends('order_line.product_id', 'order_line.product_qty', 'order_line.price_unit')
    def _compute_total_weight(self):
        """Optimized weight calculation"""
        # Batch fetch all products
        product_ids = self.order_line.product_id.ids
        products = self.env['product.product'].browse(product_ids)

        # Create product weight mapping
        weight_map = {p.id: p.weight or 0.0 for p in products}

        for order in self:
            total_weight = 0.0
            for line in order.order_line:
                weight = weight_map.get(line.product_id.id, 0.0)
                total_weight += weight * line.product_qty
            order.x_total_weight = total_weight
```

#### ✅ Batch Operations
```python
# ❌ BAD - Individual operations
def update_prices_bad(self):
    for line in self.order_line:
        if line.product_id:
            price = line.product_id._get_purchase_price(line.partner_id)
            line.write({'price_unit': price})  # N write operations

# ✅ GOOD - Batch operations
def update_prices_good(self):
    """Batch update prices for better performance"""
    # Collect data first
    lines_to_update = []
    for line in self.order_line:
        if line.product_id:
            price = line.product_id._get_purchase_price(line.partner_id)
            if line.price_unit != price:
                lines_to_update.append((line.id, price))

    # Batch update
    if lines_to_update:
        for line_id, price in lines_to_update:
            self.env['purchase.order.line'].browse(line_id).price_unit = price

        # Single write call to trigger recomputations
        self.order_line.write({'price_unit': False})  # Reset first
        for line_id, price in lines_to_update:
            self.env['purchase.order.line'].browse(line_id).write({'price_unit': price})
```

### 3. Security Best Practices

#### ✅ Access Rights Configuration
```csv
# security/ir.model.access.csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_purchase_order_user,purchase.order.user,model_purchase_order,base.group_user,1,1,1,0
access_purchase_order_manager,purchase.order.manager,model_purchase_order,purchase.group_purchase_manager,1,1,1,1
access_purchase_order_extension_user,purchase.order.extension.user,model_purchase_order,purchase.group_purchase_user,1,1,0,0
```

```xml
<!-- security/purchase_security.xml -->
<odoo>
    <data noupdate="1">
        <!-- Record rules for data isolation -->
        <record id="purchase_order_user_rule" model="ir.rule">
            <field name="name">Purchase Order User Access</field>
            <field name="model_id" ref="model_purchase_order"/>
            <field name="domain_force">[
                ('create_uid', '=', user.id),
                '|', ('state', 'in', ['sent', 'to_approve', 'purchase', 'done']),
                ('user_id', '=', user.id)
            ]</field>
            <field name="groups" eval="[(4, ref('base.group_user'))]"/>
            <field name="perm_read" eval="True"/>
            <field name="perm_write" eval="True"/>
            <field name="perm_create" eval="True"/>
            <field name="perm_unlink" eval="False"/>
        </record>

        <!-- High value orders require special access -->
        <record id="high_value_order_rule" model="ir.rule">
            <field name="name">High Value Order Manager Only</field>
            <field name="model_id" ref="model_purchase_order"/>
            <field name="domain_force">[
                ('amount_total', '>', 10000000),
                ('state', 'in', ['to_approve', 'purchase'])
            ]</field>
            <field name="groups" eval="[(4, ref('purchase.group_purchase_manager'))]"/>
        </record>
    </data>
</odoo>
```

#### ✅ Field-Level Security
```python
class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # Sensitive fields with restricted access
    x_internal_notes = fields.Text(
        string='Ghi chú nội bộ',
        groups="purchase.group_purchase_manager"
    )

    x_cost_breakdown = fields.Text(
        string='Chi tiết chi phí',
        compute='_compute_cost_breakdown',
        store=True,
        groups="purchase.group_purchase_manager"
    )

    # Read-only fields based on state
    @api.depends('state')
    def _compute_readonly_fields(self):
        """Compute readonly fields based on state"""
        for order in self:
            if order.state in ['done', 'cancel']:
                order.readonly_fields = ['partner_id', 'order_line', 'date_order']
            elif order.state == 'purchase':
                order.readonly_fields = ['partner_id', 'date_order']
            else:
                order.readonly_fields = []
```

## 🧪 Testing Strategies

### 1. Unit Testing

#### ✅ Test Structure and Setup
```python
# tests/test_purchase_order.py
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

class TestPurchaseOrder(TransactionCase):

    def setUp(self):
        """Set up test data"""
        super(TestPurchaseOrder, self).setUp()

        # Create test data
        self.PurchaseOrder = self.env['purchase.order']
        self.PurchaseOrderLine = self.env['purchase.order.line']

        # Test vendor
        self.vendor = self.env['res.partner'].create({
            'name': 'Test Vendor',
            'supplier_rank': 1,
            'email': 'vendor@test.com',
        })

        # Test product
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'default_code': 'TEST001',
            'purchase_ok': True,
            'weight': 1.5,
            'standard_price': 100.0,
        })

        # Test user with purchase rights
        self.purchase_user = self.env['res.users'].create({
            'name': 'Purchase User',
            'login': 'purchase_user@test.com',
            'groups_id': [(6, 0, [self.env.ref('purchase.group_purchase_user').id])],
        })

        # Test manager
        self.purchase_manager = self.env['res.users'].create({
            'name': 'Purchase Manager',
            'login': 'manager@test.com',
            'groups_id': [(6, 0, [self.env.ref('purchase.group_purchase_manager').id])],
        })

    def test_create_purchase_order(self):
        """Test basic purchase order creation"""
        order = self.PurchaseOrder.create({
            'partner_id': self.vendor.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 10,
                'price_unit': 50.0,
            })]
        })

        self.assertEqual(order.state, 'draft')
        self.assertEqual(order.partner_id, self.vendor)
        self.assertEqual(len(order.order_line), 1)
        self.assertEqual(order.amount_total, 500.0)

    def test_approval_workflow(self):
        """Test multi-level approval workflow"""
        # Create order requiring approval
        order = self.PurchaseOrder.create({
            'partner_id': self.vendor.id,
            'x_approval_required': True,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 100,
                'price_unit': 150.0,
            })]
        })

        # Test approval requirement
        with self.assertRaises(UserError):
            order.with_user(self.purchase_user).button_confirm()

        # Test approval by manager
        order.with_user(self.purchase_manager).write({
            'x_approver_id': self.purchase_manager.id
        })

        # Now should confirm successfully
        order.with_user(self.purchase_manager).button_confirm()
        self.assertEqual(order.state, 'purchase')

    def test_price_validation(self):
        """Test price validation constraints"""
        # Create order with invalid price
        with self.assertRaises(ValidationError):
            order = self.PurchaseOrder.create({
                'partner_id': self.vendor.id,
                'order_line': [(0, 0, {
                    'product_id': self.product.id,
                    'product_qty': 10,
                    'price_unit': -50.0,  # Invalid negative price
                })]
            })

    def test_computed_fields(self):
        """Test computed field calculations"""
        order = self.PurchaseOrder.create({
            'partner_id': self.vendor.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 10,
                'price_unit': 50.0,
            })]
        })

        # Test weight calculation
        expected_weight = 10 * 1.5  # qty * product weight
        self.assertEqual(order.x_total_weight, expected_weight)
```

#### ✅ Integration Testing
```python
# tests/test_integration.py
from odoo.tests.common import TransactionCase
from odoo.tests import tagged

@tagged('-standard', 'purchase_integration')
class TestPurchaseIntegration(TransactionCase):

    def test_inventory_integration(self):
        """Test integration with inventory module"""
        # Install stock module if not available
        if not self.env['ir.module.module'].search([('name', '=', 'stock')]):
            self.skipTest("Stock module not available")

        # Create purchase order
        order = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 10,
                'price_unit': 50.0,
            })]
        })

        # Confirm order to create picking
        order.button_confirm()
        self.assertEqual(order.state, 'purchase')

        # Check if picking was created
        pickings = self.env['stock.picking'].search([
            ('origin', '=', order.name)
        ])
        self.assertTrue(len(pickings) > 0, "Picking should be created after PO confirmation")

    def test_accounting_integration(self):
        """Test integration with accounting module"""
        # Create and confirm purchase order
        order = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 10,
                'price_unit': 50.0,
            })]
        })
        order.button_confirm()

        # Create vendor bill
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.vendor.id,
            'purchase_id': order.id,
        })

        # Check if lines are created from PO
        self.assertTrue(len(bill.line_ids) > 0, "Bill lines should be created from PO")
```

### 2. Performance Testing

#### ✅ Load Testing
```python
# tests/test_performance.py
from odoo.tests.common import TransactionCase
import time

@tagged('-standard', 'performance')
class TestPurchasePerformance(TransactionCase):

    def test_bulk_order_creation(self):
        """Test performance of bulk order creation"""
        start_time = time.time()

        # Create 100 orders
        orders = []
        for i in range(100):
            order = self.env['purchase.order'].create({
                'partner_id': self.vendor.id,
                'order_line': [(0, 0, {
                    'product_id': self.product.id,
                    'product_qty': 10,
                    'price_unit': 50.0,
                })]
            })
            orders.append(order)

        end_time = time.time()
        creation_time = end_time - start_time

        # Should complete within reasonable time (adjust threshold as needed)
        self.assertLess(creation_time, 10.0,
                       f"Bulk creation took too long: {creation_time:.2f}s")

    def test_complex_query_performance(self):
        """Test performance of complex queries"""
        # Create test data
        orders = []
        for i in range(50):
            order = self.env['purchase.order'].create({
                'partner_id': self.vendor.id,
                'amount_total': 1000 * (i + 1),
                'state': 'purchase' if i % 2 == 0 else 'draft',
                'order_line': [(0, 0, {
                    'product_id': self.product.id,
                    'product_qty': 10,
                    'price_unit': 50.0,
                })]
            })
            orders.append(order)

        # Test vendor performance query
        start_time = time.time()
        performance_data = self.env['purchase.order'].get_vendor_performance_optimized()
        end_time = time.time()

        query_time = end_time - start_time
        self.assertLess(query_time, 2.0,
                       f"Performance query took too long: {query_time:.2f}s")

        # Verify results
        self.assertTrue(len(performance_data) > 0, "Should return performance data")
```

### 3. UI Testing with JavaScript

#### ✅ Frontend Testing
```javascript
// static/tests/purchase_order_tests.js
odoo.define('custom_purchase.purchase_tests', function (require) {
    "use strict";

    var FormView = require('web.FormView');
    var testUtils = require('web.test_utils');
    var createView = testUtils.createView;

    QUnit.module('Purchase Order Tests', {
        beforeEach: function () {
            this.data = {
                'purchase.order': {
                    fields: {
                        name: {string: "Reference", type: "char", readonly: true},
                        partner_id: {string: "Vendor", type: "many2one", relation: "res.partner"},
                        state: {string: "State", type: "selection", selection: [["draft","RFQ"],["purchase","PO"]]},
                        amount_total: {string: "Total", type: "float"},
                    },
                    records: [
                        {
                            id: 1,
                            name: "PO001",
                            partner_id: 1,
                            state: "draft",
                            amount_total: 1000.00,
                        }
                    ]
                },
                'res.partner': {
                    fields: {
                        name: {string: "Name", type: "char"},
                    },
                    records: [
                        {id: 1, name: "Test Vendor"},
                    ]
                }
            };
        }
    });

    QUnit.test('Purchase order form renders correctly', async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: 'purchase.order',
            data: this.data,
            arch: '<form><field name="name"/><field name="partner_id"/><field name="state"/></form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('.o_field_widget[name=name] input').val(), 'PO001');
        assert.strictEqual(form.$('.o_field_widget[name=partner_id] input').val(), 'Test Vendor');
        assert.strictEqual(form.$('.o_field_widget[name=state] select').val(), 'draft');

        form.destroy();
    });

    QUnit.test('Confirm button triggers workflow', async function (assert) {
        assert.expect(1);

        var form = await createView({
            View: FormView,
            model: 'purchase.order',
            data: this.data,
            arch: '<form>' +
                  '<header><button name="button_confirm" type="object" string="Confirm Order"/></header>' +
                  '<field name="state"/>' +
                  '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === 'button_confirm') {
                    assert.step('button_confirm');
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            }
        });

        form.$('.o_button_confirm').click();
        assert.verifySteps(['button_confirm']);

        form.destroy();
    });
});
```

## 🚀 Deployment Best Practices

### 1. Module Versioning

#### ✅ Semantic Versioning
```python
# __manifest__.py
{
    'name': 'Custom Purchase Management',
    'version': '18.0.2.1.0',  # Major.Odoo.Series.Feature.Fix

    # Version meaning:
    # 18 - Odoo version compatibility
    # 0 - Major feature version
    # 2 - Feature update version
    # 1 - Bug fix version
    # 0 - Build number (optional)

    'depends': [
        'purchase',
        'stock',
        'account',
    ],
    'external_dependencies': {
        'python': ['requests', 'openpyxl'],
        'bin': ['wkhtmltopdf'],
    },
}
```

#### ✅ Migration Scripts
```python
# migrations/18.0.1.0.0/pre-migration.py
def migrate(cr, version):
    """Pre-migration script for version 18.0.1.0.0"""

    # Update old field names
    cr.execute("""
        ALTER TABLE purchase_order
        RENAME COLUMN old_field TO x_old_field
    """)

    # Add new fields with default values
    cr.execute("""
        ALTER TABLE purchase_order
        ADD COLUMN x_priority_level VARCHAR DEFAULT 'medium'
    """)

    # Migrate data
    cr.execute("""
        UPDATE purchase_order
        SET x_priority_level = CASE
            WHEN amount_total > 1000000 THEN 'high'
            WHEN amount_total > 500000 THEN 'medium'
            ELSE 'low'
        END
        WHERE x_priority_level = 'medium'
    """)

# migrations/18.0.2.0.0/post-migration.py
def migrate(cr, version):
    """Post-migration script for version 18.0.2.0.0"""

    # Create indexes for performance
    cr.execute("""
        CREATE INDEX IF NOT EXISTS idx_purchase_order_priority
        ON purchase_order (x_priority_level, state)
    """)

    # Update computed fields
    cr.execute("""
        UPDATE purchase_order
        SET x_total_weight = NULL
        WHERE x_total_weight IS NOT NULL
    """)
```

### 2. Configuration Management

#### ✅ System Parameters
```python
# Custom system parameters
class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Purchase configuration
    purchase_approval_limit = fields.Float(
        string='Approval Limit',
        config_parameter='custom_purchase.approval_limit',
        default=1000000.0
    )

    purchase_auto_email = fields.Boolean(
        string='Auto Email Notifications',
        config_parameter='custom_purchase.auto_email',
        default=True
    )

    purchase_default_currency = fields.Many2one(
        'res.currency',
        string='Default Currency',
        config_parameter='custom_purchase.default_currency'
    )

    # Vendor management
    vendor_performance_days = fields.Integer(
        string='Performance Analysis Days',
        config_parameter='custom_purchase.vendor_performance_days',
        default=30
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICP = self.env['ir.config_parameter'].sudo()

        res.update({
            'purchase_approval_limit': float(ICP.get_param('custom_purchase.approval_limit', '1000000.0')),
            'purchase_auto_email': ICP.get_param('custom_purchase.auto_email', 'True') == 'True',
            'purchase_default_currency': int(ICP.get_param('custom_purchase.default_currency', '1')),
            'vendor_performance_days': int(ICP.get_param('custom_purchase.vendor_performance_days', '30')),
        })
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ICP = self.env['ir.config_parameter'].sudo()

        ICP.set_param('custom_purchase.approval_limit', str(self.purchase_approval_limit))
        ICP.set_param('custom_purchase.auto_email', str(self.purchase_auto_email))
        ICP.set_param('custom_purchase.default_currency', str(self.purchase_default_currency.id))
        ICP.set_param('custom_purchase.vendor_performance_days', str(self.vendor_performance_days))
```

### 3. Monitoring & Logging

#### ✅ Custom Logging
```python
import logging
from odoo import _

_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def button_confirm(self):
        """Override with enhanced logging"""
        _logger.info("Starting PO confirmation for order %s", self.name)

        try:
            # Business logic here
            result = super(PurchaseOrder, self).button_confirm()

            # Success logging
            _logger.info(
                "PO %s confirmed successfully. Total: %.2f, Vendor: %s",
                self.name, self.amount_total, self.partner_id.name
            )

            # Business event tracking
            self._track_event('purchase_order_confirmed', {
                'amount': self.amount_total,
                'vendor': self.partner_id.name,
                'user': self.env.user.name,
            })

            return result

        except Exception as e:
            # Error logging with context
            _logger.error(
                "Failed to confirm PO %s. Error: %s. User: %s, Total: %.2f",
                self.name, str(e), self.env.user.name, self.amount_total,
                exc_info=True
            )
            raise

    def _track_event(self, event_type, context_data=None):
        """Track business events for monitoring"""
        event_vals = {
            'event_type': event_type,
            'model': 'purchase.order',
            'res_id': self.id,
            'user_id': self.env.user.id,
            'create_date': fields.Datetime.now(),
        }

        if context_data:
            event_vals.update(context_data)

        self.env['business.event.log'].create(event_vals)
```

#### ✅ Performance Monitoring
```python
# Custom performance monitoring decorator
import time
import functools

def monitor_performance(threshold_seconds=1.0):
    """Decorator to monitor method performance"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            start_time = time.time()
            try:
                result = func(self, *args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if duration > threshold_seconds:
                    _logger.warning(
                        "Slow method detected: %s took %.2f seconds",
                        func.__name__, duration
                    )
        return wrapper
    return decorator

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @monitor_performance(threshold_seconds=2.0)
    def _compute_amount_all(self):
        """Monitor expensive amount calculation"""
        return super(PurchaseOrder, self)._compute_amount_all()
```

## 📋 Testing Checklist

### ✅ Pre-Deployment Checklist

#### Code Quality
- [ ] All custom fields follow naming convention (`x_` prefix)
- [ ] Methods include proper docstrings with Vietnamese descriptions
- [ ] Error messages are user-friendly and Vietnamese
- [ ] No hard-coded IDs or references
- [ ] Proper use of `super()` in overrides
- [ ] Security rules implemented for custom access
- [ ] Performance queries optimized

#### Functionality Testing
- [ ] All workflows tested end-to-end
- [ ] Validations work for all edge cases
- [ ] Integration with inventory works
- [ ] Integration with accounting works
- [ ] Permissions and access control tested
- [ ] Multi-language support (Vietnamese) tested
- [ ] Email notifications work correctly

#### Performance Testing
- [ ] Database queries optimized
- [ ] Computed fields use `store=True` where appropriate
- [ ] Bulk operations tested
- [ ] Large dataset performance tested
- [ ] Memory usage monitored
- [ ] Concurrent operation handling tested

#### Security Testing
- [ ] Access rights properly configured
- [ ] Record rules prevent data leakage
- [ ] Sensitive fields protected
- [ ] SQL injection prevention verified
- [ ] Cross-site scripting (XSS) prevention
- [ ] Authentication and authorization tested

#### Deployment Testing
- [ ] Migration scripts tested
- [ ] Data backup and recovery tested
- [ ] Rollback procedures tested
- [ ] Configuration settings validated
- [ ] Monitoring and logging functional
- [ ] Documentation complete and updated

### ✅ Production Deployment Steps

1. **Backup Current System**
   ```bash
   # Database backup
   pg_dump -h localhost -U odoo -d production_db > backup_$(date +%Y%m%d_%H%M%S).sql

   # File system backup
   tar -czf addons_backup_$(date +%Y%m%d_%H%M%S).tar.gz /opt/odoo/addons/
   ```

2. **Deploy Code Changes**
   ```bash
   # Update addons
   cd /opt/odoo/addons/
   git pull origin main

   # Install/Update module
   sudo -u odoo /opt/odoo/odoo-bin -d production_db -u custom_purchase --without-demo
   ```

3. **Run Migration Scripts**
   ```bash
   # Run specific migration
   sudo -u odoo /opt/odoo/odoo-bin -d production_db --stop-after-init
   ```

4. **Validate Deployment**
   ```bash
   # Check module status
   psql -h localhost -U odoo -d production_db -c "SELECT name, state FROM ir_module_module WHERE name='custom_purchase';"

   # Check database integrity
   sudo -u odoo /opt/odoo/odoo-bin -d production_db --stop-after-init --test-enable
   ```

5. **Monitor System Health**
   ```bash
   # Check logs for errors
   tail -f /var/log/odoo/odoo.log

   # Monitor system resources
   top -p $(pgrep -f odoo-bin)
   ```

## 📚 Additional Resources

### Testing Framework References
- [Odoo Testing Documentation](https://www.odoo.com/documentation/18.0/developer/reference/backend/testing.html)
- [Python unittest Framework](https://docs.python.org/3/library/unittest.html)
- [JavaScript QUnit Testing](https://qunitjs.com/)

### Performance Optimization
- [Odoo Performance Guide](https://www.odoo.com/documentation/18.0/developer/reference/backend/performance.html)
- [PostgreSQL Performance Tuning](https://wiki.postgresql.org/wiki/Tuning_Your_PostgreSQL_Server)

### Security Best Practices
- [Odoo Security Guide](https://www.odoo.com/documentation/18.0/developer/reference/backend/security.html)
- [OWASP Security Guidelines](https://owasp.org/)

---

**Kết luận**: Best practices và testing strategies này đảm bảo chất lượng, performance, và security cho custom module Purchase. Segarkan test và deployment checklist thường xuyên để maintain standards.

**Next Steps**: Xem [README.md](README.md) cho overview và navigation của toàn bộ documentation series.