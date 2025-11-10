# 🚀 Best Practices & Optimization Guidelines - Manufacturing Module

## 🎯 Giới Thiệu

Best Practices documentation này cung cấp hướng dẫn toàn diện cho việc triển khai, tối ưu và bảo trì Manufacturing Module Odoo 18 trong môi trường sản xuất thực tế. Tài liệu bao gồm các patterns, chiến lược và kỹ thuật đã được chứng minh hiệu quả qua nhiều dự án thực tế.

## 📚 Development Best Practices

### 1. Customization Patterns cho Production Workflows

#### ✅ Pattern 1: Custom State Management với Approval Workflow

```python
class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    # Custom states cho approval workflow
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_approval', 'Chờ Duyệt'),
        ('approved', 'Đã Duyệt'),
        ('confirmed', 'Confirmed'),
        ('planned', 'Planned'),
        ('progress', 'In Progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', required=True, tracking=True)

    approval_user_id = fields.Many2one(
        'res.users',
        string='Người Duyệt',
        tracking=True
    )

    approval_date = fields.Datetime(
        string='Ngày Duyệt',
        tracking=True
    )

    @api.model
    def create(self, vals):
        """Override để set approval requirements"""
        if vals.get('product_qty', 0) > 1000:  # Large quantities require approval
            vals['state'] = 'waiting_approval'
        return super().create(vals)

    def action_submit_for_approval(self):
        """Gửi yêu cầu duyệt"""
        self.write({'state': 'waiting_approval'})

        # Tạo activity cho approval user
        for production in self:
            production.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=production._get_approval_user().id,
                note=f'Lệnh sản xuất {production.name} cần duyệt'
            )

    def action_approve(self):
        """Duyệt lệnh sản xuất"""
        self.write({
            'state': 'approved',
            'approval_user_id': self.env.user.id,
            'approval_date': fields.Datetime.now()
        })

        # Gửi notification
        template = self.env.ref('mrp.email_template_production_approved')
        for production in self:
            template.send_mail(production.id)

    def _get_approval_user(self):
        """Logic để xác định user duyệt dựa trên tiêu chí"""
        # Production manager cho quantities > 1000
        # Director cho quantities > 5000
        if self.product_qty > 5000:
            return self.env.ref('manufacturing.group_production_director')
        elif self.product_qty > 1000:
            return self.env.ref('manufacturing.group_production_manager')
        return self.env.user
```

#### ✅ Pattern 2: Advanced Quality Control Integration

```python
class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    quality_check_ids = fields.One2many(
        'quality.check',
        'workorder_id',
        string='Quality Checks'
    )

    quality_score = fields.Float(
        string='Quality Score',
        compute='_compute_quality_score',
        store=True
    )

    quality_passed = fields.Boolean(
        string='Quality Passed',
        compute='_compute_quality_passed',
        store=True
    )

    @api.depends('quality_check_ids.state')
    def _compute_quality_score(self):
        """Tính quality score dựa trên kết quả checks"""
        for workorder in self:
            if not workorder.quality_check_ids:
                workorder.quality_score = 0
                continue

            total_checks = len(workorder.quality_check_ids)
            passed_checks = len(workorder.quality_check_ids.filtered(
                lambda check: check.state == 'pass'
            ))

            workorder.quality_score = (passed_checks / total_checks) * 100 if total_checks > 0 else 0

    def action_start(self):
        """Override để require quality checks trước khi bắt đầu"""
        for workorder in self:
            # Kiểm tra quality checks từ operation trước
            if workorder.operation_id.sequence > 10:
                prev_operations = workorder.production_id.workorder_ids.filtered(
                    lambda wo: wo.operation_id.sequence < workorder.operation_id.sequence
                )

                for prev_op in prev_operations:
                    if not prev_op.quality_passed:
                        raise ValidationError(
                            f'Công đoạn trước {prev_op.name} chưa đạt chất lượng'
                        )

        return super().action_start()

    def button_quality_check(self):
        """Mở quality check wizard"""
        self.ensure_one()

        # Tạo quality points dựa trên work order
        quality_points = self.operation_id.quality_point_ids
        if not quality_points:
            quality_points = self.env['quality.point'].search([
                ('product_id', '=', self.product_id.id),
                ('picking_type_id', '=', self.production_id.picking_type_id.id)
            ])

        return {
            'type': 'ir.actions.act_window',
            'name': 'Quality Check',
            'res_model': 'quality.check.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_workorder_id': self.id,
                'default_product_id': self.product_id.id,
                'default_quality_point_ids': [(6, 0, quality_points.ids)]
            }
        }
```

### 2. Performance Optimization Strategies

#### ✅ Batch Processing cho Large Productions

```python
class MrpProductionBatch(models.Model):
    _name = 'mrp.production.batch'
    _description = 'Production Batch Processing'

    name = fields.Char(string='Batch Name', required=True)
    production_ids = fields.One2many(
        'mrp.production',
        'batch_id',
        string='Productions'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('error', 'Error')
    ], default='draft')

    total_quantity = fields.Float(
        compute='_compute_totals',
        store=True
    )

    @api.depends('production_ids.product_qty')
    def _compute_totals(self):
        for batch in self:
            batch.total_quantity = sum(batch.production_ids.mapped('product_qty'))

    @api.model
    def create_batch_from_sales(self, sale_order_ids):
        """Tạo batch từ sales orders"""
        sales_orders = self.env['sale.order'].browse(sale_order_ids)

        # Group by product và bom
        product_groups = {}
        for line in sales_orders.mapped('order_line'):
            key = (line.product_id.id, line.product_uom_qty)
            if key not in product_groups:
                product_groups[key] = {
                    'product_id': line.product_id,
                    'quantity': 0,
                    'sale_lines': []
                }
            product_groups[key]['quantity'] += line.product_uom_qty
            product_groups[key]['sale_lines'].append(line.id)

        # Create productions
        productions = []
        for group_data in product_groups.values():
            bom = self.env['mrp.bom']._bom_find(
                product=group_data['product_id'],
                company_id=self.env.company.id
            )

            if bom:
                # Split into optimal batch sizes
                batch_size = bom.lot_size or 100
                remaining_qty = group_data['quantity']

                while remaining_qty > 0:
                    qty = min(remaining_qty, batch_size)

                    production = self.env['mrp.production'].create({
                        'product_id': group_data['product_id'].id,
                        'product_qty': qty,
                        'bom_id': bom.id,
                        'sale_line_ids': [(6, 0, group_data['sale_lines'])]
                    })

                    productions.append(production.id)
                    remaining_qty -= qty

        # Create batch
        batch = self.create({
            'name': f'BATCH-{fields.Date.today().strftime("%Y%m%d")}-{len(self.search([])) + 1}',
            'production_ids': [(6, 0, productions)]
        })

        return batch

    def action_process_batch(self):
        """Xử lý batch với performance optimization"""
        self.write({'state': 'processing'})

        try:
            # Process productions in parallel batches
            batch_size = 50  # Process 50 productions at a time
            productions = self.production_ids.sorted('id')

            for i in range(0, len(productions), batch_size):
                batch_productions = productions[i:i + batch_size]

                # Generate work orders in batch
                self._cr.execute("""
                    UPDATE mrp_production
                    SET state = 'confirmed'
                    WHERE id IN %s
                """, (tuple(batch_productions.ids),))

                # Trigger work order generation
                for production in batch_productions:
                    production._generate_workorders()
                    production._generate_raw_moves()

            self.write({'state': 'completed'})

        except Exception as e:
            self.write({'state': 'error'})
            raise e

    def action_confirm_all(self):
        """Confirm tất cả productions trong batch"""
        for production in self.production_ids:
            if production.state == 'draft':
                production.action_confirm()
```

#### ✅ Smart Material Reservation System

