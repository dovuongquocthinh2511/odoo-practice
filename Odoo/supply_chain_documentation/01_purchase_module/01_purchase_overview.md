# 📖 Tổng Quan Module Purchase - Architecture và Components

## 🎯 Giới Thiệu

Module Purchase trong Odoo 18 là một trong những modules cốt lõi của hệ thống ERP, chịu trách nhiệm quản lý toàn bộ quy trình mua hàng từ yêu cầu báo giá (RFQ) đến khi hóa đơn được thanh toán. Module này tích hợp chặt chẽ với Inventory, Accounting, và Vendor Management.

## 🏗️ Module Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    PURCHASE MODULE                          │
├─────────────────────────────────────────────────────────────┤
│  Frontend (Web Interface)                                   │
│  ├── Purchase Orders Management                            │
│  ├── RFQ (Request for Quotation)                           │
│  ├── Vendor Portals                                        │
│  └── Dashboard & Analytics                                  │
├─────────────────────────────────────────────────────────────┤
│  Backend (Business Logic)                                   │
│  ├── Models (purchase.order, purchase.order.line)          │
│  ├── Workflow Engine                                        │
│  ├── Integration Services                                   │
│  └── Security & Access Control                              │
├─────────────────────────────────────────────────────────────┤
│  Integration Layer                                          │
│  ├── Stock Management (stock.picking)                      │
│  ├── Accounting (account.move)                              │
│  ├── Vendor Management (res.partner)                       │
│  └── Reporting & Analytics                                  │
└─────────────────────────────────────────────────────────────┘
```

## 📊 Data Model Architecture

### 1. Purchase Order Model (`purchase.order`)

**Purpose**: Entity chính quản lý đơn hàng mua
**Table**: `purchase_order`

#### Key Fields Overview
```python
class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ['portal.mixin', 'product.catalog.mixin', 'mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char('Order Reference', required=True)  # PO number
    partner_id = fields.Many2one('res.partner', 'Vendor', required=True)
    date_order = fields.Datetime('Order Deadline', required=True)

    # Status & Workflow
    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ])

    # Financial Information
    currency_id = fields.Many2one('res.currency', required=True)
    amount_total = fields.Monetary(compute='_amount_all', store=True)

    # Relations
    order_line = fields.One2many('purchase.order.line', 'order_id')
    invoice_ids = fields.Many2many('account.move', compute="_compute_invoice")
```

### 2. Purchase Order Line Model (`purchase.order.line`)

**Purpose**: Chi tiết từng sản phẩm trong đơn hàng
**Table**: `purchase_order_line`

#### Key Fields Overview
```python
class PurchaseOrderLine(models.Model):
    _name = 'purchase.order.line'
    _inherit = 'analytic.mixin'

    # Product Information
    product_id = fields.Many2one('product.product', 'Product')
    name = fields.Text('Description', required=True)
    product_qty = fields.Float('Quantity', required=True)
    product_uom = fields.Many2one('uom.uom', 'Unit of Measure')

    # Pricing
    price_unit = fields.Float('Unit Price', required=True)
    discount = fields.Float('Discount (%)')
    price_total = fields.Monetary(compute='_compute_amount', store=True)

    # Status & Integration
    qty_received = fields.Float('Received Qty', compute='_compute_qty_received', store=True)
    qty_invoiced = fields.Float('Billed Qty', compute='_compute_qty_invoiced', store=True)

    # Relations
    order_id = fields.Many2one('purchase.order', 'Order Reference', required=True)
    invoice_lines = fields.One2many('account.move.line', 'purchase_line_id')
```

## 🔄 Workflow Architecture

### State Machine Diagram

```
    ┌─────────┐
    │  Draft  │ ──→ ┌──────────┐ ──→ ┌─────────────┐
    │ (RFQ)   │     │   Sent   │     │ To Approve   │
    └─────────┘     │(RFQ Sent)│     │(Validation) │
         │          └──────────┘     └─────────────┘
         │                │                   │
         │                ↓                   ↓
         │          ┌─────────────┐     ┌─────────────┐
         │          │   Cancel    │     │  Purchase   │
         │          └─────────────┘     │   (Order)   │
         │                ↑             └─────────────┘
         └────────────────┘                    │
                              │                ↓
                              │          ┌─────────────┐
                              └────────── │    Done     │
                                         │  (Locked)   │
                                         └─────────────┘
```

### Workflow States Detail

| State | Vietnamese | Description | Key Actions |
|-------|------------|-------------|--------------|
| `draft` | RFQ (Nháp) | Request for Quotation đang soạn thảo | `action_rfq_send`, `button_confirm` |
| `sent` | RFQ Đã Gửi | RFQ đã gửi cho vendor | `print_quotation`, `button_confirm` |
| `to approve` | Chờ Duyệt | PO cần approval từ manager | `button_approve`, `button_cancel` |
| `purchase` | Purchase Order | PO đã được xác nhận, ready để execute | `button_unlock`, `create_picking` |
| `done` | Hoàn Thành | PO locked sau khi hoàn thành | `button_unlock` |
| `cancel` | Hủy Bỏ | PO bị hủy | `button_draft` (nếu có quyền) |

## 🔌 Integration Architecture

### 1. Inventory Integration (`purchase_stock`)

**Flow**: Purchase Order → Stock Picking → Receipt
```
purchase.order → _create_picking() → stock.picking → stock.move
      ↓                                    ↓
   confirm                             done/validated
      ↓                                    ↓
   products                           products received
