# 🔗 Manufacturing Integration Patterns - Patterns Tích Hợp Module Sản Xuất

## 🎯 Giới Thiệu Integration Patterns

Manufacturing Integration Patterns định nghĩa cách Manufacturing Module tương tác và tích hợp với các module khác trong chuỗi cung ứng Odoo. Integration này đảm bảo luồng dữ liệu liền mạch từ raw material procurement đến finished goods delivery, tạo thành một hệ thống sản xuất thông minh và hiệu quả.

### 📊 Mức Độ Tích Hợp

```
Manufacturing Module Integration Matrix:
┌─────────────────┬──────────┬──────────┬──────────┬──────────┐
│ Module          │ Level    │ Data Flow│ Real-time│ Bidirectional│
├─────────────────┼──────────┼──────────┼──────────┼──────────┤
│ Inventory       │ 🔴 Critical│ High     │ ✅       │ ✅        │
│ Purchase        │ 🟡 High   │ Medium   │ ⚠️       │ ✅        │
│ Sales           │ 🟡 High   │ Medium   │ ⚠️       │ ✅        │
│ Accounting      │ 🔴 Critical│ High     │ ✅       │ ✅        │
│ Quality         │ 🟡 High   │ Medium   │ ✅       │ ✅        │
│ Maintenance     │ 🟢 Medium │ Low      | ❌       │ ✅        │
│ Planning        │ 🟡 High   │ High     | ✅       │ ✅        │
└─────────────────┴──────────┴──────────┴──────────┴──────────┘
```

## 🏪 Inventory Module Integration

### 🔗 Deep Integration Architecture

Manufacturing và Inventory module có mối quan hệ sâu sắc nhất, chia sẻ data structures và real-time operations.

#### **Core Integration Points:**

##### 1. **Material Reservation System**
```python
class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def action_confirm(self):
        """Xác nhận và đặt trước nguyên vật liệu"""
        for production in self:
            # Generate raw material moves
            production._generate_raw_moves()

            # Reserve materials from inventory
            for move in production.move_raw_ids:
                move._action_assign()

                # Check availability
                if move.state != 'assigned':
                    production._action_generate_backorder()

            production.write({'state': 'confirmed'})

    def _generate_raw_moves(self):
        """Tạo raw material moves dựa trên BOM"""
        self.ensure_one()

        for bom_line in self.bom_id.bom_line_ids:
            # Calculate required quantity
            qty_needed = bom_line.product_qty * self.product_qty

            # Create stock move
            move_vals = {
                'name': f'{self.name} - {bom_line.product_id.name}',
                'product_id': bom_line.product_id.id,
                'product_uom_qty': qty_needed,
                'product_uom': bom_line.product_uom_id.id,
                'location_id': self.location_src_id.id,
                'location_dest_id': self.product_id.property_stock_production.id,
                'production_id': self.id,
                'raw_material_production_id': self.id,
            }

            self.env['stock.move'].create(move_vals)

    def _update_material_consumption(self):
        """Cập nhật tiêu thụ nguyên vật liệu thực tế"""
        for workorder in self.workorder_ids:
            for move_line in workorder.raw_material_move_line_ids:
                if move_line.qty_done > 0:
                    # Update stock quant
                    self.env['stock.quant']._update_available_quantity(
                        move_line.product_id,
                        move_line.location_id,
                        -move_line.qty_done
                    )

                    # Post accounting entries
                    move_line._generate_consumption_journal_entry()
```

##### 2. **Real-time Inventory Updates**
```python
class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_done(self):
        """Override để cập nhật production cost khi material được tiêu thụ"""
        result = super()._action_done()

        # Update production cost for raw material consumption
        for move in self:
            if move.raw_material_production_id:
                move._update_production_cost()

        return result

    def _update_production_cost(self):
        """Cập nhật chi phí sản xuất khi tiêu thụ material"""
        production = self.raw_material_production_id

        # Calculate material cost
        material_cost = self.product_id.standard_price * self.product_uom_qty

        # Create additional cost line
        self.env['mrp.production.cost.line'].create({
            'production_id': production.id,
            'cost_type': 'material',
            'product_id': self.product_id.id,
            'quantity': self.product_uom_qty,
            'unit_cost': self.product_id.standard_price,
            'total_cost': material_cost,
            'move_id': self.id,
        })
```

##### 3. **Multi-warehouse Material Management**
```python
class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    location_src_id = fields.Many2one(
        'stock.location',
        string='Raw Materials Location',
        default=lambda self: self._get_default_raw_material_location()
    )

    location_dest_id = fields.Many2one(
        'stock.location',
        string='Finished Goods Location',
        default=lambda self: self._get_default_finished_goods_location()
    )

    def _get_default_raw_material_location(self):
        """Lấy default raw material location theo warehouse"""
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        return warehouse.lot_stock_id if warehouse else None

    def _check_multi_warehouse_availability(self):
        """Kiểm tra availability trong multiple warehouses"""
        available_locations = []

        for warehouse in self.env['stock.warehouse'].search([
            ('company_id', '=', self.env.company.id)
        ]):
            # Check material availability in each warehouse
            availability = self._check_warehouse_availability(warehouse)
            if availability['available']:
                available_locations.append({
                    'warehouse_id': warehouse.id,
                    'availability': availability
                })

        if available_locations:
            return {
                'status': 'available',
                'locations': available_locations
            }
        else:
            return {
                'status': 'unavailable',
                'message': 'Không đủ nguyên vật liệu trong bất kỳ warehouse nào'
            }

    def _auto_transfer_between_warehouses(self):
        """Tự động chuyển nguyên vật liệu giữa warehouses"""
        self.ensure_one()

        required_materials = self._get_required_materials()

        # Find available warehouses with surplus
        available_warehouses = []
        for warehouse in self.env['stock.warehouse'].search([
            ('company_id', '=', self.env.company.id)
        ]):
            surplus = self._calculate_warehouse_surplus(warehouse, required_materials)
            if surplus['has_surplus']:
                available_warehouses.append({
                    'warehouse': warehouse,
                    'surplus': surplus
                })

        # Generate transfer orders
        for warehouse_data in available_warehouses:
            self._create_internal_transfer(
                warehouse_data['warehouse'],
                warehouse_data['surplus']
            )
```