```python
class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model
    def _run_reserve(self, move_ids):
        """Enhanced reservation algorithm cho manufacturing"""
        moves = self.browse(move_ids)

        # Group by product và priority
        priority_groups = {}
        for move in moves:
            key = (move.product_id.id, move.priority)
            if key not in priority_groups:
                priority_groups[key] = self.env['stock.move']
            priority_groups[key] += move

        # Process by priority (high to low)
        for (product_id, priority), group_moves in sorted(
            priority_groups.items(),
            key=lambda x: x[0][1],
            reverse=True
        ):
            self._reserve_product_moves(group_moves, product_id)

    @staticmethod
    def _reserve_product_moves(moves, product_id):
        """Smart reservation cho specific product"""
        # Get available quants with optimal selection strategy
        available_quants = moves.env['stock.quant']._gather(
            product_id,
            moves[0].location_id,
            moves[0].company_id,
            strict=True
        )

        # Sort by expiration date (FIFO) and location efficiency
        sorted_quants = available_quants.sorted([
            lambda q: q.expiration_date or '2099-12-31',
            lambda q: q.location_id.complete_name  # Prefer closer locations
        ])

        # Reserve moves using optimal quants
        for move in moves:
            remaining_qty = move.product_uom_qty
            allocated_qty = 0

            for quant in sorted_quants:
                if remaining_qty <= 0 or allocated_qty >= move.product_uom_qty:
                    break

                reserve_qty = min(
                    quant.quantity - quant.reserved_quantity,
                    remaining_qty,
                    move.product_uom_qty - allocated_qty
                )

                if reserve_qty > 0:
                    move._update_reserved_quantity(
                        reserve_qty,
                        quant_id=quant.id,
                        negative=False
                    )
                    remaining_qty -= reserve_qty
                    allocated_qty += reserve_qty
```

### 3. Security & Access Control Implementation

#### ✅ Role-Based Manufacturing Access Control

```python
class MrpSecurity(models.AbstractModel):
    _name = 'mrp.security.mixin'
    _description = 'Manufacturing Security Mixin'

    def _check_production_access(self, operation='read'):
        """Check access rights dựa trên user roles"""
        user = self.env.user
        company_id = self.env.company.id

        # Super users have full access
        if user.has_group('base.group_system'):
            return True

        # Manufacturing managers have full access
        if user.has_group('manufacturing.group_manufacturing_manager'):
            return True

        # Check specific access patterns
        access_rules = {
            'production_planner': {
                'models': ['mrp.production', 'mrp.bom'],
                'operations': ['read', 'write'],
                'domain': [('company_id', '=', company_id)]
            },
            'production_worker': {
                'models': ['mrp.workorder'],
                'operations': ['read', 'write'],
                'domain': [
                    ('company_id', '=', company_id),
                    '|', ('user_id', '=', user.id), ('user_id', '=', False)
                ]
            },
            'quality_inspector': {
                'models': ['quality.check', 'mrp.workorder'],
                'operations': ['read', 'write'],
                'domain': [('company_id', '=', company_id)]
            }
        }

        user_roles = self._get_user_manufacturing_roles(user)

        for role in user_roles:
            if role in access_rules:
                rule = access_rules[role]
                if self._name in rule['models'] and operation in rule['operations']:
                    return self.search(rule['domain']).ids == self.ids

        return False

    def _get_user_manufacturing_roles(self, user):
        """Get user's manufacturing roles"""
        roles = []

        if user.has_group('manufacturing.group_manufacturing_user'):
            roles.append('production_worker')

        if user.has_group('manufacturing.group_mrp_user'):
            roles.append('production_planner')

        if user.has_group('quality.group_quality_user'):
            roles.append('quality_inspector')

        return roles


class MrpProduction(models.Model):
    _inherit = ['mrp.production', 'mrp.security.mixin']

    def read(self, fields=None, load='_classic_read'):
        """Override read với security check"""
        for record in self:
            if not record._check_production_access('read'):
                raise AccessError(
                    _('Bạn không có quyền xem lệnh sản xuất này')
                )
        return super().read(fields, load)

    def write(self, vals):
        """Override write với security check"""
        for record in self:
            if not record._check_production_access('write'):
                raise AccessError(
                    _('Bạn không có quyền sửa lệnh sản xuất này')
                )
        return super().write(vals)

    def unlink(self):
        """Override unlink với security check"""
        for record in self:
            if not record._check_production_access('unlink'):
                raise AccessError(
                    _('Bạn không có quyền xóa lệnh sản xuất này')
                )
        return super().unlink()
```

## 🔧 Technical Implementation Patterns

### 1. Database Schema Optimization

#### ✅ Optimized Queries cho Manufacturing Analytics

```python
class MrpAnalytics(models.AbstractModel):
    _name = 'mrp.analytics.mixin'

    def get_production_analytics(self, date_from, date_to, product_ids=None):
        """Get production analytics với optimized queries"""

        # Use SQL aggregation cho performance
        query = """
            SELECT
                DATE(mp.date_planned_start) as production_date,
                mp.product_id,
                pt.name as product_name,
                SUM(mp.product_qty) as total_produced,
                COUNT(*) as production_count,
                AVG(mp.qty_produced) as avg_actual_qty,
                SUM(mp.qty_produced - mp.product_qty) as variance_qty,
                mp.state
            FROM mrp_production mp
            JOIN product_product pp ON mp.product_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            WHERE mp.date_planned_start >= %s
            AND mp.date_planned_start <= %s
            AND mp.company_id = %s
        """

        params = [date_from, date_to, self.env.company.id]

        if product_ids:
            query += " AND mp.product_id IN %s"
            params.append(tuple(product_ids))

        query += """
            GROUP BY DATE(mp.date_planned_start), mp.product_id, pt.name, mp.state
            ORDER BY production_date DESC
        """

        self.env.cr.execute(query, params)
        return self.env.cr.dictfetchall()

    def get_workcenter_utilization(self, date_from, date_to):
        """Calculate workcenter utilization efficiency"""

        query = """
            SELECT
                wc.name as workcenter_name,
                COUNT(DISTINCT wo.id) as total_workorders,
                SUM(CASE WHEN wo.state = 'done' THEN 1 ELSE 0 END) as completed_workorders,
                SUM(wo.duration_expected) as total_expected_minutes,
                SUM(wo.duration) as total_actual_minutes,
                ROUND(
                    CASE
                        WHEN SUM(wo.duration_expected) > 0
                        THEN (SUM(wo.duration_expected) / SUM(wo.duration)) * 100
                        ELSE 0
                    END, 2
                ) as efficiency_percentage
            FROM mrp_workorder wo
            JOIN mrp_workcenter wc ON wo.workcenter_id = wc.id
            WHERE wo.date_planned_start >= %s
            AND wo.date_planned_start <= %s
            AND wo.company_id = %s
            GROUP BY wc.id, wc.name
            ORDER BY efficiency_percentage DESC
        """

        self.env.cr.execute(query, [date_from, date_to, self.env.company.id])
        return self.env.cr.dictfetchall()
```

#### ✅ Smart Indexing Strategy

```python
# migrations/13.0.1.0.0/post-migration.py
def create_manufacturing_indexes():
    """Create optimized indexes cho manufacturing tables"""

    indexes = [
        # mrp_production indexes
        """
        CREATE INDEX IF NOT EXISTS idx_mrp_production_company_state
        ON mrp_production(company_id, state, date_planned_start);
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_mrp_production_product_date
        ON mrp_production(product_id, date_planned_start);
        """,

        # mrp_workorder indexes
        """
        CREATE INDEX IF NOT EXISTS idx_mrp_workorder_production_state
        ON mrp_workorder(production_id, state, date_planned_start);
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_mrp_workorder_workcenter_date
        ON mrp_workorder(workcenter_id, date_planned_start);
        """,

        # mrp_bom indexes
        """
        CREATE INDEX IF NOT EXISTS idx_mrp_bom_product_company
        ON mrp_bom(product_tmpl_id, company_id, active);
        """,

        # stock_move indexes cho material consumption
        """
        CREATE INDEX IF NOT EXISTS idx_stock_move_production_reference
        ON stock_move(reference, state, location_id, location_dest_id);
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_stock_move_product_location
        ON stock_move(product_id, location_id, location_dest_id, state);
        """
    ]

    for index_sql in indexes:
        env.cr.execute(index_sql)
```

### 2. Caching Strategy

#### ✅ Redis Integration cho Manufacturing Data

