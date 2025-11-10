# 📋 Model Reference Documentation - Inventory Module

## 🎯 Giới Thiệu

Documentation chi tiết về các models, fields, và methods trong Inventory Module Odoo 18. Đây là reference kỹ thuật toàn diện cho developers khi customizing và extending inventory functionality.

## 📦 Stock Picking Model (`stock.picking`)

### Model Definition

```python
class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = "Transfer"
    _order = "priority desc, scheduled_date asc, id desc"
    _rec_name = "name"
```

### Field Specifications

#### 🏷️ Basic Information Fields

| Field | Type | Required | Default | Description | Vietnamese |
|-------|------|----------|---------|-------------|------------|
| `name` | Char | ✅ | `'/'` | Picking reference | Mã phiếu xuất/nhập |
| `origin` | Char | ❌ | `False` | Source document reference | Nguồn tài liệu |
| `backorder_id` | Many2one | ❌ | `False` | Backorder reference | Phiếu chờ liên quan |
| `priority` | Selection | ❌ | `'1'` | Priority level | Mức độ ưu tiên |
| `scheduled_date` | Datetime | ✅ | `now()` | Scheduled date | Ngày dự kiến |

```python
priority = fields.Selection([
    ('0', 'Low'),
    ('1', 'Normal'),
    ('2', 'High'),
    ('3', 'Urgent')
], string='Priority', default='1', index=True)
```

#### 🏪 Location & Operation Fields

| Field | Type | Required | Relation | Description | Vietnamese |
|-------|------|----------|----------|-------------|------------|
| `location_id` | Many2one | ✅ | `stock.location` | Source location | Địa điểm nguồn |
| `location_dest_id` | Many2one | ✅ | `stock.location` | Destination location | Địa điểm đích |
| `picking_type_id` | Many2one | ✅ | `stock.picking.type` | Operation type | Loại thao tác |
| `move_type` | Selection | ✅ | `'direct'` | Move type | Loại di chuyển |

```python
move_type = fields.Selection([
    ('direct', 'Partial'),
    ('one', 'All at once')
], string='Operation Type', default='direct', required=True, index=True)
```

#### 🔄 Workflow & Status Fields

| Field | Type | Required | Default | Values | Vietnamese |
|-------|------|----------|---------|--------|------------|
| `state` | Selection | ✅ | `'draft'` | Workflow states | Trạng thái |
| `is_locked` | Boolean | ❌ | `False` | Locked state | Đã khóa |
| `printed` | Boolean | ❌ | `False` | Printed status | Đã in |

```python
state = fields.Selection([
    ('draft', 'Draft'),
    ('confirmed', 'Waiting'),
    ('assigned', 'Ready'),
    ('waiting', 'Waiting Another Operation'),
    ('done', 'Done'),
    ('cancel', 'Cancelled')
], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)
```

### Method Documentation

#### 🔄 Workflow Methods

##### `action_confirm()`
```python
def action_confirm(self):
    """
    Confirm the picking and check availability
    """
    # Purpose: Xác nhận phiếu và kiểm tra availability
    # Logic:
    # 1. Check move availability
    # 2. Update state to confirmed/assigned
    # 3. Trigger procurement if needed
    # Returns: True
```

##### `action_assign()`
```python
def action_assign(self):
    """
    Reserve the stock moves
    """
    # Purpose: Đặt trước các stock moves
    # Logic:
    # 1. Check quants availability
    # 2. Reserve stock for moves
    # 3. Update state to assigned
    # Returns: True
```

##### `button_validate()`
```python
def button_validate(self):
    """
    Validate the picking
    """
    # Purpose: Hoàn thành phiếu xuất/nhập kho
    # Logic:
    # 1. Process stock moves
    # 2. Update inventory levels
    # 3. Generate accounting entries
    # 4. Update state to done
    # Returns: Dictionary for wizard
```

#### 🔍 Availability & Search Methods

##### `_check_unreserved()`
```python
def _check_unreserved(self):
    """
    Check if picking can be unreserved
    """
    # Purpose: Kiểm tra có thể hủy đặt trước
    # Returns: Boolean
    # Logic: Check if moves are in appropriate state
```