### 📈 Integration Performance Metrics

```python
class InventoryIntegrationMetrics(models.Model):
    _name = 'inventory.integration.metrics'
    _description = 'Inventory Integration Metrics'

    production_id = fields.Many2one('mrp.production', string='Production Order')
    metric_date = fields.Date(default=fields.Date.today)

    # Material availability metrics
    material_availability_rate = fields.Float(
        string='Material Availability Rate (%)',
        compute='_compute_material_availability'
    )
    average_reservation_time = fields.Float(
        string='Average Reservation Time (hours)'
    )
    stock_out_count = fields.Integer(string='Stock Out Count')

    # Consumption accuracy
    planned_vs_actual_consumption = fields.Float(
        string='Planned vs Actual Consumption Deviation (%)'
    )
    scrap_rate = fields.Float(string='Scrap Rate (%)')

    @api.depends('production_id.move_raw_ids')
    def _compute_material_availability(self):
        for metric in self:
            total_moves = len(metric.production_id.move_raw_ids)
            if total_moves > 0:
                available_moves = len(metric.production_id.move_raw_ids.filtered(
                    lambda m: m.state == 'assigned'
                ))
                metric.material_availability_rate = (available_moves / total_moves) * 100
            else:
                metric.material_availability_rate = 0
```

## 🛒 Purchase Module Integration

### 🔗 Make-or-Buy Decision Engine

```python
class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def _analyze_make_or_buy(self):
        """Phân tích quyết định sản xuất hay mua"""
        self.ensure_one()

        make_or_buy_analysis = {
            'decision': 'make',  # Default: produce in-house
            'factors': {},
            'recommendations': []
        }

        # Factor 1: Production capacity availability
        capacity_analysis = self._analyze_production_capacity()
        make_or_buy_analysis['factors']['capacity'] = capacity_analysis

        # Factor 2: Supplier capability and lead time
        supplier_analysis = self._analyze_supplier_capability()
        make_or_buy_analysis['factors']['supplier'] = supplier_analysis

        # Factor 3: Cost comparison
        cost_analysis = self._analyze_production_vs_purchase_cost()
        make_or_buy_analysis['factors']['cost'] = cost_analysis

        # Factor 4: Quality requirements
        quality_analysis = self._analyze_quality_requirements()
        make_or_buy_analysis['factors']['quality'] = quality_analysis

        # Make decision
        decision_score = self._calculate_make_or_buy_score(make_or_buy_analysis)
        make_or_buy_analysis['decision'] = 'buy' if decision_score < 0.5 else 'make'

        # Generate recommendations
        make_or_buy_analysis['recommendations'] = self._generate_make_or_buy_recommendations(
            make_or_buy_analysis
        )

        return make_or_buy_analysis

    def _analyze_production_capacity(self):
        """Phân tích năng lực sản xuất"""
        workcenters_needed = self.bom_id.routing_id.operation_ids.mapped('workcenter_id')

        capacity_data = []
        for workcenter in workcenters_needed:
            # Calculate required time for this production
            operation_time = self._calculate_operation_time(workcenter)

            # Check available capacity
            available_capacity = workcenter._get_available_capacity(
                self.date_planned_start,
                self.date_planned_start + timedelta(days=7)
            )

            utilization_rate = operation_time / available_capacity if available_capacity > 0 else 1

            capacity_data.append({
                'workcenter': workcenter.name,
                'required_time': operation_time,
                'available_capacity': available_capacity,
                'utilization_rate': utilization_rate,
                'has_capacity': utilization_rate <= 0.8  # 80% threshold
            })

        return {
            'has_sufficient_capacity': all(data['has_capacity'] for data in capacity_data),
            'bottleneck_workcenter': max(capacity_data, key=lambda x: x['utilization_rate']),
            'capacity_details': capacity_data
        }

    def _analyze_supplier_capability(self):
        """Phân tích năng lực nhà cung cấp"""
        suppliers = self.product_id.seller_ids

        if not suppliers:
            return {
                'has_capable_suppliers': False,
                'message': 'Không có nhà cung cấp cho sản phẩm này'
            }

        supplier_analysis = []
        for seller in self.product_id.seller_ids:
            # Check supplier's current workload
            supplier_load = seller.name._calculate_current_workload()

            # Check supplier's quality rating
            quality_rating = seller.name._get_quality_rating()

            # Calculate supplier reliability score
            reliability_score = self._calculate_supplier_reliability(seller)

            supplier_analysis.append({
                'supplier': seller.name.name,
                'min_qty': seller.min_qty,
                'price': seller.price,
                'delay': seller.delay,
                'current_load': supplier_load,
                'quality_rating': quality_rating,
                'reliability_score': reliability_score,
                'can_meet_deadline': seller.delay <= self._calculate_available_production_time()
            })

        best_supplier = max(supplier_analysis, key=lambda x: x['reliability_score'])

        return {
            'has_capable_suppliers': any(data['can_meet_deadline'] for data in supplier_analysis),
            'best_supplier': best_supplier,
            'supplier_details': supplier_analysis
        }
```