```python
import redis
import json
import hashlib

class MrpCache(models.AbstractModel):
    _name = 'mrp.cache.mixin'

    def __init__(self, env):
        super().__init__(env)
        self._redis_client = None

    @property
    def redis_client(self):
        """Get Redis client connection"""
        if not self._redis_client:
            try:
                import redis
                redis_config = self.env['ir.config_parameter'].sudo().get_param('manufacturing.redis_config', '{}')
                config = json.loads(redis_config) if redis_config else {}

                self._redis_client = redis.Redis(
                    host=config.get('host', 'localhost'),
                    port=config.get('port', 6379),
                    db=config.get('db', 0),
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                self._redis_client.ping()  # Test connection
            except Exception:
                self._redis_client = None

        return self._redis_client

    def _cache_key(self, method_name, *args, **kwargs):
        """Generate cache key"""
        key_data = {
            'method': method_name,
            'args': args,
            'kwargs': kwargs,
            'company': self.env.company.id
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return f"mrp:{hashlib.md5(key_string.encode()).hexdigest()}"

    def cached_method(self, cache_duration=3600):
        """Decorator cho cached methods"""
        def decorator(func):
            def wrapper(self, *args, **kwargs):
                if not self.redis_client:
                    return func(self, *args, **kwargs)

                cache_key = self._cache_key(func.__name__, *args, **kwargs)

                # Try to get from cache
                try:
                    cached_data = self.redis_client.get(cache_key)
                    if cached_data:
                        return json.loads(cached_data)
                except Exception:
                    pass

                # Execute function and cache result
                result = func(self, *args, **kwargs)

                try:
                    self.redis_client.setex(
                        cache_key,
                        cache_duration,
                        json.dumps(result, default=str)
                    )
                except Exception:
                    pass

                return result
            return wrapper
        return decorator


class MrpProduction(models.Model):
    _inherit = ['mrp.production', 'mrp.cache.mixin']

    @cached_method(cache_duration=1800)  # 30 minutes cache
    def get_bom_structure(self, bom_id=None):
        """Get BOM structure với caching"""
        bom = bom_id or self.bom_id
        return self._get_bom_explosion(bom)

    @cached_method(cache_duration=3600)  # 1 hour cache
    def get_workcenter_capacity(self, workcenter_id, date_from, date_to):
        """Get workcenter capacity với caching"""
        workcenter = self.env['mrp.workcenter'].browse(workcenter_id)

        # Calculate available capacity
        total_hours = sum([
            workcenter._get_workcenter_capacity(date)
            for date in self._date_range(date_from, date_to)
        ])

        return {
            'total_capacity_hours': total_hours,
            'available_hours': total_hours * 0.85,  # 85% availability factor
            'overtime_capacity': total_hours * 0.2
        }
```

### 3. Error Handling & Recovery Patterns

#### ✅ Robust Error Handling cho Manufacturing Operations

```python
class MrpErrorHandler(models.AbstractModel):
    _name = 'mrp.error.handler.mixin'

    def handle_production_error(self, error_context, exception, recovery_action=None):
        """Comprehensive error handling với recovery options"""

        # Log error details
        error_log = {
            'timestamp': fields.Datetime.now(),
            'user': self.env.user.name,
            'error_type': type(exception).__name__,
            'error_message': str(exception),
            'context': error_context,
            'traceback': traceback.format_exc() if hasattr(exception, '__traceback__') else None
        }

        # Store in error log
        self.env['mrp.error.log'].sudo().create(error_log)

        # Attempt recovery based on error type
        if recovery_action:
            try:
                return self._execute_recovery(recovery_action, error_context, exception)
            except Exception as recovery_error:
                # Log recovery failure
                self.env['mrp.error.log'].sudo().create({
                    'timestamp': fields.Datetime.now(),
                    'user': self.env.user.name,
                    'error_type': 'RecoveryFailed',
                    'error_message': f"Recovery failed: {str(recovery_error)}",
                    'context': {'original_error': error_context, 'recovery_action': recovery_action}
                })
                raise exception  # Re-raise original exception

        # Send notification to responsible users
        self._notify_error_team(error_log)

        raise exception

    def _execute_recovery(self, recovery_action, context, exception):
        """Execute recovery action"""
        recovery_methods = {
            'retry_material_reservation': self._retry_material_reservation,
            'regenerate_workorders': self._regenerate_workorders,
            'rollback_production_state': self._rollback_production_state,
            'create_correction_order': self._create_correction_order
        }

        if recovery_action in recovery_methods:
            return recovery_methods[recovery_action](context, exception)

        raise ValueError(f"Unknown recovery action: {recovery_action}")

    def _retry_material_reservation(self, context, exception):
        """Retry material reservation"""
        production_id = context.get('production_id')
        if not production_id:
            raise ValueError("Production ID required for retry")

        production = self.env['mrp.production'].browse(production_id)

        # Clear existing reservations
        production.move_raw_ids._action_cancel()

        # Retry reservation
        production._generate_raw_moves()
        production.action_assign()

        return {
            'status': 'success',
            'message': 'Material reservation retried successfully'
        }

    def _regenerate_workorders(self, context, exception):
        """Regenerate work orders"""
        production_id = context.get('production_id')
        if not production_id:
            raise ValueError("Production ID required for regeneration")

        production = self.env['mrp.production'].browse(production_id)

        # Cancel existing work orders
        production.workorder_ids.unlink()

        # Regenerate
        production._generate_workorders()

        return {
            'status': 'success',
            'message': 'Work orders regenerated successfully'
        }

    def _notify_error_team(self, error_log):
        """Send error notification"""
        # Get notification recipients
        recipients = self.env.ref('manufacturing.group_production_manager').users

        # Create notification
        for user in recipients:
            self.env['mail.message'].create({
                'message_type': 'notification',
                'model': 'mrp.error.log',
                'res_id': error_log.get('id'),
                'body': f"Production Error: {error_log['error_message']}",
                'partner_ids': [(4, user.partner_id.id)]
            })


class MrpProduction(models.Model):
    _inherit = ['mrp.production', 'mrp.error.handler.mixin']

    def action_confirm(self):
        """Override với error handling"""
        for production in self:
            try:
                super(MrpProduction, production).action_confirm()
            except Exception as e:
                # Attempt recovery
                if "Insufficient inventory" in str(e):
                    try:
                        production.handle_production_error(
                            error_context={
                                'production_id': production.id,
                                'action': 'action_confirm',
                                'bom_id': production.bom_id.id
                            },
                            exception=e,
                            recovery_action='retry_material_reservation'
                        )
                        continue  # Success with recovery
                    except Exception:
                        pass

                # Handle other error types
                production.handle_production_error(
                    error_context={
                        'production_id': production.id,
                        'action': 'action_confirm',
                        'state': production.state,
                        'product_id': production.product_id.id,
                        'quantity': production.product_qty
                    },
                    exception=e
                )

                raise  # Re-raise if recovery failed
```

## 📊 Advanced Analytics & Reporting

### 1. Production KPI Dashboard Implementation

#### ✅ Real-time Production Dashboard