##### `action_reassign_done()`
```python
def action_reassign_done(self):
    """
    Reassign picking after changes
    """
    # Purpose: Tái phân bổ sau khi thay đổi
    # Logic:
    # 1. Unreserve all moves
    # 2. Reserve again with new parameters
    # Returns: True
```

## 🚚 Stock Move Model (`stock.move`)

### Model Definition

```python
class StockMove(models.Model):
    _name = "stock.move"
    _description = "Stock Move"
    _order = 'priority desc, date, id desc'
    _rec_name = 'product_id'
```

### Field Specifications

#### 📦 Product & Quantity Fields

| Field | Type | Required | Computed | Description | Vietnamese |
|-------|------|----------|----------|-------------|------------|
| `product_id` | Many2one | ✅ | ❌ | Product reference | Sản phẩm |
| `product_uom_qty` | Float | ✅ | ❌ | Quantity in UoM | Số lượng theo ĐVT |
| `product_uom` | Many2one | ❌ | ✅ | Unit of measure | Đơn vị tính |
| `product_qty` | Float | ❌ | ✅ | Quantity in base UoM | Số lượng gốc |

#### 💰 Financial & Valuation Fields

| Field | Type | Computed | Description | Vietnamese |
|-------|------|----------|-------------|------------|
| `price_unit` | Float | ❌ | Unit price | Đơn giá |
| `value` | Monetary | ✅ | Move value | Giá trị di chuyển |
| `remaining_value` | Monetary | ✅ | Remaining value | Giá trị còn lại |

```python
@api.depends('product_id', 'product_uom_qty', 'price_unit')
def _compute_value(self):
    for move in self:
        move.value = move.product_uom_qty * move.price_unit
        move.remaining_value = move.product_uom_qty * move.price_unit
```

#### 🔗 Relation Fields

| Field | Type | Description | Vietnamese |
|-------|------|-------------|------------|
| `picking_id` | Many2one | Related picking | Phiếu xuất/nhập |
| `location_id` | Many2one | Source location | Địa điểm nguồn |
| `location_dest_id` | Many2one | Destination location | Địa điểm đích |
| `move_orig_ids` | Many2many | Origin moves | Di chuyển nguồn |
| `move_dest_ids` | Many2many | Destination moves | Di chuyển đích |

### Method Documentation

#### 🔄 State Management Methods

##### `_action_confirm()`
```python
def _action_confirm(self, merge=True):
    """
    Confirm stock move
    """
    # Purpose: Xác nhận di chuyển tồn kho
    # Logic:
    # 1. Check procurement rules
    # 2. Create chain moves if needed
    # 3. Update state to confirmed
    # Returns: Self recordset
```

##### `_action_assign()`
```python
def _action_assign(self):
    """
    Reserve stock move
    """
    # Purpose: Đặt trước di chuyển tồn kho
    # Logic:
    # 1. Check availability
    # 2. Reserve quants
    # 3. Create move lines
    # Returns: Self recordset
```

##### `_action_done()`
```python
def _action_done(self):
    """
    Mark move as done
    """
    # Purpose: Đánh dấu hoàn thành di chuyển
    # Logic:
    # 1. Process move lines
    # 2. Update inventory levels
    # 3. Trigger accounting entries
    # Returns: Self recordset
```

#### 📊 Quantity & Valuation Methods

##### `_compute_reserved_quantity()`
```python
def _compute_reserved_quantity(self):
    """
    Compute reserved quantity
    """
    # Purpose: Tính số lượng đặt trước
    # Logic: Sum reserved quantities from move lines
    for move in self:
        move.reserved_quantity = sum(move.move_line_ids.mapped('product_qty'))
```

##### `_get_valuation_layers()`
```python
def _get_valuation_layers(self):
    """
    Get valuation layers for accounting
    """
    # Purpose: Lấy valuation layers cho kế toán
    # Returns: Account valuation layer recordset
    # Logic: Get stock valuation layers from stock moves
```

## 📦 Stock Move Line Model (`stock.move.line`)

### Model Definition

```python
class StockMoveLine(models.Model):
    _name = "stock.move.line"
    _description = "Stock Move Line"
    _order = 'result_package_id desc, id desc'
    _rec_name = 'product_id'
```

### Field Specifications