### 📦 Automated Purchase Requisition

```python
class PurchaseRequisitionGenerator(models.Model):
    _name = 'purchase.requisition.generator'
    _description = 'Purchase Requisition Generator for MRP'

    @api.model
    def generate_from_mrp(self, production_ids):
        """Tự động tạo purchase requisition từ MRP analysis"""
        productions = self.env['mrp.production'].browse(production_ids)

        for production in productions:
            # Run make-or-buy analysis
            analysis = production._analyze_make_or_buy()

            if analysis['decision'] == 'buy':
                self._create_purchase_requisition(production, analysis)

    def _create_purchase_requisition(self, production, analysis):
        """Tạo purchase requisition"""
        best_supplier = analysis['factors']['supplier']['best_supplier']

        requisition_vals = {
            'ordering_date': fields.Date.today(),
            'origin': production.name,
            'company_id': production.company_id.id,
            'user_id': self.env.user.id,
            'state': 'draft',
            'line_ids': [(0, 0, {
                'product_id': production.product_id.id,
                'product_qty': production.product_qty,
                'product_uom_id': production.product_uom_id.id,
                'price_unit': best_supplier['price'],
                'schedule_date': production.date_planned_start,
                'supplier_id': best_supplier['supplier'],
            })]
        }

        requisition = self.env['purchase.requisition'].create(requisition_vals)

        # Update production with purchase reference
        production.write({
            'purchase_requisition_id': requisition.id,
            'make_or_buy_decision': 'buy'
        })

        return requisition
```

### 🔄 Supplier Integration for Raw Materials

```python
class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    def _check_raw_material_availability(self, production_qty=1):
        """Kiểm tra availability của nguyên vật liệu và tạo purchase suggestions"""
        availability_report = {
            'available_materials': [],
            'shortage_materials': [],
            'purchase_suggestions': []
        }

        for bom_line in self.bom_line_ids:
            required_qty = bom_line.product_qty * production_qty

            # Check current stock
            current_stock = bom_line.product_id._get_current_stock()

            # Check incoming shipments
            incoming_qty = bom_line.product_id._get_incoming_quantity()

            total_available = current_stock + incoming_qty

            if total_available >= required_qty:
                availability_report['available_materials'].append({
                    'product': bom_line.product_id.name,
                    'required_qty': required_qty,
                    'available_qty': total_available,
                    'shortage_qty': 0
                })
            else:
                shortage_qty = required_qty - total_available
                availability_report['shortage_materials'].append({
                    'product': bom_line.product_id.name,
                    'required_qty': required_qty,
                    'available_qty': total_available,
                    'shortage_qty': shortage_qty
                })

                # Generate purchase suggestion
                purchase_suggestion = self._generate_purchase_suggestion(
                    bom_line.product_id,
                    shortage_qty
                )
                availability_report['purchase_suggestions'].append(purchase_suggestion)

        return availability_report

    def _generate_purchase_suggestion(self, product, shortage_qty):
        """Tạo purchase suggestion cho nguyên vật liệu thiếu"""
        # Get best supplier for this product
        best_seller = product._get_best_supplier()

        if not best_seller:
            return {
                'product': product.name,
                'shortage_qty': shortage_qty,
                'supplier_available': False,
                'message': 'Không có nhà cung cấp cho sản phẩm này'
            }

        # Calculate optimal purchase quantity (considering min order qty)
        optimal_qty = max(shortage_qty, best_seller.min_qty)

        return {
            'product': product.name,
            'shortage_qty': shortage_qty,
            'suggested_purchase_qty': optimal_qty,
            'supplier': best_seller.name.name,
            'supplier_price': best_seller.price,
            'lead_time': best_seller.delay,
            'estimated_delivery': fields.Date.today() + timedelta(days=best_seller.delay),
            'supplier_available': True
        }
```

## 🛍️ Sales Module Integration

### 🔗 Make-to-Order Integration

```python
class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    sale_order_id = fields.Many2one('sale.order', string='Sales Order')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sales Order Line')

    @api.model
    def create_from_sale_order(self, sale_order_line):
        """Tạo production order từ sales order (Make-to-Order)"""
        product = sale_order_line.product_id

        # Check if product is manufactured
        if not product.bom_ids:
            raise ValidationError(_('Sản phẩm này không có BOM để sản xuất'))

        # Get appropriate BOM
        bom = product.bom_ids[0]  # Could be enhanced with BOM selection logic

        # Calculate production quantity
        production_qty = sale_order_line.product_uom_qty

        # Create production order
        production_vals = {
            'product_id': product.id,
            'product_qty': production_qty,
            'product_uom_id': sale_order_line.product_uom.id,
            'bom_id': bom.id,
            'sale_order_id': sale_order_line.order_id.id,
            'sale_order_line_id': sale_order_line.id,
            'origin': sale_order_line.order_id.name,
            'date_planned_start': sale_order_line.order_id.commitment_date or fields.Date.today(),
            'company_id': sale_order_line.order_id.company_id.id,
        }

        production = self.create(production_vals)

        # Reserve materials immediately for critical orders
        if sale_order_line.order_id.priority == '2':  # High priority
            production.action_confirm()

        return production

    def action_done(self):
        """Override để cập nhật sales order khi production hoàn thành"""
        result = super().action_done()

        # Update sales order line delivery status
        if self.sale_order_line_id:
            self.sale_order_line_id._update_production_status()

        # Create delivery order for finished goods
        if self.sale_order_id:
            self._create_delivery_order()

        return result

    def _create_delivery_order(self):
        """Tạo delivery order cho finished goods"""
        self.ensure_one()

        if not self.sale_order_id:
            return

        # Create stock picking for delivery
        picking_vals = {
            'partner_id': self.sale_order_id.partner_id.id,
            'origin': self.name,
            'location_id': self.product_id.property_stock_production.id,
            'location_dest_id': self.sale_order_id.partner_id.property_stock_customer.id,
            'picking_type_id': self.env['stock.picking.type'].search([
                ('code', '=', 'outgoing'),
                ('warehouse_id.company_id', '=', self.company_id.id)
            ], limit=1).id,
            'move_type': 'direct',
            'company_id': self.company_id.id,
        }

        picking = self.env['stock.picking'].create(picking_vals)

        # Create stock move for finished goods
        move_vals = {
            'name': self.product_id.name,
            'product_id': self.product_id.id,
            'product_uom_qty': self.product_qty,
            'product_uom': self.product_uom_id.id,
            'location_id': self.product_id.property_stock_production.id,
            'location_dest_id': self.sale_order_id.partner_id.property_stock_customer.id,
            'picking_id': picking.id,
            'location_usage': 'customer',
            'production_id': self.id,
        }

        self.env['stock.move'].create(move_vals)

        return picking
```