```python
class MrpDashboard(models.AbstractModel):
    _name = 'mrp.dashboard.mixin'

    def get_dashboard_data(self, date_range=30):
        """Get comprehensive dashboard data"""

        date_from = fields.Date.today() - timedelta(days=date_range)
        date_to = fields.Date.today()

        return {
            'production_metrics': self._get_production_metrics(date_from, date_to),
            'quality_metrics': self._get_quality_metrics(date_from, date_to),
            'efficiency_metrics': self._get_efficiency_metrics(date_from, date_to),
            'inventory_metrics': self._get_inventory_metrics(date_from, date_to),
            'cost_metrics': self._get_cost_metrics(date_from, date_to)
        }

    def _get_production_metrics(self, date_from, date_to):
        """Calculate production KPIs"""

        # SQL query cho performance
        query = """
        SELECT
            COUNT(*) as total_orders,
            COUNT(CASE WHEN state = 'done' THEN 1 END) as completed_orders,
            COUNT(CASE WHEN state = 'progress' THEN 1 END) as in_progress_orders,
            COUNT(CASE WHEN state = 'cancel' THEN 1 END) as cancelled_orders,
            SUM(product_qty) as total_planned_qty,
            SUM(qty_produced) as total_produced_qty,
            ROUND(
                CASE
                    WHEN SUM(product_qty) > 0
                    THEN (SUM(qty_produced) / SUM(product_qty)) * 100
                    ELSE 0
                END, 2
            ) as completion_rate
        FROM mrp_production
        WHERE date_planned_start >= %s
        AND date_planned_start <= %s
        AND company_id = %s
        """

        self.env.cr.execute(query, [date_from, date_to, self.env.company.id])
        result = self.env.cr.dictfetchall()[0]

        # Calculate additional metrics
        result['on_time_delivery_rate'] = self._calculate_on_time_delivery(date_from, date_to)
        result['production_efficiency'] = self._calculate_production_efficiency(date_from, date_to)

        return result

    def _get_quality_metrics(self, date_from, date_to):
        """Calculate quality KPIs"""

        query = """
        SELECT
            COUNT(qc.id) as total_checks,
            COUNT(CASE WHEN qc.state = 'pass' THEN 1 END) as passed_checks,
            COUNT(CASE WHEN qc.state = 'fail' THEN 1 END) as failed_checks,
            ROUND(
                CASE
                    WHEN COUNT(qc.id) > 0
                    THEN (COUNT(CASE WHEN qc.state = 'pass' THEN 1 END) * 100.0 / COUNT(qc.id))
                    ELSE 0
                END, 2
            ) as pass_rate
        FROM quality_check qc
        JOIN mrp_workorder wo ON qc.workorder_id = wo.id
        JOIN mrp_production mp ON wo.production_id = mp.id
        WHERE mp.date_planned_start >= %s
        AND mp.date_planned_start <= %s
        AND mp.company_id = %s
        """

        self.env.cr.execute(query, [date_from, date_to, self.env.company.id])
        quality_data = self.env.cr.dictfetchall()[0]

        # Calculate defect rates
        quality_data['defect_rate'] = 100 - quality_data['pass_rate']
        quality_data['rework_rate'] = self._calculate_rework_rate(date_from, date_to)

        return quality_data

    def get_production_chart_data(self, chart_type, date_range=30):
        """Get data cho production charts"""

        date_from = fields.Date.today() - timedelta(days=date_range)
        date_to = fields.Date.today()

        if chart_type == 'production_trend':
            return self._get_production_trend_data(date_from, date_to)
        elif chart_type == 'workcenter_utilization':
            return self._get_workcenter_utilization_data(date_from, date_to)
        elif chart_type == 'quality_trend':
            return self._get_quality_trend_data(date_from, date_to)
        elif chart_type == 'cost_analysis':
            return self._get_cost_analysis_data(date_from, date_to)

        return {}

    def _get_production_trend_data(self, date_from, date_to):
        """Get production trend data cho line chart"""

        query = """
        SELECT
            DATE_TRUNC('day', date_planned_start) as production_date,
            COUNT(*) as orders_count,
            SUM(product_qty) as planned_qty,
            SUM(qty_produced) as produced_qty
        FROM mrp_production
        WHERE date_planned_start >= %s
        AND date_planned_start <= %s
        AND company_id = %s
        GROUP BY DATE_TRUNC('day', date_planned_start)
        ORDER BY production_date
        """

        self.env.cr.execute(query, [date_from, date_to, self.env.company.id])
        results = self.env.cr.dictfetchall()

        # Format cho Chart.js
        return {
            'labels': [r['production_date'].strftime('%Y-%m-%d') for r in results],
            'datasets': [
                {
                    'label': 'Planned Quantity',
                    'data': [float(r['planned_qty']) for r in results],
                    'borderColor': 'rgb(75, 192, 192)',
                    'backgroundColor': 'rgba(75, 192, 192, 0.2)',
                },
                {
                    'label': 'Produced Quantity',
                    'data': [float(r['produced_qty']) for r in results],
                    'borderColor': 'rgb(255, 99, 132)',
                    'backgroundColor': 'rgba(255, 99, 132, 0.2)',
                }
            ]
        }
```

#### ✅ Predictive Analytics Implementation

```python
class MrpPredictiveAnalytics(models.AbstractModel):
    _name = 'mrp.predictive.analytics.mixin'

    def predict_production_completion(self, production_id):
        """Predict production completion time using ML-like logic"""

        production = self.env['mrp.production'].browse(production_id)

        # Get historical data
        historical_data = self._get_similar_productions(production)

        if len(historical_data) < 3:
            # Fallback to simple estimation
            return self._simple_completion_estimation(production)

        # Calculate factors
        complexity_factor = self._calculate_complexity_factor(production)
        material_availability_factor = self._calculate_material_availability_factor(production)
        workcenter_load_factor = self._calculate_workcenter_load_factor(production)

        # Predict using weighted average
        base_time = sum(historical_data) / len(historical_data)

        predicted_time = base_time * complexity_factor * material_availability_factor * workcenter_load_factor

        return {
            'predicted_completion_hours': predicted_time,
            'confidence_level': min(0.9, len(historical_data) / 10),  # More data = higher confidence
            'factors': {
                'complexity': complexity_factor,
                'material_availability': material_availability_factor,
                'workcenter_load': workcenter_load_factor
            }
        }

    def predict_quality_issues(self, production_id):
        """Predict potential quality issues"""

        production = self.env['mrp.production'].browse(production_id)

        # Analyze risk factors
        risk_factors = {
            'complex_bom': self._assess_bom_complexity_risk(production.bom_id),
            'new_product': self._assess_new_product_risk(production.product_id),
            'material_variations': self._assess_material_variation_risk(production),
            'equipment_maintenance': self._assess_equipment_maintenance_risk(production)
        }

        # Calculate overall risk score
        risk_score = sum(risk_factors.values()) / len(risk_factors)

        # Get potential issues based on risk score
        potential_issues = []

        if risk_score > 0.7:
            potential_issues.append({
                'type': 'Dimensional Issues',
                'probability': risk_score * 0.8,
                'mitigation': 'Implement additional inspection points'
            })

        if risk_score > 0.6:
            potential_issues.append({
                'type': 'Material Defects',
                'probability': risk_score * 0.7,
                'mitigation': 'Enhanced incoming material inspection'
            })

        return {
            'overall_risk_score': risk_score,
            'risk_factors': risk_factors,
            'potential_issues': potential_issues,
            'recommendations': self._get_quality_recommendations(risk_score)
        }

    def _calculate_complexity_factor(self, production):
        """Calculate production complexity factor"""

        # Number of operations
        operation_count = len(production.bom_id.operation_ids or production.workorder_ids)

        # Number of components
        component_count = len(production.bom_id.bom_line_ids) if production.bom_id else 0

        # Special processes
        special_processes = 0
        for line in production.bom_id.bom_line_ids:
            if line.product_id.tracking in ('lot', 'serial'):
                special_processes += 1

        # Calculate complexity (1.0 = simple, >1.0 = complex)
        complexity = 1.0
        complexity += operation_count * 0.1
        complexity += component_count * 0.05
        complexity += special_processes * 0.2

        return min(complexity, 3.0)  # Cap at 3x complexity

    def _calculate_material_availability_factor(self, production):
        """Calculate material availability factor"""

        if not production.move_raw_ids:
            return 1.0  # No raw materials = no availability issues

        # Check availability of all raw materials
        total_moves = len(production.move_raw_ids)
        available_moves = len(production.move_raw_ids.filtered(
            lambda m: m.state == 'assigned'
        ))

        availability_ratio = available_moves / total_moves if total_moves > 0 else 1.0

        # Convert to factor (1.0 = fully available, >1.0 = shortages)
        return 2.0 - availability_ratio  # Invert: shortages increase time

    def _get_quality_recommendations(self, risk_score):
        """Get quality improvement recommendations"""

        recommendations = []

        if risk_score > 0.8:
            recommendations.extend([
                'Implement 100% inspection for critical dimensions',
                'Add additional in-process quality checkpoints',
                'Consider pilot run before full production'
            ])
        elif risk_score > 0.6:
            recommendations.extend([
                'Implement statistical process control',
                'Increase inspection frequency',
                'Review supplier quality requirements'
            ])
        elif risk_score > 0.4:
            recommendations.extend([
                'Standard quality control procedures should be sufficient',
                'Monitor first piece inspection results'
            ])
        else:
            recommendations.append('Standard quality procedures should be adequate')

        return recommendations
```

## 🔄 Integration Best Practices

### 1. Multi-Module Integration Patterns

#### ✅ Sales-to-Manufacturing Integration