#### 📦 Product & Tracking Fields

| Field | Type | Required | Description | Vietnamese |
|-------|------|----------|-------------|------------|
| `product_id` | Many2one | ✅ | Product reference | Sản phẩm |
| `product_uom_id` | Many2one | ✅ | Unit of measure | Đơn vị tính |
| `lot_id` | Many2one | ❌ | Lot number | Số lô |
| `lot_name` | Char | ❌ | Lot name (if no lot) | Tên lô |
| `package_id` | Many2one | ❌ | Source package | Gói nguồn |
| `result_package_id` | Many2one | ❌ | Destination package | Gói đích |

#### 📊 Quantity Fields

| Field | Type | Required | Computed | Description | Vietnamese |
|-------|------|----------|----------|-------------|------------|
| `product_qty` | Float | ✅ | ❌ | Quantity | Số lượng |
| `product_uom_qty` | Float | ❌ | ✅ | Quantity in UoM | Số lượng theo ĐVT |
| `reserved_uom_qty` | Float | ❌ | ✅ | Reserved quantity | Số lượng đặt trước |

#### 🔗 Relation Fields

| Field | Type | Description | Vietnamese |
|-------|------|-------------|------------|
| `move_id` | Many2one | Related stock move | Di chuyển tồn kho |
| `picking_id` | Many2one | Related picking | Phiếu xuất/nhập |
| `location_id` | Many2one | Source location | Địa điểm nguồn |
| `location_dest_id` | Many2one | Destination location | Địa điểm đích |

### Method Documentation

#### 🏷️ Tracking Methods

##### `_action_done()`
```python
def _action_done(self):
    """
    Mark move line as done
    """
    # Purpose: Hoàn thành chi tiết di chuyển
    # Logic:
    # 1. Update quant records
    # 2. Process packages
    # 3. Handle lot/serial tracking
    # Returns: Self recordset
```

##### `_update_reserved_quantity()`
```python
def _update_reserved_quantity(self, product_qty):
    """
    Update reserved quantity
    """
    # Purpose: Cập nhật số lượng đặt trước
    # Logic: Update reserved_uom_qty field
    # Returns: Self record
```

## 📊 Stock Quant Model (`stock.quant`)

### Model Definition

```python
class StockQuant(models.Model):
    _name = "stock.quant"
    _description = "Quants"
    _order = 'product_id, location_id, lot_id, package_id, id'
```

### Field Specifications

#### 📦 Core Fields

| Field | Type | Required | Description | Vietnamese |
|-------|------|----------|-------------|------------|
| `product_id` | Many2one | ✅ | Product reference | Sản phẩm |
| `location_id` | Many2one | ✅ | Location reference | Địa điểm |
| `quantity` | Float | ✅ | Current quantity | Số lượng hiện tại |
| `reserved_quantity` | Float | ✅ | Reserved quantity | Số lượng đặt trước |

```python
@api.depends('quantity', 'reserved_quantity')
def _compute_available_quantity(self):
    for quant in self:
        quant.available_quantity = quant.quantity - quant.reserved_quantity
```

#### 🏷️ Tracking Fields

| Field | Type | Description | Vietnamese |
|-------|------|-------------|------------|
| `lot_id` | Many2one | Lot reference | Số lô |
| `package_id` | Many2one | Package reference | Gói hàng |
| `owner_id` | Many2one | Product owner | Chủ sở hữu |
| `company_id` | Many2one | Company owner | Công ty |

### Method Documentation

#### 🔄 Quantity Management Methods

##### `_update_available_quantity()`
```python
def _update_available_quantity(self, product_qty, move_line_id):
    """
    Update available quantity
    """
    # Purpose: Cập nhật số lượng available
    # Logic:
    # 1. Adjust quantity field
    # 2. Create new quant if needed
    # 3. Archive zero quantity quants
    # Returns: Quant record
```

##### `_get_available_quantity()`
```python
@api.model
def _get_available_quantity(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None):
    """
    Get available quantity for given parameters
    """
    # Purpose: Lấy số lượng available theo tham số
    # Returns: Float quantity
    # Logic: Search and sum available quants
```

## 🏪 Stock Location Model (`stock.location`)

### Model Definition