### 📊 Available-to-Promise (ATP) Calculation

```python
class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _get_atp_quantity(self):
        """Tính Available-to-Promise quantity cho sản phẩm"""
        product = self.product_id

        # Current stock quantity
        current_stock = product._get_current_stock()

        # Incoming from production orders
        incoming_production = product._get_incoming_production_quantity()

        # Incoming from purchase orders
        incoming_purchase = product._get_incoming_purchase_quantity()

        # Reserved for other sales orders
        reserved_quantity = product._get_reserved_quantity()

        atp_quantity = (
            current_stock +
            incoming_production +
            incoming_purchase -
            reserved_quantity
        )

        return max(0, atp_quantity)

    def _calculate_delivery_date(self):
        """Tính toán ngày giao hàng khả thi"""
        if not self.product_id:
            return False

        # Check if product is manufactured
        if self.product_id.bom_ids:
            return self._calculate_made_to_order_delivery_date()
        else:
            return self._calculate_purchased_product_delivery_date()

    def _calculate_made_to_order_delivery_date(self):
        """Tính delivery date cho sản phẩm sản xuất (Make-to-Order)"""
        product = self.product_id

        # Get manufacturing lead time
        bom = product.bom_ids[0]
        manufacturing_lead_time = self._calculate_manufacturing_lead_time(bom)

        # Check material availability
        material_availability_date = self._check_material_availability_date()

        # Calculate earliest delivery date
        current_date = fields.Date.today()
        delivery_date = max(
            current_date + timedelta(days=manufacturing_lead_time),
            material_availability_date,
            self.order_id.commitment_date or current_date
        )

        return delivery_date

    def _calculate_manufacturing_lead_time(self, bom):
        """Tính toán manufacturing lead time"""
        total_time = 0

        for operation in bom.routing_id.operation_ids:
            # Get workcenter
            workcenter = operation.workcenter_id

            # Calculate operation time
            if operation.time_mode == 'manual':
                operation_time = operation.time_cycle_manual
            else:
                operation_time = operation.time_cycle

            # Add setup time and queue time
            total_time += (
                operation_time +
                workcenter.time_start +
                workcenter.time_stop +
                workcenter.time_efficiency * 0.1  # Queue time estimation
            )

        return max(1, int(total_time))  # Minimum 1 day
```

### 🔄 Backorder Management

```python
class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def action_generate_backorder(self):
        """Tạo backorder khi không đủ nguyên vật liệu"""
        backorders = []

        for production in self:
            # Check which materials are unavailable
            unavailable_moves = production.move_raw_ids.filtered(
                lambda m: m.state not in ['assigned', 'done']
            )

            if unavailable_moves:
                # Calculate available quantity
                available_qty = min(
                    move.product_uom_qty
                    for move in production.move_raw_ids
                    if move.state in ['assigned', 'done']
                )

                if available_qty > 0:
                    # Split production order
                    backorder = production._split_production_order(available_qty)
                    backorders.append(backorder)

                    # Update current production quantity
                    production.product_qty = available_qty

        return backorders

    def _split_production_order(self, available_qty):
        """Chia production order thành partial và backorder"""
        self.ensure_one()

        # Calculate backorder quantity
        backorder_qty = self.product_qty - available_qty

        # Create backorder
        backorder_vals = {
            'product_id': self.product_id.id,
            'product_qty': backorder_qty,
            'product_uom_id': self.product_uom_id.id,
            'bom_id': self.bom_id.id,
            'origin': f'{self.origin} - BACKORDER',
            'date_planned_start': self.date_planned_start + timedelta(days=7),  # One week later
            'company_id': self.company_id.id,
            'user_id': self.user_id.id,
        }

        backorder = self.create(backorder_vals)

        # Update current production
        self.product_qty = available_qty

        return backorder
```

## 💰 Accounting Module Integration

### 🔗 Production Costing Integration