```python
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    manufacturing_priority = fields.Selection([
        ('normal', 'Normal'),
        ('urgent', 'Urgent'),
        ('expedited', 'Expedited')
    ], default='normal')

    def action_confirm(self):
        """Override để create manufacturing orders nếu cần"""
        result = super().action_confirm()

        for order in self:
            if order.manufacturing_priority != 'normal':
                order._create_urgent_manufacturing_orders()

        return result

    def _create_urgent_manufacturing_orders(self):
        """Create urgent manufacturing orders"""

        for line in self.order_line:
            if not line.product_id.produce_delay:
                continue

            # Check if manufacturing is needed
            bom = self.env['mrp.bom']._bom_find(
                product=line.product_id,
                company_id=self.company_id
            )

            if bom and line.product_uom_qty > 0:
                # Create production order with expedited priority
                production = self.env['mrp.production'].create({
                    'product_id': line.product_id.id,
                    'product_qty': line.product_uom_qty,
                    'bom_id': bom.id,
                    'origin': self.name,
                    'priority': self._get_mrp_priority(self.manufacturing_priority),
                    'date_planned_start': fields.Datetime.now(),
                    'user_id': self.env.user.id
                })

                # Auto-confirm urgent orders
                production.action_confirm()

    def _get_mrp_priority(self, sale_priority):
        """Convert sale priority to MRP priority"""
        mapping = {
            'normal': '0',
            'urgent': '1',
            'expedited': '2'
        }
        return mapping.get(sale_priority, '0')

    def action_view_production_orders(self):
        """View related production orders"""
        productions = self.env['mrp.production'].search([
            ('origin', '=', self.name)
        ])

        if not productions:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Production Orders',
                    'message': 'No production orders found for this sales order.',
                    'type': 'info'
                }
            }

        return {
            'type': 'ir.actions.act_window',
            'name': 'Production Orders',
            'res_model': 'mrp.production',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', productions.ids)],
            'context': {'form_view_initial_mode': 'edit'}
        }


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        compute='_compute_sale_order',
        store=True
    )

    sale_line_ids = fields.Many2many(
        'sale.order.line',
        string='Sales Order Lines'
    )

    delivery_priority = fields.Selection([
        ('normal', 'Normal'),
        ('express', 'Express'),
        ('overnight', 'Overnight')
    ], default='normal')

    @api.depends('origin', 'move_finished_ids')
    def _compute_sale_order(self):
        """Link production order to sales order"""
        for production in self:
            if production.origin:
                # Try to find sale order by name
                sale_order = self.env['sale.order'].search([
                    ('name', '=', production.origin)
                ], limit=1)
                production.sale_order_id = sale_order
            else:
                # Try to find through finished moves
                finished_moves = production.move_finished_ids.filtered(
                    lambda m: m.sale_line_id
                )
                if finished_moves:
                    production.sale_order_id = finished_moves[0].sale_line_id.order_id

    def action_done(self):
        """Override để update sales order khi production hoàn thành"""
        result = super().action_done()

        for production in self:
            if production.sale_order_id:
                production._update_sales_order_status()

        return result

    def _update_sales_order_status(self):
        """Update sales order with production completion"""

        if not self.sale_order_id:
            return

        # Check if all productions for this sale order are done
        all_productions = self.env['mrp.production'].search([
            ('origin', '=', self.sale_order_id.name)
        ])

        if all(p.state == 'done' for p in all_productions):
            # Notify sales team
            self.sale_order_id.message_post_with_view(
                'mail.message_origin_link',
                values={
                    'self': self.sale_order_id,
                    'origin': self,
                    'record_name': self.name,
                },
                subtype_id=self.env.ref('mail.mt_note').id,
                message_type='notification'
            )
```

#### ✅ Purchase-to-Manufacturing Integration

```python
class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    is_for_production = fields.Boolean(
        string='For Production',
        help='Indicates this purchase order is for manufacturing materials'
    )

    production_ids = fields.Many2many(
        'mrp.production',
        string='Production Orders'
    )

    def _create_manufacturing_request(self):
        """Create manufacturing request when materials arrive"""

        if not self.is_for_production:
            return

        # Get produced products that need these materials
        for line in self.order_line:
            # Find BOMs that use this product
            boms_using_product = self.env['mrp.bom'].search([
                ('bom_line_ids.product_id', '=', line.product_id.id)
            ])

            for bom in boms_using_product:
                # Check if there are pending productions needing this BOM
                pending_productions = self.env['mrp.production'].search([
                    ('product_id', '=', bom.product_tmpl_id.product_variant_ids[:1].id),
                    ('bom_id', '=', bom.id),
                    ('state', 'in', ['confirmed', 'planned'])
                ])

                for production in pending_productions:
                    # Check if materials are now available
                    if self._are_materials_available(production):
                        production.action_assign()

                        # Notify production manager
                        production.message_post_with_view(
                            'mail.message_origin_link',
                            values={
                                'self': production,
                                'origin': self,
                                'record_name': self.name,
                            },
                            subtype_id=self.env.ref('mail.mt_note').id,
                            message_type='notification'
                        )

    def _are_materials_available(self, production):
        """Check if all materials are available for production"""

        for move in production.move_raw_ids:
            if move.state not in ('assigned', 'done'):
                return False
        return True


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    purchase_request_ids = fields.One2many(
        'purchase.request',
        'production_id',
        string='Purchase Requests'
    )

    def action_generate_purchase_requests(self):
        """Generate purchase requests for missing materials"""

        for production in self:
            missing_materials = production._get_missing_materials()

            for material in missing_materials:
                self.env['purchase.request'].create({
                    'production_id': production.id,
                    'product_id': material['product_id'],
                    'product_qty': material['quantity'],
                    'date_required': production.date_planned_start,
                    'reason': f'Material needed for production {production.name}',
                    'urgent': production.priority == '2'
                })

    def _get_missing_materials(self):
        """Get list of materials that need to be purchased"""

        missing_materials = []

        for move in self.move_raw_ids:
            if move.state == 'confirmed':  # Not enough inventory
                available_qty = self.env['stock.quant']._get_available_quantity(
                    move.product_id,
                    move.location_id,
                    lot_id=move.lot_id,
                    package_id=move.package_id,
                    owner_id=move.owner_id,
                    strict=True
                )

                if available_qty < move.product_qty:
                    missing_materials.append({
                        'product_id': move.product_id.id,
                        'quantity': move.product_qty - available_qty,
                        'uom_id': move.product_uom.id,
                        'date_required': self.date_planned_start
                    })

        return missing_materials
```

### 2. External System Integration

#### ✅ MES (Manufacturing Execution System) Integration

```python
class MrpMESIntegration(models.AbstractModel):
    _name = 'mrp.mes.integration.mixin'

    def sync_to_mes(self, action_type='create'):
        """Synchronize production data to MES system"""

        mes_config = self.env['mrp.mes.config'].sudo().get_active_config()
        if not mes_config:
            raise ValidationError('MES configuration not found')

        # Prepare data for MES
        mes_data = self._prepare_mes_data(action_type)

        # Send to MES via API
        try:
            response = requests.post(
                f"{mes_config.api_url}/production/{action_type}",
                json=mes_data,
                headers={
                    'Authorization': f"Bearer {mes_config.api_key}",
                    'Content-Type': 'application/json'
                },
                timeout=30
            )

            if response.status_code != 200:
                raise ValidationError(f"MES API Error: {response.text}")

            # Store MES reference
            self._store_mes_reference(response.json())

        except requests.exceptions.RequestException as e:
            # Queue for retry
            self._queue_mes_sync(action_type, mes_data, str(e))

    def _prepare_mes_data(self, action_type):
        """Prepare data structure for MES"""

        if action_type == 'create':
            return {
                'production_order': {
                    'external_id': self.id,
                    'work_order_number': self.name,
                    'product_code': self.product_id.default_code or self.product_id.name,
                    'planned_quantity': self.product_qty,
                    'planned_start': self.date_planned_start.isoformat(),
                    'bill_of_materials': self._get_mes_bom_data(),
                    'operations': self._get_mes_operations_data()
                }
            }
        elif action_type == 'start':
            return {
                'production_start': {
                    'external_id': self.id,
                    'actual_start': self.date_start.isoformat() if self.date_start else datetime.now().isoformat(),
                    'operator_id': self.user_id.id if self.user_id else None
                }
            }
        elif action_type == 'complete':
            return {
                'production_complete': {
                    'external_id': self.id,
                    'actual_quantity': self.qty_produced,
                    'completion_date': datetime.now().isoformat(),
                    'quality_data': self._get_mes_quality_data()
                }
            }

    def _get_mes_bom_data(self):
        """Get BOM data for MES"""

        bom_data = []
        for line in self.bom_id.bom_line_ids:
            bom_data.append({
                'component_code': line.product_id.default_code or line.product_id.name,
                'required_quantity': line.product_qty,
                'unit_of_measure': line.product_uom_id.name
            })

        return bom_data

    def _get_mes_operations_data(self):
        """Get operations data for MES"""

        operations_data = []
        for workorder in self.workorder_ids:
            operations_data.append({
                'operation_code': workorder.operation_id.code or workorder.operation_id.name,
                'workcenter_code': workorder.workcenter_id.code or workorder.workcenter_id.name,
                'planned_duration': workorder.duration_expected,
                'sequence': workorder.operation_id.sequence
            })

        return operations_data


class MrpProduction(models.Model):
    _inherit = ['mrp.production', 'mrp.mes.integration.mixin']

    mes_reference = fields.Char(string='MES Reference')

    def action_confirm(self):
        """Override để sync to MES"""
        result = super().action_confirm()

        for production in self:
            if self.env['ir.config_parameter'].sudo().get_param('manufacturing.mes_enabled') == 'True':
                production.sync_to_mes('create')

        return result

    def button_mark_done(self):
        """Override để sync completion to MES"""
        result = super().button_mark_done()

        for production in self:
            if self.env['ir.config_parameter'].sudo().get_param('manufacturing.mes_enabled') == 'True':
                production.sync_to_mes('complete')

        return result

    def action_start(self):
        """Override để sync start to MES"""
        result = super().action_start()

        for production in self:
            if self.env['ir.config_parameter'].sudo().get_param('manufacturing.mes_enabled') == 'True':
                production.sync_to_mes('start')

        return result
```