```python
class StockLocation(models.Model):
    _name = "stock.location"
    _description = "Inventory Locations"
    _order = 'parent_path'
    _parent_name = "location_id"
    _parent_store = True
```

### Field Specifications

#### 📍 Location Hierarchy Fields

| Field | Type | Required | Description | Vietnamese |
|-------|------|----------|-------------|------------|
| `name` | Char | ✅ | Location name | Tên địa điểm |
| `location_id` | Many2one | ❌ | Parent location | Địa điểm cha |
| `child_ids` | One2many | ❌ | Child locations | Địa điểm con |

#### 🏷️ Classification Fields

| Field | Type | Required | Default | Description | Vietnamese |
|-------|------|----------|---------|-------------|------------|
| `usage` | Selection | ❌ | `'internal'` | Location usage | Loại địa điểm |
| `scrap_location` | Boolean | ❌ | `False` | Scrap location | Địa điểm hỏng |

```python
usage = fields.Selection([
    ('supplier', 'Vendor Location'),
    ('view', 'View'),
    ('internal', 'Internal Location'),
    ('customer', 'Customer Location'),
    ('inventory', 'Inventory Loss'),
    ('procurement', 'Procurement'),
    ('production', 'Production'),
    ('transit', 'Transit Location')
], string='Location Type', default='internal')
```

### Method Documentation

#### 🔍 Search & Navigation Methods

##### `search_by_name()`
```python
@api.model
def search_by_name(self, name):
    """
    Search location by name with hierarchy support
    """
    # Purpose: Tìm địa điểm theo tên với hỗ trợ hierarchy
    # Returns: Location recordset
    # Logic: Search locations matching name pattern
```

##### `get_putaway_strategy()`
```python
def get_putaway_strategy(self, product):
    """
    Get putaway strategy for product
    """
    # Purpose: Lấy chiến lược cất hàng cho sản phẩm
    # Returns: Destination location or False
    # Logic: Check putaway rules and return appropriate location
```

## 🏭 Stock Warehouse Model (`stock.warehouse`)

### Model Definition

```python
class StockWarehouse(models.Model):
    _name = "stock.warehouse"
    _description = "Warehouse"
    _order = "name asc"
```

### Field Specifications

#### 🏪 Basic Warehouse Fields

| Field | Type | Required | Relation | Description | Vietnamese |
|-------|------|----------|----------|-------------|------------|
| `name` | Char | ✅ | - | Warehouse name | Tên kho |
| `company_id` | Many2one | ✅ | `res.company` | Company | Công ty |
| `partner_id` | Many2one | ❌ | `res.partner` | Warehouse address | Địa chỉ kho |

#### 📍 Location Fields

| Field | Type | Required | Relation | Description | Vietnamese |
|-------|------|----------|----------|-------------|------------|
| `lot_stock_id` | Many2one | ✅ | `stock.location` | Stock location | Vị trí tồn kho |
| `wh_input_stock_loc_id` | Many2one | ❌ | `stock.location` | Input location | Vị trí nhập kho |
| `wh_output_stock_loc_id` | Many2one | ❌ | `stock.location` | Output location | Vị trí xuất kho |

#### 🛒 Route Configuration Fields

| Field | Type | Required | Description | Vietnamese |
|-------|------|----------|-------------|------------|
| `route_ids` | Many2many | ❌ | Warehouse routes | Tuyến đường kho |
| `default_resupply_wh_id` | Many2one | ❌ | Default resupply warehouse | Kho bổ sung mặc định |

### Method Documentation

#### 🛒 Route Management Methods

##### `_update_routes()`
```python
def _update_routes(self):
    """
    Update warehouse routes
    """
    # Purpose: Cập nhật tuyến đường kho
    # Logic:
    # 1. Create/update resupply routes
    # 2. Configure picking types
    # 3. Update route sequences
    # Returns: True
```

##### `get_routes_count()`
```python
def get_routes_count(self):
    """
    Count of routes for the warehouse
    """
    # Purpose: Đếm số lượng tuyến đường
    # Returns: Integer count
    # Logic: Count active routes
```

## ⚙️ Stock Rule Model (`stock.rule`)

### Model Definition