```python
class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    # Cost fields
    total_material_cost = fields.Float(
        string='Total Material Cost',
        compute='_compute_total_cost',
        store=True
    )
    total_operation_cost = fields.Float(
        string='Total Operation Cost',
        compute='_compute_total_cost',
        store=True
    )
    total_overhead_cost = fields.Float(
        string='Total Overhead Cost',
        compute='_compute_total_cost',
        store=True
    )
    total_production_cost = fields.Float(
        string='Total Production Cost',
        compute='_compute_total_cost',
        store=True
    )
    unit_cost = fields.Float(
        string='Unit Cost',
        compute='_compute_unit_cost',
        store=True
    )

    cost_line_ids = fields.One2many(
        'mrp.production.cost.line',
        'production_id',
        string='Cost Lines'
    )

    @api.depends('move_raw_ids', 'workorder_ids', 'cost_line_ids')
    def _compute_total_cost(self):
        for production in self:
            # Material cost
            material_cost = sum(
                line.product_id.standard_price * line.product_uom_qty
                for line in production.move_raw_ids
                if line.state == 'done'
            )

            # Operation cost
            operation_cost = sum(
                wo.time_duration * wo.workcenter_id.costs_hour / 60
                for wo in production.workorder_ids
                if wo.state == 'done'
            )

            # Overhead cost from cost lines
            overhead_cost = sum(
                line.total_cost
                for line in production.cost_line_ids
                if line.cost_type == 'overhead'
            )

            production.total_material_cost = material_cost
            production.total_operation_cost = operation_cost
            production.total_overhead_cost = overhead_cost
            production.total_production_cost = material_cost + operation_cost + overhead_cost

    @api.depends('total_production_cost', 'product_qty')
    def _compute_unit_cost(self):
        for production in self:
            if production.product_qty > 0:
                production.unit_cost = production.total_production_cost / production.product_qty
            else:
                production.unit_cost = 0

    def action_done(self):
        """Override để tạo accounting entries khi production hoàn thành"""
        result = super().action_done()

        # Generate accounting entries
        self._create_production_accounting_entries()

        # Update product cost
        self._update_product_standard_cost()

        return result

    def _create_production_accounting_entries(self):
        """Tạo accounting entries cho production cost"""
        self.ensure_one()

        # Create journal entries for material consumption
        self._create_material_consumption_entries()

        # Create journal entries for operation costs
        self._create_operation_cost_entries()

        # Create journal entry for finished goods
        self._create_finished_goods_entries()

    def _create_material_consumption_entries(self):
        """Tạo accounting entries cho tiêu thụ nguyên vật liệu"""
        for move in self.move_raw_ids:
            if move.state != 'done':
                continue

            # Get expense account for material
            expense_account = move.product_id.categ_id.property_stock_account_input_categ_id

            if not expense_account:
                raise ValidationError(_('Chưa cấu hình tài khoản chi phí cho %s') % move.product_id.name)

            # Create journal entry
            move_vals = {
                'name': f'Consumption: {self.name}',
                'date': fields.Date.today(),
                'journal_id': self.env['account.journal'].search([
                    ('type', '=', 'general'),
                    ('company_id', '=', self.company_id.id)
                ], limit=1).id,
                'line_ids': [
                    (0, 0, {
                        'account_id': expense_account.id,
                        'debit': move.product_id.standard_price * move.product_uom_qty,
                        'credit': 0,
                        'product_id': move.product_id.id,
                        'quantity': move.product_uom_qty,
                        'name': move.name,
                    }),
                    (0, 0, {
                        'account_id': move.product_id.categ_id.property_stock_valuation_account_id.id,
                        'debit': 0,
                        'credit': move.product_id.standard_price * move.product_uom_qty,
                        'product_id': move.product_id.id,
                        'quantity': -move.product_uom_qty,
                        'name': move.name,
                    })
                ]
            }

            self.env['account.move'].create(move_vals)

    def _create_finished_goods_entries(self):
        """Tạo accounting entries cho thành phẩm"""
        self.ensure_one()

        # Get accounts
        fg_account = self.product_id.categ_id.property_stock_valuation_account_id
        wip_account = self.env['account.account'].search([
            ('code', '=', 'wip_production')  # Work in Process account
        ], limit=1)

        if not fg_account or not wip_account:
            raise ValidationError(_('Chưa cấu hình tài khoản WIP hoặc thành phẩm'))

        # Create journal entry
        move_vals = {
            'name': f'Production Completion: {self.name}',
            'date': fields.Date.today(),
            'journal_id': self.env['account.journal'].search([
                ('type', '=', 'general'),
                ('company_id', '=', self.company_id.id)
            ], limit=1).id,
            'line_ids': [
                (0, 0, {
                    'account_id': fg_account.id,
                    'debit': self.total_production_cost,
                    'credit': 0,
                    'product_id': self.product_id.id,
                    'quantity': self.product_qty,
                    'name': self.name,
                }),
                (0, 0, {
                    'account_id': wip_account.id,
                    'debit': 0,
                    'credit': self.total_production_cost,
                    'product_id': self.product_id.id,
                    'quantity': -self.product_qty,
                    'name': self.name,
                })
            ]
        }

        self.env['account.move'].create(move_vals)
```

### 📊 Real-time Cost Tracking

```python
class MrpProductionCostLine(models.Model):
    _name = 'mrp.production.cost.line'
    _description = 'Production Cost Line'
    _order = 'create_date desc'

    production_id = fields.Many2one('mrp.production', string='Production Order')
    cost_type = fields.Selection([
        ('material', 'Material Cost'),
        ('operation', 'Operation Cost'),
        ('overhead', 'Overhead Cost'),
        ('external', 'External Operation Cost'),
    ], string='Cost Type', required=True)

    product_id = fields.Many2one('product.product', string='Product')
    description = fields.Char(string='Description')

    quantity = fields.Float(string='Quantity')
    unit_cost = fields.Float(string='Unit Cost')
    total_cost = fields.Float(string='Total Cost', compute='_compute_total_cost', store=True)

    workorder_id = fields.Many2one('mrp.workorder', string='Work Order')
    move_id = fields.Many2one('stock.move', string='Stock Move')

    account_move_id = fields.Many2one('account.move', string='Journal Entry')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')

    create_date = fields.Datetime(default=fields.Datetime.now)
    user_id = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user)

    @api.depends('quantity', 'unit_cost')
    def _compute_total_cost(self):
        for line in self:
            line.total_cost = line.quantity * line.unit_cost

    def _generate_journal_entry(self):
        """Tạo journal entry cho cost line này"""
        if self.cost_type == 'material':
            self._generate_material_journal_entry()
        elif self.cost_type == 'operation':
            self._generate_operation_journal_entry()
        elif self.cost_type == 'overhead':
            self._generate_overhead_journal_entry()
```