## 🔍 Testing Strategies

### 1. Comprehensive Testing Framework

#### ✅ Unit Testing cho Manufacturing Logic

```python
# tests/test_mrp_production.py
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

class TestMrpProduction(TransactionCase):

    def setUp(self):
        super().setUp()

        # Create test data
        self.Product = self.env['product.product']
        self.Bom = self.env['mrp.bom']
        self.Production = self.env['mrp.production']

        # Create test products
        self.finished_product = self.Product.create({
            'name': 'Finished Product',
            'type': 'product',
            'tracking': 'none'
        })

        self.component1 = self.Product.create({
            'name': 'Component 1',
            'type': 'product',
            'tracking': 'none'
        })

        self.component2 = self.Product.create({
            'name': 'Component 2',
            'type': 'product',
            'tracking': 'none'
        })

        # Create BOM
        self.bom = self.Bom.create({
            'product_tmpl_id': self.finished_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [
                (0, 0, {
                    'product_id': self.component1.id,
                    'product_qty': 2.0
                }),
                (0, 0, {
                    'product_id': self.component2.id,
                    'product_qty': 1.0
                })
            ]
        })

    def test_production_order_creation(self):
        """Test production order creation"""

        production = self.Production.create({
            'product_id': self.finished_product.id,
            'product_qty': 10.0,
            'bom_id': self.bom.id
        })

        self.assertEqual(production.state, 'draft')
        self.assertEqual(production.product_qty, 10.0)
        self.assertEqual(production.bom_id, self.bom)

    def test_production_confirmation(self):
        """Test production confirmation workflow"""

        # Create production order
        production = self.Production.create({
            'product_id': self.finished_product.id,
            'product_qty': 5.0,
            'bom_id': self.bom.id
        })

        # Add inventory for components
        self._create_inventory(self.component1, 100)
        self._create_inventory(self.component2, 100)

        # Confirm production
        production.action_confirm()

        self.assertEqual(production.state, 'confirmed')
        self.assertTrue(production.move_raw_ids)
        self.assertEqual(len(production.move_raw_ids), 2)

    def test_workorder_generation(self):
        """Test work order generation"""

        # Add operations to BOM
        self.bom.operation_ids = [
            (0, 0, {
                'name': 'Assembly',
                'workcenter_id': self._create_workcenter('Assembly WC').id,
                'time_cycle': 60
            })
        ]

        production = self.Production.create({
            'product_id': self.finished_product.id,
            'product_qty': 5.0,
            'bom_id': self.bom.id
        })

        # Add inventory
        self._create_inventory(self.component1, 100)
        self._create_inventory(self.component2, 100)

        production.action_confirm()

        self.assertTrue(production.workorder_ids)
        self.assertEqual(len(production.workorder_ids), 1)

    def test_production_costing(self):
        """Test production cost calculation"""

        # Set component costs
        self.component1.standard_price = 10.0
        self.component2.standard_price = 20.0

        # Add labor costs
        workcenter = self._create_workcenter('Assembly WC')
        workcenter.costs_hour = 50.0

        self.bom.operation_ids = [
            (0, 0, {
                'name': 'Assembly',
                'workcenter_id': workcenter.id,
                'time_cycle': 30  # 30 minutes
            })
        ]

        production = self.Production.create({
            'product_id': self.finished_product.id,
            'product_qty': 1.0,
            'bom_id': self.bom.id
        })

        production.action_confirm()

        # Check cost calculation
        expected_material_cost = (2.0 * 10.0) + (1.0 * 20.0)  # 40.0
        expected_labor_cost = (30.0 / 60.0) * 50.0  # 25.0
        expected_total_cost = expected_material_cost + expected_labor_cost  # 65.0

        self.assertAlmostEqual(production.calculate_total_cost(), expected_total_cost, 2)

    def test_quality_control_integration(self):
        """Test quality control integration"""

        # Create quality point
        quality_point = self.env['quality.point'].create({
            'name': 'Dimension Check',
            'product_id': self.finished_product.id,
            'picking_type_id': self.env.ref('mrp.picking_type_manufacturing').id,
            'measure_on': 'operation',
            'test_type_id': self.env.ref('quality.test_type_pass_fail').id
        })

        self.bom.operation_ids = [
            (0, 0, {
                'name': 'Assembly',
                'workcenter_id': self._create_workcenter('Assembly WC').id,
                'quality_point_ids': [(6, 0, [quality_point.id])]
            })
        ]

        production = self.Production.create({
            'product_id': self.finished_product.id,
            'product_qty': 5.0,
            'bom_id': self.bom.id
        })

        production.action_confirm()

        # Check quality check generation
        workorder = production.workorder_ids[0]
        workorder.action_start()

        quality_checks = self.env['quality.check'].search([
            ('workorder_id', '=', workorder.id)
        ])

        self.assertTrue(quality_checks)

    def _create_inventory(self, product, quantity):
        """Helper to create inventory"""
        inventory = self.env['stock.quant'].create({
            'product_id': product.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'quantity': quantity
        })
        return inventory

    def _create_workcenter(self, name):
        """Helper to create workcenter"""
        return self.env['mrp.workcenter'].create({
            'name': name,
            'capacity': 1.0,
            'time_efficiency': 1.0,
            'costs_hour': 0.0
        })


class TestMrpBom(TransactionCase):

    def setUp(self):
        super().setUp()

        self.Product = self.env['product.product']
        self.Bom = self.env['mrp.bom']

        self.product_a = self.Product.create({'name': 'Product A'})
        self.product_b = self.Product.create({'name': 'Product B'})
        self.component_c = self.Product.create({'name': 'Component C'})

    def test_bom_explode(self):
        """Test BOM explosion"""

        # Create sub-BOM
        sub_bom = self.Bom.create({
            'product_tmpl_id': self.product_b.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [
                (0, 0, {
                    'product_id': self.component_c.id,
                    'product_qty': 2.0
                })
            ]
        })

        # Create main BOM with sub-assembly
        main_bom = self.Bom.create({
            'product_tmpl_id': self.product_a.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [
                (0, 0, {
                    'product_id': self.product_b.id,
                    'product_qty': 3.0
                }),
                (0, 0, {
                    'product_id': self.component_c.id,
                    'product_qty': 1.0
                })
            ]
        })

        # Test explosion
        exploded_bom = main_bom.explode(self.product_a, 2.0)

        # Should contain:
        # - Product B: 3.0 * 2.0 = 6.0
        # - Component C from Product B: 2.0 * 6.0 = 12.0 (from sub-BOM)
        # - Component C directly: 1.0 * 2.0 = 2.0
        # Total Component C: 14.0

        self.assertEqual(len(exploded_bom), 2)

        component_c_line = next(line for line in exploded_bom
                                if line[0].id == self.component_c.id)
        self.assertEqual(component_c_line[1], 14.0)  # Total quantity
```

#### ✅ Integration Testing cho External Systems