```

**Key Integration Points**:
- `stock.picking`: Tạo receipt picking khi PO confirmed
- `stock.move`: Movement lines cho từng product
- `stock.location`: Source/Destination locations
- `procurement`: Demand-driven procurement

### 2. Accounting Integration (`account`)

**Flow**: Receipt → Invoice → Payment
```
purchase.order → account.move → account.payment
      ↓               ↓              ↓
   receipt       vendor bill      payment
      ↓               ↓              ↓
   qty_received   invoice_lines  reconciliation
```

**Key Integration Points**:
- `account.move`: Vendor bills generation
- `account.move.line`: Invoice lines matching PO lines
- `account.payment`: Payment processing
- `tax`: Tax calculations và reporting

### 3. Vendor Management Integration (`base`)

**Flow**: Partner → Performance → Analytics
```
res.partner → purchase.order → analytics/reports
     ↓               ↓                 ↓
  vendor info   purchase history   performance metrics
```

## 🔧 Technical Architecture Details

### 1. Inheritance Hierarchy

```python
PurchaseOrder
├── mail.thread (Chatter & Activities)
├── mail.activity.mixin (Activity Management)
├── portal.mixin (Portal Access)
└── product.catalog.mixin (Product Catalog)

PurchaseOrderLine
├── analytic.mixin (Analytic Accounting)
└── mail.thread (Chatter support)
```

### 2. Computing Fields Architecture

**Price Calculations**:
```python
# Line-level calculations
price_subtotal = product_qty * price_unit * (1 - discount/100)
price_tax = tax calculation based on taxes_id
price_total = price_subtotal + price_tax

# Order-level aggregations
amount_untaxed = sum(order_lines.price_subtotal)
amount_tax = sum(order_lines.price_tax)
amount_total = amount_untaxed + amount_tax
```

**Quantity Tracking**:
```python
qty_received = sum(stock.moves.qty_done for related pickings)
qty_invoiced = sum(invoice_lines.quantity for related invoices)
qty_to_invoice = product_qty - qty_invoiced
```

### 3. Security Architecture

**Access Rights Structure**:
```
purchase.order
├── User: Read own orders
├── Manager: All operations
└── Portal: Access to own company orders

purchase.order.line
├── User: Read (inherited from order)
└── Manager: All operations (inherited from order)
```

**Record Rules**:
- Multi-company filtering
- Vendor access restrictions
- Read/write permissions based on user roles

## 📈 Performance Architecture

### 1. Database Optimization
- Indexed fields: `name`, `partner_id`, `date_order`, `state`
- Computed fields with `store=True` cho performance
- Optimized SQL queries với proper joins

### 2. Caching Strategy
- Price calculations cached tại database level
- Product information caching
- Vendor pricelist caching

### 3. Batch Processing
- Bulk order processing
- Background jobs cho large operations
- Optimized picking creation cho multiple orders

## 🌐 Multi-Company Architecture

### Company Isolation
```python
company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
currency_id = fields.Many2one('res.currency', compute='_compute_currency_id', store=True)
```

### Cross-Company Features
- Inter-company transfers
- Consolidated reporting
- Company-specific pricing

## 🔍 Module Dependencies

### Required Dependencies
```python
'depends': [
    'account',           # Financial integration
    'mail',              # Email và notifications
    'product',           # Product management
    'web',               # Web interface
]
```

### Optional Dependencies
```python
# Inventory integration
'purchase_stock' → stock module integration
'purchase_mrp' → Manufacturing integration

# Advanced features
'purchase_requisition' → Purchase requisitions
'purchase_landed_cost' → Landed cost calculation
```

## 📚 File Structure Overview

```
purchase/
├── __init__.py              # Module initialization
├── __manifest__.py          # Module manifest
├── models/                  # Data models
│   ├── __init__.py
│   ├── purchase_order.py     # Main PO model
│   ├── purchase_order_line.py # PO lines
│   ├── account_invoice.py    # Invoice integration
│   └── res_partner.py        # Vendor enhancements
├── views/                   # UI views
│   ├── purchase_views.xml   # Forms, lists, searches
│   └── purchase_order_views.xml
├── security/                # Access control
│   ├── purchase_security.xml # Security rules
│   └── ir.model.access.csv   # Access rights
├── data/                    # Default data
├── report/                  # Reports
├── static/                  # Web assets
└── controllers/             # Web controllers
```

## 🎯 Key Features Summary

### Core Functionality
1. **Request for Quotation (RFQ)**
   - Tạo và quản lý yêu cầu báo giá
   - Send emails cho vendors
   - Track vendor responses

2. **Purchase Order Management**
   - Convert RFQ → Purchase Order
   - Multi-level approval workflows
   - Contract và terms management

3. **Receipt Processing**
   - Inventory integration
   - Quality control workflows
   - Partial/full receipt handling

4. **Invoice Management**
   - Three-way matching (PO-Receipt-Invoice)
   - Automated invoice generation
   - Discrepancy resolution

5. **Vendor Management**
   - Supplier performance tracking
   - Pricelist management
   - Communication history

### Advanced Features
- **Multi-company support**
- **Multi-currency operations**
- **Advanced reporting**
- **Portal access cho vendors**
- **Mobile-friendly interface**
- **API integration capabilities**

## 🚀 Getting Started with Development

### 1. Understanding the Base Models
Đọc [02_models_reference.md](02_models_reference.md) cho detailed model documentation.

### 2. Workflow Customization
Xem [03_workflows_guide.md](03_workflows_guide.md) để hiểu state transitions.

### 3. Integration Patterns
Đọc [04_integration_patterns.md](04_integration_patterns.md) cho detailed integration examples.

### 4. Code Examples
Xem [05_code_examples.md](05_code_examples.md) cho practical implementations.

---

**Next Steps**: Đọc tiếp model documentation để hiểu detailed implementation.