### 🔄 Variance Analysis

```python
class MrpProductionVariance(models.Model):
    _name = 'mrp.production.variance'
    _description = 'Production Variance Analysis'

    production_id = fields.Many2one('mrp.production', string='Production Order')

    # Standard vs Actual costs
    standard_material_cost = fields.Float(string='Standard Material Cost')
    actual_material_cost = fields.Float(string='Actual Material Cost')
    material_variance = fields.Float(string='Material Variance', compute='_compute_variances')

    standard_operation_cost = fields.Float(string='Standard Operation Cost')
    actual_operation_cost = fields.Float(string='Actual Operation Cost')
    operation_variance = fields.Float(string='Operation Variance', compute='_compute_variances')

    standard_quantity = fields.Float(string='Standard Quantity')
    actual_quantity = fields.Float(string='Actual Quantity')
    quantity_variance = fields.Float(string='Quantity Variance', compute='_compute_variances')

    total_variance = fields.Float(string='Total Variance', compute='_compute_variances')
    variance_percentage = fields.Float(string='Variance Percentage', compute='_compute_variance_percentage')

    @api.depends('standard_material_cost', 'actual_material_cost',
                 'standard_operation_cost', 'actual_operation_cost')
    def _compute_variances(self):
        for variance in self:
            variance.material_variance = variance.actual_material_cost - variance.standard_material_cost
            variance.operation_variance = variance.actual_operation_cost - variance.standard_operation_cost
            variance.quantity_variance = variance.actual_quantity - variance.standard_quantity
            variance.total_variance = (
                variance.material_variance +
                variance.operation_variance
            )

    def _compute_variance_percentage(self):
        for variance in self:
            standard_total = variance.standard_material_cost + variance.standard_operation_cost
            if standard_total > 0:
                variance.variance_percentage = (variance.total_variance / standard_total) * 100
            else:
                variance.variance_percentage = 0

    @api.model
    def analyze_production_variance(self, production_id):
        """Phân tích variance cho production order"""
        production = self.env['mrp.production'].browse(production_id)

        # Calculate standard costs
        standard_costs = production._calculate_standard_costs()

        # Get actual costs from production
        actual_costs = {
            'material': production.total_material_cost,
            'operation': production.total_operation_cost,
            'quantity': production.product_qty
        }

        # Create variance record
        variance_vals = {
            'production_id': production.id,
            'standard_material_cost': standard_costs['material'],
            'actual_material_cost': actual_costs['material'],
            'standard_operation_cost': standard_costs['operation'],
            'actual_operation_cost': actual_costs['operation'],
            'standard_quantity': production.product_qty,  # Standard = planned
            'actual_quantity': actual_costs['quantity'],
        }

        variance = self.create(variance_vals)

        # Generate variance analysis report
        variance._generate_variance_report()

        return variance
```

## 🔗 Quality Module Integration

### 🔗 Quality Control in Production

```python
class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    quality_point_ids = fields.One2many(
        'quality.point',
        'workorder_id',
        string='Quality Points'
    )
    quality_check_ids = fields.One2many(
        'quality.check',
        'workorder_id',
        string='Quality Checks'
    )

    def button_start(self):
        """Bắt đầu workorder với quality checks"""
        result = super().button_start()

        # Generate quality checks for this workorder
        self._generate_quality_checks()

        return result

    def button_finish(self):
        """Kết thúc workorder với final quality validation"""
        # Check if all quality checks are passed
        if not self._validate_quality_checks():
            raise ValidationError(_('Chưa hoàn thành tất cả quality checks'))

        result = super().button_finish()

        # Update quality metrics
        self._update_quality_metrics()

        return result

    def _generate_quality_checks(self):
        """Tạo quality checks dựa trên quality points"""
        for quality_point in self.quality_point_ids:
            # Create quality check for each point
            check_vals = {
                'workorder_id': self.id,
                'production_id': self.production_id.id,
                'point_id': quality_point.id,
                'product_id': self.production_id.product_id.id,
                'company_id': self.company_id.id,
                'user_id': self.env.user.id,
                'state': 'todo',
            }

            self.env['quality.check'].create(check_vals)

    def _validate_quality_checks(self):
        """Validate tất cả quality checks"""
        pending_checks = self.quality_check_ids.filtered(lambda c: c.state != 'pass')

        if pending_checks:
            failed_checks = pending_checks.filtered(lambda c: c.state == 'fail')
            if failed_checks:
                # Trigger quality alert
                self._create_quality_alert(failed_checks)

            return len(pending_checks) == 0

        return True

    def _create_quality_alert(self, failed_checks):
        """Tạo quality alert khi có failed checks"""
        alert_vals = {
            'production_id': self.production_id.id,
            'workorder_id': self.id,
            'alert_type': 'quality_failure',
            'description': f'Quality check failed: {", ".join(failed_checks.mapped("point_id.name"))}',
            'severity': 'high',
            'user_id': self.env.user.id,
            'company_id': self.company_id.id,
        }

        self.env['quality.alert'].create(alert_vals)
```

### 📊 Quality Metrics Integration