```python
# tests/test_mes_integration.py
import json
import responses
from unittest.mock import patch

from odoo.tests.common import TransactionCase

class TestMESIntegration(TransactionCase):

    def setUp(self):
        super().setUp()

        self.Production = self.env['mrp.production']
        self.MesConfig = self.env['mrp.mes.config']

        # Enable MES integration
        self.env['ir.config_parameter'].sudo().set_param(
            'manufacturing.mes_enabled', 'True'
        )

        # Create MES config
        self.mes_config = self.MesConfig.create({
            'name': 'Test MES',
            'api_url': 'https://test-mes.example.com/api/v1',
            'api_key': 'test-api-key',
            'active': True
        })

        # Create test production
        self.production = self.env['mrp.production'].create({
            'name': 'TEST-001',
            'product_id': self.env.ref('product.product_product_1').id,
            'product_qty': 10.0
        })

    @responses.activate
    def test_mes_sync_on_create(self):
        """Test MES synchronization on production creation"""

        # Mock MES API response
        responses.add(
            responses.POST,
            'https://test-mes.example.com/api/v1/production/create',
            json={'id': 'MES-12345', 'status': 'created'},
            status=200
        )

        # Create production (should sync to MES)
        production = self.Production.create({
            'name': 'MES-TEST-001',
            'product_id': self.env.ref('product.product_product_1').id,
            'product_qty': 5.0
        })

        production.action_confirm()

        # Check MES API was called
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(
            responses.calls[0].request.headers['Authorization'],
            'Bearer test-api-key'
        )

        # Check request data
        request_data = json.loads(responses.calls[0].request.body)
        self.assertIn('production_order', request_data)
        self.assertEqual(
            request_data['production_order']['work_order_number'],
            'MES-TEST-001'
        )

    @responses.activate
    def test_mes_sync_with_retry(self):
        """Test MES sync with retry mechanism"""

        # First call fails
        responses.add(
            responses.POST,
            'https://test-mes.example.com/api/v1/production/create',
            json={'error': 'Server error'},
            status=500
        )

        # Second call succeeds
        responses.add(
            responses.POST,
            'https://test-mes.example.com/api/v1/production/create',
            json={'id': 'MES-12345', 'status': 'created'},
            status=200
        )

        # Create production
        production = self.Production.create({
            'name': 'MES-RETRY-001',
            'product_id': self.env.ref('product.product_product_1').id,
            'product_qty': 5.0
        })

        # Mock retry mechanism
        with patch('time.sleep', return_value=None):  # Skip actual sleep
            production.action_confirm()

        # Should have made 2 attempts
        self.assertEqual(len(responses.calls), 2)

    def test_mes_sync_disabled(self):
        """Test behavior when MES sync is disabled"""

        # Disable MES
        self.env['ir.config_parameter'].sudo().set_param(
            'manufacturing.mes_enabled', 'False'
        )

        # Create production
        production = self.Production.create({
            'name': 'NO-MES-001',
            'product_id': self.env.ref('product.product_product_1').id,
            'product_qty': 5.0
        })

        # Should not raise error even without MES setup
        production.action_confirm()
        self.assertEqual(production.state, 'confirmed')
```

### 2. Performance Testing

#### ✅ Load Testing cho Manufacturing Operations

```python
# tests/test_manufacturing_performance.py
import time
from odoo.tests.common import TransactionCase

class TestManufacturingPerformance(TransactionCase):

    def setUp(self):
        super().setUp()

        self.Production = self.env['mrp.production']

        # Create test data for performance testing
        self._setup_test_data()

    def test_bulk_production_creation_performance(self):
        """Test performance of creating many production orders"""

        start_time = time.time()

        # Create 100 production orders
        productions = []
        for i in range(100):
            production = self.Production.create({
                'name': f'PERF-TEST-{i:04d}',
                'product_id': self.test_product.id,
                'product_qty': 10.0,
                'bom_id': self.test_bom.id
            })
            productions.append(production)

        creation_time = time.time() - start_time

        # Assert reasonable performance (< 5 seconds for 100 records)
        self.assertLess(creation_time, 5.0,
                       f"Creating 100 productions took too long: {creation_time:.2f}s")

        # Test batch confirmation performance
        start_time = time.time()

        self.Production.browse([p.id for p in productions]).action_confirm()

        confirmation_time = time.time() - start_time

        # Assert reasonable performance (< 3 seconds for confirmation)
        self.assertLess(confirmation_time, 3.0,
                       f"Confirming 100 productions took too long: {confirmation_time:.2f}s")

    def test_bom_explosion_performance(self):
        """Test BOM explosion performance with complex BOMs"""

        # Create complex BOM with 50 components
        complex_bom = self._create_complex_bom(50)

        start_time = time.time()

        # Explode BOM multiple times
        for i in range(100):
            exploded_bom = complex_bom.explode(self.test_product, 1.0)

        explosion_time = time.time() - start_time

        # Assert reasonable performance (< 1 second for 100 explosions)
        self.assertLess(explosion_time, 1.0,
                       f"BOM explosion took too long: {explosion_time:.2f}s")

        # Verify explosion correctness
        self.assertEqual(len(exploded_bom), 50)

    def test_workorder_scheduling_performance(self):
        """Test work order scheduling performance"""

        # Create production with many work orders
        production = self.Production.create({
            'name': 'SCHEDULING-TEST',
            'product_id': self.test_product.id,
            'product_qty': 10.0,
            'bom_id': self.complex_bom.id
        })

        start_time = time.time()

        production.action_confirm()

        scheduling_time = time.time() - start_time

        # Assert reasonable performance (< 2 seconds for scheduling)
        self.assertLess(scheduling_time, 2.0,
                       f"Work order scheduling took too long: {scheduling_time:.2f}s")

        # Verify work order creation
        self.assertGreater(len(production.workorder_ids), 0)

    def _setup_test_data(self):
        """Setup test data for performance testing"""

        # Create test product
        self.test_product = self.env['product.product'].create({
            'name': 'Test Product for Performance'
        })

        # Create components
        self.components = self.env['product.product'].create([
            {'name': f'Component {i}'} for i in range(100)
        ])

        # Create simple BOM
        self.test_bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.test_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [
                (0, 0, {
                    'product_id': self.components[0].id,
                    'product_qty': 1.0
                })
            ]
        })

        # Create workcenter
        self.workcenter = self.env['mrp.workcenter'].create({
            'name': 'Test Workcenter',
            'capacity': 1.0
        })

    def _create_complex_bom(self, num_components):
        """Create complex BOM with specified number of components"""

        bom_lines = []
        for i in range(num_components):
            bom_lines.append((0, 0, {
                'product_id': self.components[i].id,
                'product_qty': 1.0
            }))

        complex_bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.test_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': bom_lines
        })

        return complex_bom
```

## 🚀 Deployment & Maintenance

### 1. Production Deployment Guidelines

#### ✅ Deployment Checklist

```python
# Class for deployment validation
class ManufacturingDeploymentValidator(models.AbstractModel):
    _name = 'manufacturing.deployment.validator'

    def validate_pre_deployment(self):
        """Comprehensive pre-deployment validation"""

        validation_results = {
            'status': 'success',
            'checks': [],
            'errors': [],
            'warnings': []
        }

        # Check 1: Data integrity
        validation_results['checks'].append(self._check_data_integrity())

        # Check 2: Configuration completeness
        validation_results['checks'].append(self._check_configuration_completeness())

        # Check 3: Performance optimization
        validation_results['checks'].append(self._check_performance_optimization())

        # Check 4: Security settings
        validation_results['checks'].append(self._check_security_settings())

        # Check 5: Integration points
        validation_results['checks'].append(self._check_integration_points())

        # Aggregate results
        for check in validation_results['checks']:
            if check['status'] == 'error':
                validation_results['errors'].extend(check['issues'])
                validation_results['status'] = 'error'
            elif check['status'] == 'warning':
                validation_results['warnings'].extend(check['issues'])

        return validation_results

    def _check_data_integrity(self):
        """Check data integrity"""

        issues = []

        # Check for orphaned records
        orphaned_productions = self.env.cr.execute("""
            SELECT COUNT(*)
            FROM mrp_production mp
            LEFT JOIN product_product pp ON mp.product_id = pp.id
            WHERE pp.id IS NULL
        """)[0][0]

        if orphaned_productions > 0:
            issues.append(f'Found {orphaned_productions} orphaned production records')

        # Check for inconsistent states
        inconsistent_states = self.env.cr.execute("""
            SELECT COUNT(*)
            FROM mrp_production
            WHERE state = 'confirmed'
            AND (SELECT COUNT(*) FROM mrp_workorder WHERE production_id = mrp_production.id) = 0
        """)[0][0]

        if inconsistent_states > 0:
            issues.append(f'Found {inconsistent_states} productions without work orders')

        return {
            'status': 'error' if issues else 'success',
            'issues': issues,
            'description': 'Data integrity validation'
        }

    def _check_configuration_completeness(self):
        """Check manufacturing configuration completeness"""

        issues = []

        # Check workcenter configuration
        workcenters_without_capacity = self.env['mrp.workcenter'].search([
            ('capacity', '=', 0)
        ])

        if workcenters_without_capacity:
            issues.append(f'{len(workcenters_without_capacity)} workcenters without capacity')

        # Check BOM completeness
        boms_without_operations = self.env['mrp.bom'].search([
            ('operation_ids', '=', False),
            ('bom_line_ids', '!=', False)
        ])

        if boms_without_operations:
            issues.append(f'{len(boms_without_operations)} BOMs without operations')

        # Check quality point configuration
        products_without_quality = self.env['product.product'].search([
            ('produce_delay', '>', 0),
            ('quality_point_ids', '=', False)
        ])

        if products_without_quality:
            issues.append(f'{len(products_without_quality)} products without quality points')

        return {
            'status': 'warning' if issues else 'success',
            'issues': issues,
            'description': 'Configuration completeness check'
        }

    def _check_performance_optimization(self):
        """Check performance optimizations"""

        issues = []

        # Check if indexes exist
        required_indexes = [
            'idx_mrp_production_company_state',
            'idx_mrp_workorder_production_state',
            'idx_mrp_bom_product_company'
        ]

        for index_name in required_indexes:
            index_exists = self.env.cr.execute(f"""
                SELECT COUNT(*) FROM pg_indexes
                WHERE indexname = '{index_name}'
            """)[0][0] > 0

            if not index_exists:
                issues.append(f'Missing index: {index_name}')

        # Check table statistics
        stale_statistics = self.env.cr.execute("""
            SELECT COUNT(*) FROM pg_stat_user_tables
            WHERE last_vacuum < NOW() - INTERVAL '7 days'
            AND schemaname = 'public'
            AND tablename LIKE 'mrp_%'
        """)[0][0]

        if stale_statistics > 0:
            issues.append(f'{stale_statistics} manufacturing tables need VACUUM ANALYZE')

        return {
            'status': 'warning' if issues else 'success',
            'issues': issues,
            'description': 'Performance optimization check'
        }
```