```python
class StockRule(models.Model):
    _name = "stock.rule"
    _description = "Stock Rules"
    _order = "route_sequence, id"
```

### Field Specifications

#### 🔧 Rule Configuration Fields

| Field | Type | Required | Description | Vietnamese |
|-------|------|----------|-------------|------------|
| `name` | Char | ✅ | Rule name | Tên quy tắc |
| `action` | Selection | ✅ | Action type | Loại hành động |
| `route_sequence` | Integer | ❌ | Route sequence | Thứ tự tuyến |

```python
action = fields.Selection([
    ('pull', 'Pull from'),
    ('push', 'Push to'),
    ('pull_push', 'Pull & Push')
], string='Action', required=True, default='pull')
```

#### 🏪 Procurement Fields

| Field | Type | Relation | Description | Vietnamese |
|-------|------|----------|-------------|------------|
| `company_id` | Many2one | `res.company` | Company | Công ty |
| `route_id` | Many2one | `stock.location.route` | Route | Tuyến đường |
| `picking_type_id` | Many2one | `stock.picking.type` | Picking type | Loại xuất/nhập |
| `warehouse_id` | Many2one | `stock.warehouse` | Warehouse | Kho hàng |

### Method Documentation

#### 🔄 Rule Evaluation Methods

##### `_run_pull()`
```python
def _run_pull(self, procurements):
    """
    Execute pull rule
    """
    # Purpose: Thực thi quy tắc kéo
    # Logic:
    # 1. Create stock moves
    # 2. Trigger procurement
    # 3. Update move destinations
    # Returns: Stock move recordset
```

##### `_run_push()`
```python
def _run_push(self, move):
    """
    Execute push rule
    """
    # Purpose: Thực thi quy tắc đẩy
    # Logic:
    # 1. Create destination move
    # 2. Chain moves together
    # 3. Update move locations
    # Returns: Stock move record
```

## 🔗 Integration Models

### Account Move Integration (`account.move`)

#### Additional Fields for Inventory

```python
class AccountMove(models.Model):
    _inherit = 'account.move'

    stock_move_id = fields.Many2one('stock.move')
    stock_move_count = fields.Integer(compute="_compute_stock_move_count")
```

#### Key Integration Methods

##### `_get_stock_valuation_lines()`
```python
def _get_stock_valuation_lines(self):
    """
    Get stock valuation lines for accounting
    """
    # Purpose: Lấy stock valuation lines cho kế toán
    # Returns: Account move line recordset
    # Logic: Get stock moves and create accounting entries
```

## 🔒 Security & Access Control

### Access Rights Structure

```csv
id,name,model_id/id,group_id/id,perm_read,perm_write,perm_create,perm_unlink
access_stock_picking_user,stock.picking.user,model_stock_picking,stock.group_stock_user,1,1,1,0
access_stock_picking_manager,stock.picking.manager,model_stock_picking,stock.group_stock_manager,1,1,1,1
access_stock_move_user,stock.move.user,model_stock_move,stock.group_stock_user,1,1,1,0
access_stock_move_manager,stock.move.manager,model_stock_move,stock.group_stock_manager,1,1,1,1
```

### Record Rules

```xml
<record id="stock_picking_rule_user" model="ir.rule">
    <field name="name">Stock Picking: User can see their pickings</field>
    <field name="model_id" ref="model_stock_picking"/>
    <field name="domain_force">[('company_id', 'in', user.company_ids.ids)]</field>
    <field name="groups" eval="[(4, ref('stock.group_stock_user'))]"/>
</record>
```

## 🔍 SQL Constraints & Validations

### Stock Picking Constraints

```python
_sql_constraints = [
    ('name_uniq', 'unique(name, company_id)', 'Reference must be unique per company!'),
    ('picking_type_check', 'check(location_id != location_dest_id)', 'Source and destination locations must be different!'),
]
```

### Stock Move Constraints

```python
_sql_constraints = [
    ('product_qty_check', 'check(product_qty >= 0)', 'Quantity must be positive!'),
    ('location_check', 'check(location_id != location_dest_id)', 'Source and destination must be different!'),
]
```

## 📊 Database Schema Overview

### Tables Structure