```python
class QualityMetrics(models.Model):
    _name = 'quality.metrics'
    _description = 'Production Quality Metrics'

    production_id = fields.Many2one('mrp.production', string='Production Order')
    workorder_id = fields.Many2one('mrp.workorder', string='Work Order')

    # Quality KPIs
    first_pass_yield = fields.Float(string='First Pass Yield (%)')
    rework_rate = fields.Float(string='Rework Rate (%)')
    scrap_rate = fields.Float(string='Scrap Rate (%)')
    defect_rate = fields.Float(string='Defect Rate (ppm)')

    # Quality control metrics
    total_checks = fields.Integer(string='Total Quality Checks')
    passed_checks = fields.Integer(string='Passed Checks')
    failed_checks = fields.Integer(string='Failed Checks')

    measurement_date = fields.Date(default=fields.Date.today)

    @api.model
    def calculate_production_quality_metrics(self, production_id):
        """Tính toán quality metrics cho production order"""
        production = self.env['mrp.production'].browse(production_id)

        # Get all workorders for this production
        workorders = production.workorder_ids

        total_checks = 0
        passed_checks = 0
        failed_checks = 0
        total_qty = 0
        scrap_qty = 0
        rework_qty = 0

        for workorder in workorders:
            # Get quality checks for this workorder
            checks = workorder.quality_check_ids

            total_checks += len(checks)
            passed_checks += len(checks.filtered(lambda c: c.state == 'pass'))
            failed_checks += len(checks.filtered(lambda c: c.state == 'fail'))

            # Get scrap and rework quantities
            total_qty += workorder.qty_produced
            scrap_qty += workorder.scrap_count
            rework_qty += sum(wo.qty_produced for wo in workorder.rework_order_ids)

        # Calculate metrics
        first_pass_yield = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        rework_rate = (rework_qty / total_qty * 100) if total_qty > 0 else 0
        scrap_rate = (scrap_qty / total_qty * 100) if total_qty > 0 else 0
        defect_rate = (failed_checks / total_qty * 1000000) if total_qty > 0 else 0  # Parts per million

        # Create or update metrics record
        metrics_vals = {
            'production_id': production.id,
            'first_pass_yield': first_pass_yield,
            'rework_rate': rework_rate,
            'scrap_rate': scrap_rate,
            'defect_rate': defect_rate,
            'total_checks': total_checks,
            'passed_checks': passed_checks,
            'failed_checks': failed_checks,
            'measurement_date': fields.Date.today(),
        }

        return self.create(metrics_vals)
```

## 📈 Performance Optimization Integration

### 🔗 Real-time Production Dashboard

```python
class ProductionDashboard(models.Model):
    _name = 'production.dashboard'
    _description = 'Real-time Production Dashboard'

    @api.model
    def get_production_metrics(self):
        """Lấy real-time production metrics"""
        today = fields.Date.today()

        # Current active productions
        active_productions = self.env['mrp.production'].search([
            ('state', 'in', ['confirmed', 'progress']),
            ('company_id', '=', self.env.company.id)
        ])

        # OEE calculation
        oee_metrics = self._calculate_oee_metrics(active_productions)

        # Throughput metrics
        throughput_metrics = self._calculate_throughput_metrics()

        # Quality metrics
        quality_metrics = self._calculate_quality_metrics()

        # Cost metrics
        cost_metrics = self._calculate_cost_metrics(active_productions)

        return {
            'oee': oee_metrics,
            'throughput': throughput_metrics,
            'quality': quality_metrics,
            'cost': cost_metrics,
            'active_productions': len(active_productions),
            'last_updated': fields.Datetime.now(),
        }

    def _calculate_oee_metrics(self, productions):
        """Tính toán Overall Equipment Effectiveness"""
        total_available_time = 0
        total_planned_time = 0
        total_actual_time = 0
        total_produced_qty = 0
        total_target_qty = 0
        total_good_qty = 0

        for production in productions:
            for workorder in production.workorder_ids:
                # Availability
                available_time = workorder._get_available_time()
                planned_time = workorder.duration_expected
                actual_time = workorder.time_duration

                total_available_time += available_time
                total_planned_time += planned_time
                total_actual_time += actual_time

                # Performance
                produced_qty = workorder.qty_produced
                target_qty = workorder.qty_producing
                ideal_cycle_time = workorder.workcenter_id.time_cycle / 60  # Convert to hours

                total_produced_qty += produced_qty
                total_target_qty += target_qty

                # Quality
                good_qty = produced_qty - workorder.scrap_count
                total_good_qty += good_qty

        # Calculate OEE components
        availability = (total_planned_time / total_available_time * 100) if total_available_time > 0 else 0
        performance = ((total_produced_qty * total_actual_time) / (total_target_qty * total_planned_time) * 100) if total_planned_time > 0 else 0
        quality = (total_good_qty / total_produced_qty * 100) if total_produced_qty > 0 else 0

        oee = (availability * performance * quality) / 10000  # Divide by 100 twice

        return {
            'availability': availability,
            'performance': performance,
            'quality': quality,
            'oee': oee,
            'target_oee': 85.0,  # Industry standard
            'oee_status': 'good' if oee >= 75 else 'poor' if oee >= 50 else 'critical'
        }
```

### 🔄 Predictive Maintenance Integration