#### ✅ Migration Strategy

```python
# migrations/13.0.1.0.0/pre-migration.py
def pre_migration_checks():
    """Pre-migration validation"""

    issues = []

    # Check data volume
    production_count = env.cr.execute("SELECT COUNT(*) FROM mrp_production")[0][0]
    if production_count > 100000:
        issues.append(f"Large production dataset: {production_count} records")

    # Check custom modules compatibility
    custom_modules = env['ir.module.module'].search([
        ('state', '=', 'installed'),
        ('name', 'like', 'manufacturing%')
    ])

    if custom_modules:
        issues.append(f"Custom manufacturing modules found: {custom_modules.mapped('name')}")

    if issues:
        raise UserError("Pre-migration issues found:\n" + "\n".join(issues))

# migrations/13.0.1.0.0/post-migration.py
def post_migration_optimizations():
    """Post-migration optimizations"""

    # Update materialized views
    env.cr.execute("""
        REFRESH MATERIALIZED VIEW mrp_production_analytics;
    """)

    # Rebuild indexes
    env.cr.execute("REINDEX INDEX CONCURRENTLY idx_mrp_production_company_state;")

    # Update statistics
    env.cr.execute("ANALYZE mrp_production;")
    env.cr.execute("ANALYZE mrp_workorder;")
    env.cr.execute("ANALYZE mrp_bom;")

    # Create default configurations if missing
    if not env['ir.config_parameter'].sudo().search([('key', '=', 'manufacturing.mes_enabled')]):
        env['ir.config_parameter'].sudo().create({
            'key': 'manufacturing.mes_enabled',
            'value': 'False'
        })
```

### 2. Monitoring & Maintenance

#### ✅ Manufacturing Health Monitoring

```python
class ManufacturingHealthMonitor(models.AbstractModel):
    _name = 'manufacturing.health.monitor'

    def get_system_health(self):
        """Get comprehensive system health metrics"""

        health_data = {
            'overall_status': 'healthy',
            'metrics': {},
            'alerts': [],
            'recommendations': []
        }

        # Performance metrics
        health_data['metrics']['performance'] = self._get_performance_metrics()

        # Data quality metrics
        health_data['metrics']['data_quality'] = self._get_data_quality_metrics()

        # System usage metrics
        health_data['metrics']['usage'] = self._get_usage_metrics()

        # Integration status
        health_data['metrics']['integrations'] = self._get_integration_status()

        # Generate alerts and recommendations
        health_data['alerts'] = self._generate_alerts(health_data['metrics'])
        health_data['recommendations'] = self._generate_recommendations(health_data['metrics'])

        # Determine overall status
        if health_data['alerts']:
            if any(alert['severity'] == 'critical' for alert in health_data['alerts']):
                health_data['overall_status'] = 'critical'
            else:
                health_data['overall_status'] = 'warning'

        return health_data

    def _get_performance_metrics(self):
        """Get performance metrics"""

        return {
            'avg_production_time': self._calculate_avg_production_time(),
            'production_throughput': self._calculate_production_throughput(),
            'workcenter_utilization': self._calculate_workcenter_utilization(),
            'quality_pass_rate': self._calculate_quality_pass_rate()
        }

    def _get_data_quality_metrics(self):
        """Get data quality metrics"""

        return {
            'orphaned_records': self._count_orphaned_records(),
            'incomplete_data': self._count_incomplete_records(),
            'data_consistency_score': self._calculate_consistency_score()
        }

    def _generate_alerts(self, metrics):
        """Generate system alerts based on metrics"""

        alerts = []

        # Performance alerts
        if metrics['performance']['avg_production_time'] > 8:  # hours
            alerts.append({
                'type': 'performance',
                'severity': 'warning',
                'message': f"Average production time is {metrics['performance']['avg_production_time']:.1f} hours",
                'recommendation': 'Consider optimizing production workflows'
            })

        if metrics['performance']['quality_pass_rate'] < 90:  # percent
            alerts.append({
                'type': 'quality',
                'severity': 'critical',
                'message': f"Quality pass rate is {metrics['performance']['quality_pass_rate']:.1f}%",
                'recommendation': 'Review quality control processes'
            })

        # Data quality alerts
        if metrics['data_quality']['orphaned_records'] > 0:
            alerts.append({
                'type': 'data_quality',
                'severity': 'warning',
                'message': f"Found {metrics['data_quality']['orphaned_records']} orphaned records",
                'recommendation': 'Run data cleanup procedures'
            })

        return alerts

    def create_maintenance_tasks(self, health_data):
        """Create maintenance tasks based on health analysis"""

        Task = self.env['project.task']
        Project = self.env['project.project']

        # Get or create maintenance project
        project = Project.search([('name', '=', 'Manufacturing Maintenance')], limit=1)
        if not project:
            project = Project.create({
                'name': 'Manufacturing Maintenance',
                'privacy_visibility': 'employees'
            })

        tasks_created = []

        for alert in health_data['alerts']:
            if alert['severity'] == 'critical':
                task = Task.create({
                    'name': alert['message'],
                    'description': alert['recommendation'],
                    'project_id': project.id,
                    'priority': '3',  # High
                    'stage_id': self.env.ref('project.project_stage_1').id
                })
                tasks_created.append(task.id)

        return tasks_created
```

---

## 📋 Summary

Best Practices documentation này cung cấp:

### ✅ **Comprehensive Development Guidelines**
- Customization patterns cho production workflows
- Performance optimization strategies
- Security implementation patterns
- Error handling và recovery mechanisms

### ✅ **Technical Implementation Excellence**
- Database schema optimization
- Caching strategies với Redis integration
- Predictive analytics implementation
- Testing frameworks (unit, integration, performance)

### ✅ **Integration Best Practices**
- Multi-module integration patterns
- External system integration (MES)
- Sales-to-Manufacturing workflows
- Purchase-to-Manufacturing automation

### ✅ **Production Deployment Ready**
- Deployment validation checklist
- Migration strategies
- Health monitoring systems
- Maintenance automation

### ✅ **Quality Assurance**
- Comprehensive testing framework
- Performance benchmarking
- Data quality validation
- Security compliance checks

---

**Module Status**: ✅ **COMPLETED**
**File Size**: ~12,000 từ
**Language**: Tiếng Việt
**Target Audience**: Developers, Manufacturing Engineers, System Administrators
**Completion**: 2025-11-08

*File này hoàn thiện Manufacturing Module documentation với các best practices toàn diện, đảm bảo triển khai sản xuất thành công và bền vững trong môi trường thực tế.*