```sql
-- Stock Locations
CREATE TABLE stock_location (
    id INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL,
    location_id INTEGER REFERENCES stock_location(id),
    usage VARCHAR DEFAULT 'internal',
    company_id INTEGER REFERENCES res_company(id),
    parent_path VARCHAR
);

-- Stock Warehouses
CREATE TABLE stock_warehouse (
    id INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL,
    company_id INTEGER REFERENCES res_company(id),
    lot_stock_id INTEGER REFERENCES stock_location(id)
);

-- Stock Pickings
CREATE TABLE stock_picking (
    id INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL,
    location_id INTEGER REFERENCES stock_location(id),
    location_dest_id INTEGER REFERENCES stock_location(id),
    state VARCHAR DEFAULT 'draft',
    picking_type_id INTEGER REFERENCES stock_picking_type(id),
    scheduled_date TIMESTAMP
);

-- Stock Moves
CREATE TABLE stock_move (
    id INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL,
    location_id INTEGER REFERENCES stock_location(id),
    location_dest_id INTEGER REFERENCES stock_location(id),
    product_id INTEGER REFERENCES product_product(id),
    product_uom_qty DECIMAL,
    state VARCHAR DEFAULT 'draft',
    picking_id INTEGER REFERENCES stock_picking(id)
);

-- Stock Move Lines
CREATE TABLE stock_move_line (
    id INTEGER PRIMARY KEY,
    move_id INTEGER REFERENCES stock_move(id),
    product_id INTEGER REFERENCES product_product(id),
    location_id INTEGER REFERENCES stock_location(id),
    location_dest_id INTEGER REFERENCES stock_location(id),
    product_qty DECIMAL,
    lot_id INTEGER REFERENCES stock_production_lot(id),
    package_id INTEGER REFERENCES stock_package(id)
);

-- Stock Quants
CREATE TABLE stock_quant (
    id INTEGER PRIMARY KEY,
    product_id INTEGER REFERENCES product_product(id),
    location_id INTEGER REFERENCES stock_location(id),
    quantity DECIMAL,
    reserved_quantity DECIMAL,
    lot_id INTEGER REFERENCES stock_production_lot(id),
    company_id INTEGER REFERENCES res_company(id)
);
```

## 🔧 Extending Models

### Custom Field Addition

```python
class StockPicking(models.Model):
    _inherit = 'stock.picking'

    custom_field = fields.Char('Custom Field')
    custom_date = fields.Date('Custom Date')

    @api.depends('custom_field')
    def _compute_custom_logic(self):
        # Custom computation logic
        pass
```

### Custom Validation

```python
@api.constrains('scheduled_date')
def _check_scheduled_date(self):
    for picking in self:
        if picking.scheduled_date < fields.Datetime.now():
            raise ValidationError('Scheduled date cannot be in the past!')
```

## 📈 Performance Optimizations

### Computed Fields Optimization

```python
# Use store=True for expensive computations
@api.depends('move_line_ids.product_qty')
def _compute_total_quantity(self):
    # Optimized calculation using SQL for large datasets
    for picking in self:
        if picking.id:
            query = """
                SELECT COALESCE(SUM(product_qty), 0)
                FROM stock_move_line
                WHERE picking_id = %s
            """
            picking.env.cr.execute(query, (picking.id,))
            picking.total_quantity = picking.env.cr.fetchone()[0] or 0
```

### Query Optimization

```python
# Use prefetch_related and select_related
pickings = self.env['stock.picking'].search([
    ('state', '=', 'assigned')
]).with_context(prefetch_fields=False)

# Batch processing for large operations
def _batch_update_quantities(self, move_lines):
    # Update quantities in batches for better performance
    BATCH_SIZE = 100
    for i in range(0, len(move_lines), BATCH_SIZE):
        batch = move_lines[i:i + BATCH_SIZE]
        # Process batch
```

---

**Next Steps**: Đọc [03_warehouse_operations.md](03_warehouse_operations.md) để hiểu detailed workflow implementations.

**File Size**: ~8,000 từ
**Language**: Tiếng Việt
**Target Audience**: Developers, Technical Consultants
**Completion**: 2025-11-08

*File này cung cấp comprehensive model reference cho Inventory Module Odoo 18, phục vụ như technical guide cho developers.*