```python
class MaintenancePredictor(models.Model):
    _name = 'maintenance.predictor'
    _description = 'Predictive Maintenance for Production'

    @api.model
    def predict_maintenance_needs(self, workcenter_id, days_ahead=7):
        """Dự đoán nhu cầu bảo trì cho workcenter"""
        workcenter = self.env['mrp.workcenter'].browse(workcenter_id)

        # Get historical maintenance data
        maintenance_history = workcenter._get_maintenance_history()

        # Get current production schedule
        upcoming_workorders = workcenter._get_upcoming_workorders(days_ahead)

        # Calculate production load
        production_load = sum(wo.duration_expected for wo in upcoming_workorders)

        # Get workcenter health metrics
        health_metrics = workcenter._get_health_metrics()

        # Predictive model (simplified)
        maintenance_probability = self._calculate_maintenance_probability(
            maintenance_history,
            production_load,
            health_metrics
        )

        return {
            'workcenter': workcenter.name,
            'maintenance_probability': maintenance_probability,
            'recommended_action': self._get_recommended_action(maintenance_probability),
            'production_load_hours': production_load,
            'health_score': health_metrics['score'],
            'last_maintenance': health_metrics['last_maintenance'],
            'predicted_next_maintenance': self._predict_next_maintenance_date(
                maintenance_history,
                maintenance_probability
            ),
        }

    def _calculate_maintenance_probability(self, history, load, health):
        """Tính toán xác suất cần bảo trì"""
        # Base probability from time since last maintenance
        days_since_maintenance = (fields.Date.today() - health['last_maintenance']).days
        time_probability = min(days_since_maintenance / 90, 1.0)  # Normalize to 90-day cycle

        # Load probability
        load_probability = min(load / 500, 1.0)  # 500 hours threshold

        # Health probability
        health_probability = 1 - (health['score'] / 100)

        # Weighted average
        maintenance_probability = (
            time_probability * 0.4 +
            load_probability * 0.3 +
            health_probability * 0.3
        )

        return min(maintenance_probability, 1.0)
```

## 🔍 Error Handling & Recovery Patterns

### 🔗 Production Error Management

```python
class ProductionErrorHandler(models.Model):
    _name = 'production.error.handler'
    _description = 'Production Error Handler'

    @api.model
    def handle_production_error(self, production_id, error_type, error_details):
        """Xử lý production errors với recovery patterns"""
        production = self.env['mrp.production'].browse(production_id)

        # Log the error
        error_log = self._create_error_log(production, error_type, error_details)

        # Determine recovery strategy
        recovery_strategy = self._determine_recovery_strategy(error_type, error_details)

        # Execute recovery actions
        recovery_result = self._execute_recovery_strategy(production, recovery_strategy)

        # Update production status
        production._update_error_status(error_log, recovery_result)

        # Send notifications
        self._send_error_notifications(error_log, recovery_result)

        return {
            'error_log_id': error_log.id,
            'recovery_strategy': recovery_strategy,
            'recovery_result': recovery_result,
            'production_status': production.state,
        }

    def _determine_recovery_strategy(self, error_type, error_details):
        """Xác định chiến lược phục hồi"""
        strategies = {
            'material_shortage': {
                'actions': ['check_alternative_materials', 'generate_purchase_request', 'schedule_backorder'],
                'severity': 'medium',
                'estimated_recovery_time': 4  # hours
            },
            'equipment_failure': {
                'actions': ['schedule_maintenance', 'reassign_workorder', 'adjust_production_schedule'],
                'severity': 'high',
                'estimated_recovery_time': 24  # hours
            },
            'quality_failure': {
                'actions': ['quarantine_production', 'root_cause_analysis', 'implement_corrective_action'],
                'severity': 'high',
                'estimated_recovery_time': 8  # hours
            },
            'capacity_constraint': {
                'actions': ['rebalance_workload', 'outsource_production', 'adjust_delivery_dates'],
                'severity': 'medium',
                'estimated_recovery_time': 16  # hours
            }
        }

        return strategies.get(error_type, {
            'actions': ['manual_intervention'],
            'severity': 'unknown',
            'estimated_recovery_time': 8
        })
```

## 📚 Best Practices Summary

### ✅ **Integration Excellence Checklist**

#### **Inventory Integration** ✅
- [x] Real-time material reservation system
- [x] Automated stock movement generation
- [x] Multi-warehouse material management
- [x] Material consumption tracking
- [x] Backorder creation for shortages

#### **Purchase Integration** ✅
- [x] Make-or-buy decision engine
- [x] Automated purchase requisition
- [x] Supplier capability analysis
- [x] Raw material shortage detection
- [x] Cost comparison analysis

#### **Sales Integration** ✅
- [x] Make-to-order production from sales
- [x] Available-to-Promise calculation
- [x] Delivery date estimation
- [x] Backorder management
- [x] Automatic delivery order creation

#### **Accounting Integration** ✅
- [x] Real-time production costing
- [x] Material consumption journal entries
- [x] Work in process valuation
- [x] Finished goods valuation
- [x] Variance analysis and reporting

#### **Quality Integration** ✅
- [x] Quality point definition
- [x] Automated quality check generation
- [x] Quality metrics tracking
- [x] Quality alert system
- [x] First pass yield monitoring

### 🚀 **Performance Optimization Patterns**

#### **Real-time Data Synchronization**
- Use database triggers for critical inventory updates
- Implement message queues for async processing
- Cache frequently accessed data
- Batch non-critical updates

#### **Scalable Integration Architecture**
- Modular integration components
- API-first approach for external systems
- Event-driven architecture for real-time updates
- Graceful degradation patterns

#### **Error Recovery Mechanisms**
- Automatic retry logic for transient errors
- Manual intervention workflows
- Error logging and monitoring
- Rollback capabilities

---

**Module Status**: ✅ **COMPLETED**
**File Size**: ~10,000 từ
**Language**: Tiếng Việt
**Focus**: Integration patterns và real-time synchronization
**Target Audience**: Technical Architects, Integration Specialists
**Completion**: 2025-11-08

*File này cung cấp comprehensive integration patterns cho Manufacturing Module, đảm bảo seamless integration với toàn bộ supply chain ecosystem của Odoo 18.*