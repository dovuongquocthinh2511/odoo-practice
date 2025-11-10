# 📚 Best Practices Accounting Module - Odoo 18

## 🎯 Giới Thiệu Best Practices

Chương này cung cấp best practices toàn diện cho accounting module integration với supply chain, tập trung vào financial compliance, audit trail, security, performance optimization, và business process excellence với Vietnamese regulatory compliance.

## 🔍 Financial Compliance Best Practices

### 1. Vietnamese Accounting Standards (VAS) Implementation

```python
class VietnameseAccountingCompliance(models.Model):
    _inherit = 'account.move'

    def _check_vas_compliance(self):
        """Kiểm tra tuân thủ Vietnamese Accounting Standards"""
        self.ensure_one()

        compliance_issues = []

        # Check 1: Chart of Accounts compliance
        if not self._check_chart_of_accounts_compliance():
            compliance_issues.append({
                'type': 'chart_of_accounts',
                'severity': 'error',
                'message': _('Chart of Accounts không tuân thủ VAS 03')
            })

        # Check 2: Transaction classification
        if not self._check_transaction_classification():
            compliance_issues.append({
                'type': 'transaction_classification',
                'severity': 'warning',
                'message': _('Phân loại giao dịch cần kiểm tra theo VAS 01')
            })

        # Check 3: Document requirements
        if not self._check_document_requirements():
            compliance_issues.append({
                'type': 'documentation',
                'severity': 'error',
                'message': _('Thiếu chứng từ kế toán theo quy định')
            })

        # Check 4: Tax compliance
        tax_issues = self._check_tax_compliance()
        compliance_issues.extend(tax_issues)

        return compliance_issues

    def _check_chart_of_accounts_compliance(self):
        """Kiểm tra tuân thủ hệ thống tài khoản theo Thông tư 200/2014/TT-BTC"""
        required_accounts = [
            '111',  # Tiền mặt
            '112',  # Tiền gửi ngân hàng
            '131',  # Phải thu khách hàng
            '331',  # Phải trả nhà cung cấp
            '511',  # Doanh thu bán hàng
            '632',  # Giá vốn hàng bán
            '811',  # Chi phí quản lý doanh nghiệp
            '821',  # Chi phí bán hàng
        ]

        for line in self.line_ids:
            account_code = line.account_id.code[:3]
            if account_code in required_accounts:
                return True

        return False

    def _check_transaction_classification(self):
        """Kiểm tra phân loại giao dịch theo VAS 01"""
        # VAS 01 yêu cầu phân loại rõ ràng các loại giao dịch
        has_revenue = False
        has_expense = False
        has_asset = False

        for line in self.line_ids:
            account_internal_type = line.account_id.internal_type

            if account_internal_type == 'income':
                has_revenue = True
            elif account_internal_type == 'expense':
                has_expense = True
            elif account_internal_type == 'asset':
                has_asset = True

        # Revenue transactions should have corresponding expense or asset
        if has_revenue and not (has_expense or has_asset):
            return False

        return True

    def _check_document_requirements(self):
        """Kiểm tra yêu cầu chứng từ theo Luật Kế toán"""
        # Kiểm tra required attachments
        if self.move_type in ['out_invoice', 'in_invoice']:
            if not self.attachment_ids:
                return False

            # Check for specific document types
            if self.move_type == 'in_invoice':
                # Supplier invoice requires PO or receipt
                if not self.purchase_order_id and not self.stock_picking_id:
                    return False

        return True

    def _check_tax_compliance(self):
        """Kiểm tra tuân thủ thuế GTGT và TNDN"""
        issues = []

        # VAT compliance
        for line in self.line_ids:
            for tax in line.tax_ids:
                if tax.amount_type == 'percent':
                    # Check VAT rate validity
                    valid_vat_rates = [0, 5, 10]  # VAT rates in Vietnam
                    if tax.amount not in valid_vat_rates:
                        issues.append({
                            'type': 'invalid_vat_rate',
                            'severity': 'error',
                            'message': _('Thuế suất VAT không hợp lệ: %s%%') % tax.amount
                        })

        return issues

    @api.model
    def generate_vas_compliance_report(self, date_from, date_to):
        """Tạo báo cáo tuân thủ VAS"""
        domain = [
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('state', '=', 'posted'),
            ('company_id', '=', self.env.company.id)
        ]

        moves = self.search(domain)

        compliance_report = {
            'total_transactions': len(moves),
            'compliance_issues': [],
            'chart_of_accounts_compliance': 0,
            'transaction_classification_compliance': 0,
            'documentation_compliance': 0,
            'tax_compliance': 0,
        }

        for move in moves:
            issues = move._check_vas_compliance()
            if issues:
                compliance_report['compliance_issues'].append({
                    'move_id': move.id,
                    'move_name': move.name,
                    'issues': issues
                })

            # Update compliance metrics
            if move._check_chart_of_accounts_compliance():
                compliance_report['chart_of_accounts_compliance'] += 1

            if move._check_transaction_classification():
                compliance_report['transaction_classification_compliance'] += 1

            if move._check_document_requirements():
                compliance_report['documentation_compliance'] += 1

            if not move._check_tax_compliance():
                compliance_report['tax_compliance'] += 1

        # Calculate percentages
        if compliance_report['total_transactions'] > 0:
            base = compliance_report['total_transactions']
            compliance_report['chart_of_accounts_compliance_pct'] = (
                compliance_report['chart_of_accounts_compliance'] / base * 100
            )
            compliance_report['transaction_classification_compliance_pct'] = (
                compliance_report['transaction_classification_compliance'] / base * 100
            )
            compliance_report['documentation_compliance_pct'] = (
                compliance_report['documentation_compliance'] / base * 100
            )
            compliance_report['tax_compliance_pct'] = (
                compliance_report['tax_compliance'] / base * 100
            )

        return compliance_report

# Vietnamese Chart of Accounts Configuration
class VietnameseChartOfAccounts(models.Model):
    _name = 'vietnamese.chart.of.accounts'
    _description = 'Vietnamese Chart of Accounts Configuration'

    company_id = fields.Many2one('res.company', string='Company', required=True)
    vas_version = fields.Selection([
        ('2014', 'VAS 2014 (Thông tư 200/2014/TT-BTC)'),
        ('current', 'Current Version'),
    ], string='VAS Version', default='2014')
    is_configured = fields.Boolean(string='Is Configured', default=False)

    def action_configure_chart_of_accounts(self):
        """Cấu hình hệ thống tài khoản theo VAS"""
        self.ensure_one()

        # Tạo account structure theo VAS 2014
        account_templates = self._get_vas_account_templates()

        for template in account_templates:
            self._create_account_from_template(template)

        self.write({'is_configured': True})

    def _get_vas_account_templates(self):
        """Lấy templates cho hệ thống tài khoản VAS"""
        return [
            # Tài sản ngắn hạn (Class 1)
            {
                'code': '110',
                'name': 'TÀI SẢN NGẮN HẠN',
                'type': 'view',
                'internal_type': 'asset',
            },
            {
                'code': '111',
                'name': 'Tiền mặt',
                'type': 'liquidity',
                'internal_type': 'asset',
                'parent_code': '110',
            },
            {
                'code': '112',
                'name': 'Tiền gửi ngân hàng',
                'type': 'liquidity',
                'internal_type': 'asset',
                'parent_code': '110',
            },
            {
                'code': '131',
                'name': 'Phải thu khách hàng',
                'type': 'receivable',
                'internal_type': 'asset_receivable',
                'parent_code': '110',
            },
            {
                'code': '138',
                'name': 'Tài sản ngắn hạn khác',
                'type': 'other',
                'internal_type': 'asset',
                'parent_code': '110',
            },

            # Tài sản dài hạn (Class 2)
            {
                'code': '210',
                'name': 'TÀI SẢN DÀI HẠN',
                'type': 'view',
                'internal_type': 'asset',
            },
            {
                'code': '211',
                'name': 'Tài sản cố định hữu hình',
                'type': 'fixed_assets',
                'internal_type': 'asset',
                'parent_code': '210',
            },
            {
                'code': '214',
                'name': 'Tài sản cố định vô hình',
                'type': 'intangible',
                'internal_type': 'asset',
                'parent_code': '210',
            },

            # Nợ phải trả (Class 3)
            {
                'code': '310',
                'name': 'NỢ PHẢI TRẢ',
                'type': 'view',
                'internal_type': 'liability',
            },
            {
                'code': '311',
                'name': 'Phải trả người lao động',
                'type': 'payable',
                'internal_type': 'liability_payable',
                'parent_code': '310',
            },
            {
                'code': '331',
                'name': 'Phải trả nhà cung cấp',
                'type': 'payable',
                'internal_type': 'liability_payable',
                'parent_code': '310',
            },
            {
                'code': '338',
                'name': 'Nợ phải trả khác',
                'type': 'other',
                'internal_type': 'liability',
                'parent_code': '310',
            },

            # Vốn chủ sở hữu (Class 4)
            {
                'code': '410',
                'name': 'VỐN CHỦ SỞ HỮU',
                'type': 'view',
                'internal_type': 'equity',
            },
            {
                'code': '411',
                'name': 'Vốn góp của chủ sở hữu',
                'type': 'equity',
                'internal_type': 'equity',
                'parent_code': '410',
            },
            {
                'code': '421',
                'name': 'Lợi nhuận sau thuế chưa phân phối',
                'type': 'equity',
                'internal_type': 'equity',
                'parent_code': '410',
            },

            # Doanh thu (Class 5)
            {
                'code': '510',
                'name': 'DOANH THU',
                'type': 'view',
                'internal_type': 'income',
            },
            {
                'code': '511',
                'name': 'Doanh thu bán hàng',
                'type': 'income',
                'internal_type': 'income',
                'parent_code': '510',
            },
            {
                'code': '515',
                'name': 'Doanh thu cung cấp dịch vụ',
                'type': 'income',
                'internal_type': 'income',
                'parent_code': '510',
            },
            {
                'code': '521',
                'name': 'Doanh thu tài chính',
                'type': 'income_other',
                'internal_type': 'income',
                'parent_code': '510',
            },
            {
                'code': '522',
                'name': 'Doanh thu ngoài hoạt động',
                'type': 'income_other',
                'internal_type': 'income',
                'parent_code': '510',
            },

            # Giá vốn (Class 6 - chỉ hàng bán)
            {
                'code': '632',
                'name': 'Giá vốn hàng bán',
                'type': 'expense',
                'internal_type': 'expense',
            },

            # Chi phí hoạt động (Class 8)
            {
                'code': '810',
                'name': 'CHI PHÍ HOẠT ĐỘNG',
                'type': 'view',
                'internal_type': 'expense',
            },
            {
                'code': '811',
                'name': 'Chi phí quản lý doanh nghiệp',
                'type': 'expense',
                'internal_type': 'expense',
                'parent_code': '810',
            },
            {
                'code': '821',
                'name': 'Chi phí bán hàng',
                'type': 'expense',
                'internal_type': 'expense',
                'parent_code': '810',
            },
            {
                'code': '822',
                'name': 'Chi phí quản lý doanh nghiệp',
                'type': 'expense',
                'internal_type': 'expense',
                'parent_code': '810',
            },
        ]

    def _create_account_from_template(self, template):
        """Tạo account từ template"""
        # Check if account already exists
        existing_account = self.env['account.account'].search([
            ('code', '=', template['code']),
            ('company_id', '=', self.company_id.id)
        ])

        if existing_account:
            return existing_account

        # Find parent account if specified
        parent_account = None
        if 'parent_code' in template:
            parent_account = self.env['account.account'].search([
                ('code', '=', template['parent_code']),
                ('company_id', '=', self.company_id.id)
            ], limit=1)

        account_vals = {
            'name': template['name'],
            'code': template['code'],
            'user_type_id': self._get_account_user_type(template['type']),
            'internal_type': template['internal_type'],
            'company_id': self.company_id.id,
            'reconcile': template['type'] in ['receivable', 'payable'],
        }

        if parent_account:
            account_vals['parent_id'] = parent_account.id

        return self.env['account.account'].create(account_vals)

    def _get_account_user_type(self, account_type):
        """Lấy user type cho account"""
        user_type_map = {
            'liquidity': 'data_account_type_current_assets',
            'receivable': 'data_account_type_receivable',
            'payable': 'data_account_type_payable',
            'income': 'data_account_type_revenue',
            'expense': 'data_account_type_expenses',
            'equity': 'data_account_type_equity',
            'fixed_assets': 'data_account_type_fixed_assets',
            'intangible': 'data_account_type_fixed_assets',
            'other': 'data_account_type_current_assets',
            'income_other': 'data_account_type_other_income',
        }

        user_type_code = user_type_map.get(account_type, 'data_account_type_current_assets')

        return self.env['account.account.type'].search([
            ('type', '=', user_type_code),
        ], limit=1).id or self.env.ref('account.data_account_type_current_assets').id
```

## 🔒 Security and Access Control

### 2. Advanced Access Control Matrix

```python
class AccountingSecurity(models.Model):
    _inherit = 'res.users'

    # Add security fields
    accounting_access_level = fields.Selection([
        ('none', 'No Access'),
        ('read_only', 'Read Only'),
        ('limited_write', 'Limited Write'),
        ('full_access', 'Full Access'),
        ('admin', 'Administrator'),
    ], string='Accounting Access Level', default='none')

    approved_for_posting = fields.Boolean(string='Approved for Posting', default=False)
    can_approve_invoices = fields.Boolean(string='Can Approve Invoices', default=False)
    can_process_payments = fields.Boolean(string='Can Process Payments', default=False)
    can_access_reports = fields.Boolean(string='Can Access Reports', default=False)

    @api.model
    def check_accounting_access(self, operation, account_id=None):
        """Kiểm tra quyền truy cập accounting"""
        user = self.env.user

        if user.accounting_access_level == 'admin':
            return True

        if operation == 'read':
            return user.accounting_access_level in ['read_only', 'limited_write', 'full_access']

        if operation == 'write':
            return user.accounting_access_level in ['limited_write', 'full_access']

        if operation == 'post':
            return user.accounting_access_level == 'full_access' and user.approved_for_posting

        if operation == 'approve':
            return user.can_approve_invoices

        if operation == 'payment':
            return user.can_process_payments

        return False

class AccountMoveSecurity(models.Model):
    _inherit = 'account.move'

    @api.model
    def create(self, vals):
        """Override create với security checks"""
        # Check user permissions
        if not self.env.user.check_accounting_access('write'):
            raise AccessDenied(_('You do not have permission to create accounting entries'))

        # Validate account access for each line
        if 'line_ids' in vals:
            for line_vals in vals['line_ids']:
                if line_vals[0] == 0:  # New line
                    account_id = line_vals[2].get('account_id')
                    if account_id:
                        if not self._check_account_access(account_id, 'write'):
                            raise AccessDenied(_('You do not have access to account %s') % account_id)

        return super().create(vals)

    def write(self, vals):
        """Override write với security checks"""
        # Check if user can modify posted entries
        if self.filtered(lambda m: m.state == 'posted'):
            if not self.env.user.has_group('account.group_account_manager'):
                raise AccessDenied(_('You cannot modify posted accounting entries'))

        # Check write permissions
        if not self.env.user.check_accounting_access('write'):
            raise AccessDenied(_('You do not have permission to modify accounting entries'))

        # Validate account access for line modifications
        if 'line_ids' in vals:
            for line_vals in vals['line_ids']:
                if line_vals[0] in [0, 1]:  # New or updated line
                    account_id = line_vals[2].get('account_id')
                    if account_id and not self._check_account_access(account_id, 'write'):
                        raise AccessDenied(_('You do not have access to account %s') % account_id)

        return super().write(vals)

    def action_post(self):
        """Override posting với approval workflow"""
        # Check posting permission
        if not self.env.user.check_accounting_access('post'):
            raise AccessDenied(_('You are not authorized to post accounting entries'))

        # Check if approval is required
        if self._requires_approval() and not self._is_approved():
            self._request_approval()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Approval Required'),
                    'message': _('This entry requires approval before posting'),
                    'type': 'warning'
                }
            }

        return super().action_post()

    def _requires_approval(self):
        """Kiểm tra entry có yêu cầu approval không"""
        # Large amounts require approval
        if self.amount_total > self.env.company.approval_threshold:
            return True

        # Certain account types require approval
        restricted_accounts = ['591', '592']  # Chi phí quỹ cáo
        for line in self.line_ids:
            if line.account_id.code[:3] in restricted_accounts:
                return True

        return False

    def _is_approved(self):
        """Kiểm tra entry đã được approve chưa"""
        return self.approval_ids.filtered(
            lambda a: a.state == 'approved'
        ).exists()

    def _request_approval(self):
        """Gửi yêu cầu approval"""
        self.env['account.approval'].create({
            'move_id': self.id,
            'requested_by': self.env.user.id,
            'approver_ids': [(6, 0, self._get_approvers().ids)],
            'amount': self.amount_total,
        })

    def _get_approvers(self):
        """Lấy danh sách approvers"""
        approvers = self.env['res.users'].search([
            ('can_approve_invoices', '=', True),
            ('accounting_access_level', 'in', ['full_access', 'admin']),
        ])

        # Filter by amount threshold
        approvers = approvers.filtered(
            lambda u: u.approval_limit >= self.amount_total
        )

        return approvers

    def _check_account_access(self, account_id, operation):
        """Kiểm tra access cho specific account"""
        account = self.env['account.account'].browse(account_id)

        # Check user's account restrictions
        user_accounts = self.env.user.account_restriction_ids.mapped('account_id')

        if user_accounts:
            if account not in user_accounts:
                return False

        # Check account type restrictions
        if account.internal_type == 'liability' and not self.env.user.can_access_liability_accounts:
            return False

        if account.internal_type == 'equity' and not self.env.user.can_access_equity_accounts:
            return False

        return True

class AccountApproval(models.Model):
    _name = 'account.approval'
    _description = 'Accounting Entry Approval'
    _order = 'create_date desc'

    move_id = fields.Many2one('account.move', string='Journal Entry', required=True)
    requested_by = fields.Many2one('res.users', string='Requested by', required=True)
    approver_ids = fields.Many2many('res.users', string='Approvers')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='pending')
    amount = fields.Float(string='Amount', required=True)
    reason = fields.Text(string='Rejection Reason')
    approval_date = fields.Datetime(string='Approval Date')
    approved_by = fields.Many2one('res.users', string='Approved by')

    def action_approve(self):
        """Approve entry"""
        self.write({
            'state': 'approved',
            'approval_date': fields.Datetime.now(),
            'approved_by': self.env.user.id
        })

        # Post the move
        self.move_id.action_post()

        # Send notification
        self.move_id.message_post(
            body=_('Entry approved and posted by %s') % self.env.user.name
        )

    def action_reject(self):
        """Reject entry"""
        if not self.reason:
            raise UserError(_('Please provide rejection reason'))

        self.write({'state': 'rejected'})

        # Send notification
        self.move_id.message_post(
            body=_('Entry rejected: %s') % self.reason
        )

# User Account Restrictions
class UserAccountRestriction(models.Model):
    _name = 'user.account.restriction'
    _description = 'User Account Access Restrictions'

    user_id = fields.Many2one('res.users', string='User', required=True)
    account_id = fields.Many2one('account.account', string='Account', required=True)
    access_type = fields.Selection([
        ('read_only', 'Read Only'),
        ('read_write', 'Read/Write'),
    ], string='Access Type', default='read_write')
```

## 📊 Performance Optimization

### 3. Database Optimization Strategies

```python
class AccountingPerformanceOptimizer(models.Model):
    _inherit = ['account.move', 'account.move.line']

    @api.model
    def optimize_database_performance(self):
        """Tối ưu database performance cho accounting"""
        # Create indexes cho performance-critical queries
        self._create_performance_indexes()

        # Optimize queries
        self._optimize_common_queries()

        # Cleanup old data
        self._cleanup_old_data()

        return True

    def _create_performance_indexes(self):
        """Tạo indexes cho performance optimization"""
        cr = self._cr

        # Indexes cho account.move
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_account_move_date_company ON account_move(date, company_id, state)",
            "CREATE INDEX IF NOT EXISTS idx_account_move_partner_journal ON account_move(partner_id, journal_id, state)",
            "CREATE INDEX IF NOT EXISTS idx_account_move_type_state ON account_move(move_type, state, date)",
            "CREATE INDEX IF NOT EXISTS idx_account_move_invoice_origin ON account_move(invoice_origin, state)",
        ]

        # Indexes cho account.move.line
        line_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_account_move_line_account_date ON account_move_line(account_id, date, company_id)",
            "CREATE INDEX IF NOT EXISTS idx_account_move_line_partner_account ON account_move_line(partner_id, account_id, reconcile)",
            "CREATE INDEX IF NOT EXISTS idx_account_move_line_move_state ON account_move_line(move_id, state)",
            "CREATE INDEX IF NOT EXISTS idx_account_move_line_reconcile ON account_move_line(reconcile, date)",
        ]

        # Indexes cho stock valuation layer (inventory integration)
        stock_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_stock_valuation_layer_product_date ON stock_valuation_layer(product_id, create_date, company_id)",
            "CREATE INDEX IF NOT EXISTS idx_stock_valuation_layer_remaining_qty ON stock_valuation_layer(remaining_qty, company_id)",
        ]

        all_indexes = indexes + line_indexes + stock_indexes

        for index_sql in all_indexes:
            try:
                cr.execute(index_sql)
            except Exception as e:
                _logger.warning('Failed to create index: %s', str(e))

    def _optimize_common_queries(self):
        """Tối ưu các queries phổ biến"""
        # Configure database parameters
        self._configure_database_parameters()

        # Optimize query patterns
        self._optimize_query_patterns()

    def _configure_database_parameters(self):
        """Cấu hình database parameters cho performance"""
        cr = self._cr

        # PostgreSQL performance parameters
        if cr._cnx.server_version_info()[0] == 'PostgreSQL':
            # Increase work_mem cho complex queries
            parameters = [
                "ALTER SYSTEM SET work_mem = '64MB'",
                "ALTER SYSTEM SET maintenance_work_mem = '256MB'",
                "ALTER SYSTEM SET checkpoint_completion_target = 0.9",
                "ALTER SYSTEM SET wal_buffers = '64MB'",
            ]

            for param in parameters:
                try:
                    cr.execute(param)
                except Exception as e:
                    _logger.warning('Failed to set parameter %s: %s', param, str(e))

    def _optimize_query_patterns(self):
        """Tối ưu patterns cho queries"""
        # Materialized views cho reporting
        self._create_materialized_views()

    def _create_materialized_views(self):
        """Tạo materialized views cho reporting"""
        cr = self._cr

        # Trial balance materialized view
        mv_trial_balance = """
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_trial_balance AS
        SELECT
            a.id as account_id,
            a.code,
            a.name as account_name,
            COALESCE(SUM(CASE WHEN l.debit > 0 THEN l.debit ELSE 0 END), 0) as total_debit,
            COALESCE(SUM(CASE WHEN l.credit > 0 THEN l.credit ELSE 0 END), 0) as total_credit,
            COALESCE(SUM(l.balance), 0) as balance,
            l.company_id,
            MAX(l.date) as last_transaction_date
        FROM account_move_line l
        JOIN account_account a ON l.account_id = a.id
        WHERE l.state != 'cancel'
        GROUP BY a.id, a.code, a.name, l.company_id
        """

        # Inventory valuation materialized view
        mv_inventory_valuation = """
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_inventory_valuation AS
        SELECT
            p.id as product_id,
            p.default_code,
            p.name as product_name,
            c.id as category_id,
            c.name as category_name,
            COALESCE(SUM(svl.quantity * svl.unit_cost), 0) as total_value,
            COALESCE(SUM(svl.quantity), 0) as total_quantity,
            svl.company_id
        FROM stock_valuation_layer svl
        JOIN product_product p ON svl.product_id = p.id
        JOIN product_category c ON p.categ_id = c.id
        WHERE svl.remaining_qty > 0
        GROUP BY p.id, p.default_code, p.name, c.id, c.name, svl.company_id
        """

        materialized_views = [mv_trial_balance, mv_inventory_valuation]

        for mv_sql in materialized_views:
            try:
                cr.execute(mv_sql)
                # Create unique index for refresh
                cr.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_trial_balance_unique
                    ON mv_trial_balance(account_id, company_id)
                """)
                cr.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_inventory_valuation_unique
                    ON mv_inventory_valuation(product_id, company_id)
                """)
            except Exception as e:
                _logger.warning('Failed to create materialized view: %s', str(e))

    def _cleanup_old_data(self):
        """Cleanup old data để improve performance"""
        cr = self._cr

        # Archive old moves
        archive_days = self.env.company.accounting_archive_days or 1095  # 3 years default

        # Archive old journal entries
        archive_sql = """
        UPDATE account_move
        SET state = 'archived'
        WHERE date < NOW() - INTERVAL '%s days'
        AND state = 'posted'
        AND company_id = %s
        """ % (archive_days, self.env.company.id)

        try:
            cr.execute(archive_sql)
        except Exception as e:
            _logger.warning('Failed to archive old moves: %s', str(e))

        # Cleanup old temporary files
        self._cleanup_temporary_files()

    def _cleanup_temporary_files(self):
        """Cleanup temporary files"""
        import os
        import tempfile

        temp_dir = tempfile.gettempdir()
        accounting_temp_dir = os.path.join(temp_dir, 'odoo_accounting_temp')

        if os.path.exists(accounting_temp_dir):
            try:
                # Remove files older than 7 days
                cutoff_time = time.time() - 7 * 24 * 60 * 60  # 7 days

                for filename in os.listdir(accounting_temp_dir):
                    file_path = os.path.join(accounting_temp_dir, filename)
                    if os.path.isfile(file_path):
                        if os.path.getmtime(file_path) < cutoff_time:
                            os.remove(file_path)
            except Exception as e:
                _logger.warning('Failed to cleanup temporary files: %s', str(e))

# Query Optimization Decorators
def optimize_query(func):
    """Decorator để optimize accounting queries"""
    def wrapper(self, *args, **kwargs):
        # Enable query optimization
        original_context = self.env.context
        optimized_context = dict(original_context)
        optimized_context['prefetch_fields'] = False

        # Use optimized context
        self = self.with_context(optimized_context)

        try:
            result = func(self, *args, **kwargs)
        finally:
            # Restore original context
            self = self.with_context(original_context)

        return result

    return wrapper

class AccountMove(models.Model):
    _inherit = 'account.move'

    @optimize_query
    def get_trial_balance_data(self, date_from, date_to):
        """Optimized trial balance query"""
        self._cr.execute("""
            SELECT
                aa.code,
                aa.name,
                COALESCE(SUM(CASE WHEN aml.debit > 0 THEN aml.debit ELSE 0 END), 0) as debit,
                COALESCE(SUM(CASE WHEN aml.credit > 0 THEN aml.credit ELSE 0 END), 0) as credit,
                COALESCE(SUM(aml.balance), 0) as balance
            FROM account_move_line aml
            JOIN account_account aa ON aml.account_id = aa.id
            WHERE aml.date BETWEEN %s AND %s
            AND aml.state != 'cancel'
            AND aml.company_id = %s
            GROUP BY aa.id, aa.code, aa.name
            ORDER BY aa.code
        """, (date_from, date_to, self.env.company.id))

        return self._cr.dictfetchall()

    @api.model
    @optimize_query
    def get_balance_sheet_data(self, date):
        """Optimized balance sheet query"""
        self._cr.execute("""
            SELECT
                aa.internal_type,
                COALESCE(SUM(aml.balance), 0) as balance
            FROM account_move_line aml
            JOIN account_account aa ON aml.account_id = aa.id
            WHERE aml.date <= %s
            AND aml.state != 'cancel'
            AND aml.company_id = %s
            GROUP BY aa.internal_type
        """, (date, self.env.company.id))

        return self._cr.dictfetchall()
```

## 🏪 Business Process Automation

### 4. Workflow Automation Engine

```python
class AccountingWorkflowEngine(models.Model):
    _name = 'accounting.workflow.engine'
    _description = 'Accounting Workflow Automation Engine'

    name = fields.Char(string='Workflow Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    trigger_model = fields.Selection([
        ('account.move', 'Account Move'),
        ('stock.picking', 'Stock Picking'),
        ('mrp.production', 'Manufacturing Order'),
        ('sale.order', 'Sales Order'),
        ('purchase.order', 'Purchase Order'),
    ], string='Trigger Model', required=True)
    trigger_condition = fields.Text(string='Trigger Condition',
                                   help='Python expression that evaluates to True/False')
    action_sequence = fields.One2many('accounting.workflow.action', 'workflow_id',
                                     string='Actions')

    def evaluate_trigger(self, record):
        """Evaluate trigger condition"""
        if not self.trigger_condition:
            return True

        # Create safe evaluation context
        context = {
            'record': record,
            'env': self.env,
            'user': self.env.user,
            'company': self.env.company,
            'today': fields.Date.today(),
            'now': fields.Datetime.now(),
        }

        try:
            return eval(self.trigger_condition, {'__builtins__': {}}, context)
        except Exception as e:
            _logger.error('Error evaluating workflow trigger: %s', str(e))
            return False

    def execute_actions(self, record):
        """Execute all actions in sequence"""
        for action in self.action_sequence.sorted('sequence'):
            if not action.active:
                continue

            try:
                action.execute_action(record)
            except Exception as e:
                _logger.error('Error executing workflow action %s: %s',
                           action.name, str(e))
                # Continue with next action if fail_fast is False
                if action.fail_fast:
                    raise

class AccountingWorkflowAction(models.Model):
    _name = 'accounting.workflow.action'
    _description = 'Accounting Workflow Action'

    workflow_id = fields.Many2one('accounting.workflow.engine', string='Workflow')
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Action Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    action_type = fields.Selection([
        ('create_journal_entry', 'Create Journal Entry'),
        ('send_notification', 'Send Notification'),
        ('create_task', 'Create Task'),
        ('update_record', 'Update Record'),
        ('call_method', 'Call Method'),
        ('validate_record', 'Validate Record'),
    ], string='Action Type', required=True)
    fail_fast = fields.Boolean(string='Stop on Error', default=True)
    parameters = fields.Text(string='Parameters', help='JSON format')

    def execute_action(self, trigger_record):
        """Execute the action"""
        parameters = self._get_parameters()

        if self.action_type == 'create_journal_entry':
            return self._create_journal_entry(trigger_record, parameters)
        elif self.action_type == 'send_notification':
            return self._send_notification(trigger_record, parameters)
        elif self.action_type == 'create_task':
            return self._create_task(trigger_record, parameters)
        elif self.action_type == 'update_record':
            return self._update_record(trigger_record, parameters)
        elif self.action_type == 'call_method':
            return self._call_method(trigger_record, parameters)
        elif self.action_type == 'validate_record':
            return self._validate_record(trigger_record, parameters)

    def _get_parameters(self):
        """Parse parameters from JSON"""
        if not self.parameters:
            return {}

        try:
            import json
            return json.loads(self.parameters)
        except json.JSONDecodeError:
            _logger.error('Invalid JSON parameters for workflow action %s', self.name)
            return {}

    def _create_journal_entry(self, trigger_record, params):
        """Create journal entry action"""
        entry_vals = {
            'journal_id': params.get('journal_id'),
            'date': params.get('date', fields.Date.today()),
            'ref': params.get('ref', 'Auto-generated from workflow'),
            'move_type': params.get('move_type', 'entry'),
            'line_ids': [],
        }

        # Create lines
        for line_params in params.get('lines', []):
            line_vals = {
                'account_id': line_params.get('account_id'),
                'debit': line_params.get('debit', 0),
                'credit': line_params.get('credit', 0),
                'name': line_params.get('name'),
                'partner_id': line_params.get('partner_id'),
                'quantity': line_params.get('quantity', 0),
                'price_unit': line_params.get('price_unit', 0),
            }

            if trigger_record._name == 'stock.picking':
                # Link to stock picking if applicable
                line_vals['stock_move_id'] = trigger_record.move_ids[0].id if trigger_record.move_ids else False

            entry_vals['line_ids'].append((0, 0, line_vals))

        entry = self.env['account.move'].create(entry_vals)

        if params.get('auto_post', False):
            entry.action_post()

        return entry

    def _send_notification(self, trigger_record, params):
        """Send notification action"""
        # Send email notification
        template = params.get('email_template')
        if template:
            template_id = self.env.ref(template, raise_if_not_found=False)
            if template_id:
                template_id.send_mail(trigger_record.id)

        # Send in-app notification
        partner_ids = params.get('partner_ids', [])
        if partner_ids:
            self.env['mail.message'].create({
                'message_type': 'notification',
                'subtype_id': self.env.ref('mail.mt_comment').id,
                'subject': params.get('subject', 'Workflow Notification'),
                'body': params.get('body', 'Workflow action triggered'),
                'model': trigger_record._name,
                'res_id': trigger_record.id,
                'partner_ids': [(6, 0, partner_ids)],
            })

        return True

    def _create_task(self, trigger_record, params):
        """Create task action"""
        task_vals = {
            'name': params.get('task_name'),
            'description': params.get('description'),
            'user_id': params.get('assigned_to'),
            'project_id': params.get('project_id'),
            'date_deadline': params.get('deadline'),
            'priority': params.get('priority', '0'),
        }

        # Link to trigger record if possible
        if hasattr(trigger_record, 'activity_ids'):
            activity_vals = {
                'summary': params.get('task_name'),
                'note': params.get('description'),
                'activity_type_id': params.get('activity_type'),
                'user_id': params.get('assigned_to'),
                'date_deadline': params.get('deadline'),
            }
            trigger_record.activity_schedule(**activity_vals)

        return True

    def _update_record(self, trigger_record, params):
        """Update record action"""
        update_vals = {}

        for field, value in params.items():
            if hasattr(trigger_record, field):
                update_vals[field] = value

        if update_vals:
            trigger_record.write(update_vals)

        return True

    def _call_method(self, trigger_record, params):
        """Call method action"""
        method_name = params.get('method_name')
        method_args = params.get('args', [])

        if hasattr(trigger_record, method_name):
            method = getattr(trigger_record, method_name)
            if callable(method):
                return method(*method_args)

        return False

    def _validate_record(self, trigger_record, params):
        """Validate record action"""
        validation_rules = params.get('validation_rules', [])

        for rule in validation_rules:
            field_name = rule.get('field')
            operator = rule.get('operator')
            value = rule.get('value')

            if hasattr(trigger_record, field_name):
                field_value = getattr(trigger_record, field_name)

                if operator == '==' and field_value != value:
                    raise ValidationError(_('Validation failed: %s must equal %s') % (field_name, value))
                elif operator == '>=' and field_value < value:
                    raise ValidationError(_('Validation failed: %s must be >= %s') % (field_name, value))
                elif operator == '<=' and field_value > value:
                    raise ValidationError(_('Validation failed: %s must be <= %s') % (field_name, value))

        return True

# Predefined Workflows for Supply Chain
class SupplyChainWorkflows(models.Model):
    _name = 'supply.chain.workflows'
    _description = 'Predefined Supply Chain Accounting Workflows'

    @api.model
    def create_standard_workflows(self):
        """Tạo standard workflows cho supply chain"""
        # Workflow 1: Automatic Inventory Valuation
        self._create_inventory_valuation_workflow()

        # Workflow 2: Purchase Order Invoice Creation
        self._create_purchase_invoice_workflow()

        # Workflow 3: Manufacturing Cost Calculation
        self._create_manufacturing_cost_workflow()

        # Workflow 4: Sales COGS Recognition
        self._create_sales_cogs_workflow()

    def _create_inventory_valuation_workflow(self):
        """Tạo workflow cho inventory valuation"""
        workflow = self.env['accounting.workflow.engine'].create({
            'name': 'Automatic Inventory Valuation',
            'trigger_model': 'stock.picking',
            'trigger_condition': 'record.state == "done" and record.picking_type_id.code == "incoming"',
        })

        # Create journal entry for inventory receipt
        self.env['accounting.workflow.action'].create({
            'workflow_id': workflow.id,
            'sequence': 10,
            'name': 'Create Inventory Receipt Entry',
            'action_type': 'create_journal_entry',
            'parameters': json.dumps({
                'journal_id': 'stock_valuation_journal',
                'ref': 'Inventory Receipt - ${record.name}',
                'auto_post': True,
                'lines': [
                    {
                        'account_id': '${record.company_id.property_stock_account_input_categ_id.id}',
                        'debit': '${record._get_total_value()}',
                        'name': 'Inventory Receipt - ${record.name}',
                    },
                    {
                        'account_id': '${record.company_id.property_account_expense_categ_id.id}',
                        'credit': '${record._get_total_value()}',
                        'name': 'Inventory Receipt - ${record.name}',
                    }
                ]
            })
        })

    def _create_purchase_invoice_workflow(self):
        """Tạo workflow cho purchase invoice creation"""
        workflow = self.env['accounting.workflow.engine'].create({
            'name': 'Purchase Invoice Creation',
            'trigger_model': 'stock.picking',
            'trigger_condition': 'record.state == "done" and record.purchase_id and record.picking_type_id.code == "incoming"',
        })

        # Create supplier invoice
        self.env['accounting.workflow.action'].create({
            'workflow_id': workflow.id,
            'sequence': 10,
            'name': 'Create Supplier Invoice',
            'action_type': 'call_method',
            'parameters': json.dumps({
                'method_name': 'action_create_supplier_invoice',
                'args': []
            })
        })

        # Send notification to accounting team
        self.env['accounting.workflow.action'].create({
            'workflow_id': workflow.id,
            'sequence': 20,
            'name': 'Notify Accounting Team',
            'action_type': 'send_notification',
            'parameters': json.dumps({
                'subject': 'New Supplier Invoice Created',
                'body': 'Supplier invoice has been automatically created for purchase order: ${record.purchase_id.name}',
                'partner_ids': '${self.env["res.users"].search([("accounting_access_level", "in", ["full_access", "admin"])]).mapped("partner_id").ids}'
            })
        })

    def _create_manufacturing_cost_workflow(self):
        """Tạo workflow cho manufacturing cost calculation"""
        workflow = self.env['accounting.workflow.engine'].create({
            'name': 'Manufacturing Cost Calculation',
            'trigger_model': 'mrp.production',
            'trigger_condition': 'record.state == "done" and record._get_total_actual_cost() > 0',
        })

        # Create manufacturing cost journal entry
        self.env['accounting.workflow.action'].create({
            'workflow_id': workflow.id,
            'sequence': 10,
            'name': 'Create Manufacturing Cost Entry',
            'action_type': 'call_method',
            'parameters': json.dumps({
                'method_name': 'action_post_accounting_entries',
                'args': []
            })
        })

    def _create_sales_cogs_workflow(self):
        """Tạo workflow cho sales COGS recognition"""
        workflow = self.env['accounting.workflow.engine'].create({
            'name': 'Sales COGS Recognition',
            'trigger_model': 'stock.picking',
            'trigger_condition': 'record.state == "done" and record.picking_type_id.code == "outgoing" and record.sale_id',
        })

        # Create COGS entry
        self.env['accounting.workflow.action'].create({
            'workflow_id': workflow.id,
            'sequence': 10,
            'name': 'Create COGS Entry',
            'action_type': 'create_journal_entry',
            'parameters': json.dumps({
                'journal_id': 'sales_journal',
                'ref': 'COGS - ${record.sale_id.name}',
                'auto_post': True,
                'lines': [
                    {
                        'account_id': '${record.company_id.property_account_expense_categ_id.id}',
                        'debit': '${record._get_cogs_amount()}',
                        'name': 'COGS - ${record.sale_id.name}',
                    },
                    {
                        'account_id': '${record.company_id.property_stock_account_output_categ_id.id}',
                        'credit': '${record._get_cogs_amount()}',
                        'name': 'COGS - ${record.sale_id.name}',
                    }
                ]
            })
        })
```

## 🔍 Audit Trail and Compliance Monitoring

### 5. Comprehensive Audit System

```python
class AccountingAuditTrail(models.Model):
    _name = 'accounting.audit.trail'
    _description = 'Accounting Audit Trail'
    _order = 'create_date desc'

    res_id = fields.Integer(string='Record ID')
    res_model = fields.Char(string='Model')
    user_id = fields.Many2one('res.users', string='User', required=True)
    action = fields.Selection([
        ('create', 'Create'),
        ('write', 'Write'),
        ('unlink', 'Delete'),
        ('post', 'Post'),
        ('cancel', 'Cancel'),
        ('reconcile', 'Reconcile'),
    ], string='Action', required=True)
    timestamp = fields.Datetime(string='Timestamp', required=True, default=fields.Datetime.now)
    old_values = fields.Text(string='Old Values')
    new_values = fields.Text(string='New Values')
    change_description = fields.Text(string='Change Description')
    ip_address = fields.Char(string='IP Address')
    session_id = fields.Char(string='Session ID')

    @api.model
    def create_audit_log(self, record, action, old_values=None, new_values=None, description=None):
        """Tạo audit log entry"""
        if not record:
            return

        # Skip audit for certain models if configured
        if record._name in self.env['ir.config_parameter'].sudo().get_param('accounting.audit_excluded_models', '').split(','):
            return

        audit_vals = {
            'res_id': record.id,
            'res_model': record._name,
            'user_id': self.env.user.id,
            'action': action,
            'old_values': json.dumps(old_values) if old_values else None,
            'new_values': json.dumps(new_values) if new_values else None,
            'change_description': description,
            'ip_address': self._get_client_ip(),
            'session_id': self._get_session_id(),
        }

        return self.create(audit_vals)

    def _get_client_ip(self):
        """Lấy client IP address"""
        return self.env.httprequest.environ.get('HTTP_X_FORWARDED_FOR') or \
               self.env.httprequest.environ.get('REMOTE_ADDR')

    def _get_session_id(self):
        """Lấy session ID"""
        return self.env.session.sid

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def create(self, vals):
        """Override create với audit trail"""
        old_values = {}
        new_values = vals

        record = super().create(vals)

        # Create audit log
        self.env['accounting.audit.trail'].create_audit_log(
            record, 'create', old_values, new_values,
            f'Created {record.move_type} entry with amount {record.amount_total}'
        )

        return record

    def write(self, vals):
        """Override write với audit trail"""
        old_values = {}
        new_values = vals

        # Capture old values
        if self.exists():
            old_values = self.read()[0]

        result = super().write(vals)

        # Create audit log for each modified field
        for record in self:
            change_description = []
            for field in vals.keys():
                if hasattr(record, field):
                    old_val = old_values.get(field) if old_values else None
                    new_val = vals[field]
                    if old_val != new_val:
                        change_description.append(f'{field}: {old_val} → {new_val}')

            if change_description:
                self.env['accounting.audit.trail'].create_audit_log(
                    record, 'write', old_values, new_values,
                    f'Modified fields: {", ".join(change_description)}'
                )

        return result

    def unlink(self):
        """Override unlink với audit trail"""
        for record in self:
            self.env['accounting.audit.trail'].create_audit_log(
                record, 'unlink', {}, {},
                f'Deleted {record.move_type} entry with amount {record.amount_total}'
            )

        return super().unlink()

    def action_post(self):
        """Override posting với audit trail"""
        for record in self:
            self.env['accounting.audit.trail'].create_audit_log(
                record, 'post', {}, {},
                f'Posted {record.move_type} entry with amount {record.amount_total}'
            )

        return super().action_post()

    def action_cancel(self):
        """Override cancellation với audit trail"""
        for record in self:
            self.env['accounting.audit.trail'].create_audit_log(
                record, 'cancel', {}, {},
                f'Cancelled {record.move_type} entry with amount {record.amount_total}'
            )

        return super().action_cancel()

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def create(self, vals):
        """Override create với audit trail"""
        record = super().create(vals)
        self.env['accounting.audit.trail'].create_audit_log(
            record.move_id, 'create', {}, vals,
            f'Created line: {record.name} ({record.debit}/{record.credit})'
        )
        return record

    def write(self, vals):
        """Override write với audit trail"""
        # Capture old values
        old_values = self.read()[0]

        result = super().write(vals)

        # Check if reconciliation status changed
        if 'reconcile' in vals:
            if vals['reconcile'] and not old_values.get('reconcile'):
                action = 'reconcile'
            elif not vals['reconcile'] and old_values.get('reconcile'):
                action = 'unreconcile'
            else:
                action = 'write'
        else:
            action = 'write'

        self.env['accounting.audit.trail'].create_audit_log(
            self.move_id, action, old_values, vals,
            f'Modified line: {self.name}'
        )

        return result

# Compliance Monitoring System
class AccountingComplianceMonitor(models.Model):
    _name = 'accounting.compliance.monitor'
    _description = 'Accounting Compliance Monitoring'

    @api.model
    def check_compliance_rules(self):
        """Kiểm tra tất cả compliance rules"""
        violations = []

        # Check duplicate invoice numbers
        duplicate_violations = self._check_duplicate_invoices()
        violations.extend(duplicate_violations)

        # Check unauthorized entries
        unauthorized_violations = self._check_unauthorized_entries()
        violations.extend(unauthorized_violations)

        # Check missing documentation
        doc_violations = self._check_missing_documentation()
        violations.extend(doc_violations)

        # Check tax compliance
        tax_violations = self._check_tax_compliance()
        violations.extend(tax_violations)

        # Create compliance reports for violations
        if violations:
            self._create_compliance_violations(violations)

        return violations

    def _check_duplicate_invoices(self):
        """Kiểm tra trùng số hóa đơn"""
        cr = self._cr
        violations = []

        # Check duplicate invoice numbers by vendor
        cr.execute("""
            SELECT partner_id, invoice_origin, COUNT(*) as count
            FROM account_move
            WHERE move_type = 'in_invoice'
            AND state = 'posted'
            AND invoice_origin IS NOT NULL
            GROUP BY partner_id, invoice_origin
            HAVING COUNT(*) > 1
        """)

        for row in cr.fetchall():
            violations.append({
                'type': 'duplicate_invoice',
                'severity': 'high',
                'description': _('Duplicate invoice number %s for vendor %s') % (row[1], row[0]),
                'partner_id': row[0],
                'invoice_reference': row[1],
            })

        return violations

    def _check_unauthorized_entries(self):
        """Kiểm tra entries không được uỷ quyền"""
        cr = self._cr
        violations = []

        # Check entries created by unauthorized users
        cr.execute("""
            SELECT am.id, am.name, am.create_uid, am.create_date
            FROM account_move am
            JOIN res_users ru ON am.create_uid = ru.id
            LEFT JOIN res_groups_users rgu ON ru.id = rgu.uid
            LEFT JOIN res_groups rg ON rgu.gid = rg.id
            WHERE am.state = 'posted'
            AND rg.id IS NULL
            AND am.create_date >= NOW() - INTERVAL '7 days'
        """)

        for row in cr.fetchall():
            violations.append({
                'type': 'unauthorized_entry',
                'severity': 'high',
                'description': _('Entry %s created by unauthorized user') % row[1],
                'move_id': row[0],
                'user_id': row[2],
            })

        return violations

    def _check_missing_documentation(self):
        """Kiểm tra thiếu chứng từ"""
        violations = []

        # Check invoices without attachments
        invoices_without_docs = self.env['account.move'].search([
            ('move_type', 'in', ['out_invoice', 'in_invoice']),
            ('state', '=', 'posted'),
            ('attachment_ids', '=', False),
            ('invoice_date', '>=', fields.Date.today() - timedelta(days=30)),
        ])

        for invoice in invoices_without_docs:
            violations.append({
                'type': 'missing_documentation',
                'severity': 'medium',
                'description': _('Invoice %s missing supporting documents') % invoice.name,
                'move_id': invoice.id,
            })

        return violations

    def _check_tax_compliance(self):
        """Kiểm tra tuân thủ thuế"""
        violations = []

        # Check invalid VAT rates
        cr = self._cr
        cr.execute("""
            SELECT DISTINCT aml.id, aml.name, at.amount
            FROM account_move_line aml
            JOIN account_tax at ON at.id = ANY(aml.tax_ids)
            JOIN account_move am ON aml.move_id = am.id
            WHERE am.state = 'posted'
            AND at.amount NOT IN (0, 5, 10)
            AND am.date >= NOW() - INTERVAL '30 days'
        """)

        for row in cr.fetchall():
            violations.append({
                'type': 'invalid_tax_rate',
                'severity': 'medium',
                'description': _('Invalid VAT rate %s%% on line %s') % (row[2], row[1]),
                'line_id': row[0],
            })

        return violations

    def _create_compliance_violations(self, violations):
        """Tạo compliance violation records"""
        for violation in violations:
            self.env['accounting.compliance.violation'].create({
                'violation_type': violation['type'],
                'severity': violation['severity'],
                'description': violation['description'],
                'move_id': violation.get('move_id'),
                'partner_id': violation.get('partner_id'),
                'user_id': violation.get('user_id'),
                'detection_date': fields.Datetime.now(),
            })

class AccountingComplianceViolation(models.Model):
    _name = 'accounting.compliance.violation'
    _description = 'Accounting Compliance Violations'

    violation_type = fields.Selection([
        ('duplicate_invoice', 'Duplicate Invoice'),
        ('unauthorized_entry', 'Unauthorized Entry'),
        ('missing_documentation', 'Missing Documentation'),
        ('invalid_tax_rate', 'Invalid Tax Rate'),
        ('other', 'Other'),
    ], string='Violation Type', required=True)
    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], string='Severity', required=True)
    description = fields.Text(string='Description', required=True)
    move_id = fields.Many2one('account.move', string='Journal Entry')
    partner_id = fields.Many2one('res.partner', string='Partner')
    user_id = fields.Many2one('res.users', string='User')
    detection_date = fields.Datetime(string='Detection Date', required=True)
    resolution_status = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('false_positive', 'False Positive'),
    ], string='Resolution Status', default='pending')
    resolved_by = fields.Many2one('res.users', string='Resolved by')
    resolution_date = fields.Datetime(string='Resolution Date')
    resolution_notes = fields.Text(string='Resolution Notes')

    def action_resolve(self):
        """Resolve violation"""
        self.write({
            'resolution_status': 'resolved',
            'resolved_by': self.env.user.id,
            'resolution_date': fields.Datetime.now(),
        })

    def action_false_positive(self):
        """Mark as false positive"""
        self.write({
            'resolution_status': 'false_positive',
            'resolved_by': self.env.user.id,
            'resolution_date': fields.Datetime.now(),
        })
```

## 📈 Monitoring and Reporting

### 6. Real-time Financial Dashboard

```python
class FinancialDashboard(models.Model):
    _name = 'financial.dashboard'
    _description = 'Real-time Financial Dashboard'

    @api.model
    def get_dashboard_data(self, date_from=None, date_to=None):
        """Lấy dashboard data với real-time updates"""
        if not date_from:
            date_from = fields.Date.today().replace(day=1)  # First day of current month
        if not date_to:
            date_to = fields.Date.today()

        dashboard_data = {
            'summary_metrics': self._get_summary_metrics(date_from, date_to),
            'cash_flow': self._get_cash_flow_data(date_from, date_to),
            'revenue_analysis': self._get_revenue_analysis(date_from, date_to),
            'expense_analysis': self._get_expense_analysis(date_from, date_to),
            'inventory_metrics': self._get_inventory_metrics(),
            'accounts_receivable': self._get_accounts_receivable_data(),
            'accounts_payable': self._get_accounts_payable_data(),
            'profit_loss': self._get_profit_loss_data(date_from, date_to),
            'balance_sheet': self._get_balance_sheet_data(date_to),
            'alerts': self._get_financial_alerts(),
        }

        return dashboard_data

    def _get_summary_metrics(self, date_from, date_to):
        """Lấy summary metrics"""
        cr = self._cr

        # Total Revenue
        cr.execute("""
            SELECT COALESCE(SUM(credit), 0)
            FROM account_move_line aml
            JOIN account_move am ON aml.move_id = am.id
            JOIN account_account aa ON aml.account_id = aa.id
            WHERE am.date BETWEEN %s AND %s
            AND am.state = 'posted'
            AND aa.internal_type = 'income'
            AND am.company_id = %s
        """, (date_from, date_to, self.env.company.id))
        total_revenue = cr.fetchone()[0] or 0

        # Total Expenses
        cr.execute("""
            SELECT COALESCE(SUM(debit), 0)
            FROM account_move_line aml
            JOIN account_move am ON aml.move_id = am.id
            JOIN account_account aa ON aml.account_id = aa.id
            WHERE am.date BETWEEN %s AND %s
            AND am.state = 'posted'
            AND aa.internal_type = 'expense'
            AND am.company_id = %s
        """, (date_from, date_to, self.env.company.id))
        total_expenses = cr.fetchone()[0] or 0

        # Net Profit
        net_profit = total_revenue - total_expenses

        # Cash Balance
        cr.execute("""
            SELECT COALESCE(SUM(balance), 0)
            FROM account_move_line aml
            JOIN account_account aa ON aml.account_id = aa.id
            WHERE aa.internal_type = 'liquidity'
            AND aml.company_id = %s
            AND aml.state != 'cancel'
        """, (self.env.company.id,))
        cash_balance = cr.fetchone()[0] or 0

        # Accounts Receivable
        cr.execute("""
            SELECT COALESCE(SUM(balance), 0)
            FROM account_move_line aml
            JOIN account_account aa ON aml.account_id = aa.id
            WHERE aa.internal_type = 'receivable'
            AND aml.company_id = %s
            AND aml.state != 'cancel'
        """, (self.env.company.id,))
        accounts_receivable = cr.fetchone()[0] or 0

        # Accounts Payable
        cr.execute("""
            SELECT COALESCE(SUM(-balance), 0)
            FROM account_move_line aml
            JOIN account_account aa ON aml.account_id = aa.id
            WHERE aa.internal_type = 'payable'
            AND aml.company_id = %s
            AND aml.state != 'cancel'
        """, (self.env.company.id,))
        accounts_payable = cr.fetchone()[0] or 0

        return {
            'total_revenue': total_revenue,
            'total_expenses': total_expenses,
            'net_profit': net_profit,
            'cash_balance': cash_balance,
            'accounts_receivable': accounts_receivable,
            'accounts_payable': accounts_payable,
            'profit_margin': (net_profit / total_revenue * 100) if total_revenue > 0 else 0,
        }

    def _get_cash_flow_data(self, date_from, date_to):
        """Lấy cash flow data"""
        cr = self._cr

        # Operating Cash Flow
        cr.execute("""
            SELECT
                DATE_TRUNC('day', am.date) as date,
                COALESCE(SUM(CASE WHEN aa.internal_type = 'liquidity' AND aml.debit > 0 THEN aml.debit ELSE 0 END), 0) as cash_out,
                COALESCE(SUM(CASE WHEN aa.internal_type = 'liquidity' AND aml.credit > 0 THEN aml.credit ELSE 0 END), 0) as cash_in
            FROM account_move_line aml
            JOIN account_move am ON aml.move_id = am.id
            JOIN account_account aa ON aml.account_id = aa.id
            WHERE am.date BETWEEN %s AND %s
            AND am.state = 'posted'
            AND aa.internal_type = 'liquidity'
            AND am.company_id = %s
            GROUP BY DATE_TRUNC('day', am.date)
            ORDER BY date
        """, (date_from, date_to, self.env.company.id))

        cash_flow_data = []
        for row in cr.fetchall():
            cash_flow_data.append({
                'date': row[0].strftime('%Y-%m-%d'),
                'cash_in': row[2],
                'cash_out': row[1],
                'net_flow': row[2] - row[1]
            })

        return cash_flow_data

    def _get_revenue_analysis(self, date_from, date_to):
        """Lấy revenue analysis theo category và customer"""
        cr = self._cr

        # Revenue by Customer
        cr.execute("""
            SELECT
                rp.name as customer,
                COALESCE(SUM(aml.credit), 0) as revenue
            FROM account_move_line aml
            JOIN account_move am ON aml.move_id = am.id
            JOIN account_account aa ON aml.account_id = aa.id
            JOIN res_partner rp ON am.partner_id = rp.id
            WHERE am.date BETWEEN %s AND %s
            AND am.state = 'posted'
            AND aa.internal_type = 'income'
            AND am.company_id = %s
            GROUP BY rp.id, rp.name
            ORDER BY revenue DESC
            LIMIT 10
        """, (date_from, date_to, self.env.company.id))

        top_customers = []
        for row in cr.fetchall():
            top_customers.append({
                'customer': row[0],
                'revenue': row[1]
            })

        # Revenue by Product Category
        cr.execute("""
            SELECT
                pc.name as category,
                COALESCE(SUM(aml.credit), 0) as revenue
            FROM account_move_line aml
            JOIN account_move am ON aml.move_id = am.id
            JOIN account_account aa ON aml.account_id = aa.id
            JOIN product_product pp ON aml.product_id = pp.id
            JOIN product_category pc ON pp.categ_id = pc.id
            WHERE am.date BETWEEN %s AND %s
            AND am.state = 'posted'
            AND aa.internal_type = 'income'
            AND am.company_id = %s
            GROUP BY pc.id, pc.name
            ORDER BY revenue DESC
        """, (date_from, date_to, self.env.company.id))

        revenue_by_category = []
        for row in cr.fetchall():
            revenue_by_category.append({
                'category': row[0],
                'revenue': row[1]
            })

        return {
            'top_customers': top_customers,
            'revenue_by_category': revenue_by_category,
        }

    def _get_expense_analysis(self, date_from, date_to):
        """Lấy expense analysis"""
        cr = self._cr

        # Expenses by Category
        cr.execute("""
            SELECT
                aa.name as expense_category,
                COALESCE(SUM(aml.debit), 0) as expense
            FROM account_move_line aml
            JOIN account_move am ON aml.move_id = am.id
            JOIN account_account aa ON aml.account_id = aa.id
            WHERE am.date BETWEEN %s AND %s
            AND am.state = 'posted'
            AND aa.internal_type = 'expense'
            AND am.company_id = %s
            GROUP BY aa.id, aa.name
            ORDER BY expense DESC
        """, (date_from, date_to, self.env.company.id))

        expense_by_category = []
        for row in cr.fetchall():
            expense_by_category.append({
                'category': row[0],
                'expense': row[1]
            })

        return {
            'expense_by_category': expense_by_category,
        }

    def _get_inventory_metrics(self):
        """Lấy inventory metrics"""
        cr = self._cr

        # Inventory Value by Category
        cr.execute("""
            SELECT
                pc.name as category,
                COALESCE(SUM(svl.quantity * svl.unit_cost), 0) as value,
                COALESCE(SUM(svl.quantity), 0) as quantity
            FROM stock_valuation_layer svl
            JOIN product_product pp ON svl.product_id = pp.id
            JOIN product_category pc ON pp.categ_id = pc.id
            WHERE svl.remaining_qty > 0
            AND svl.company_id = %s
            GROUP BY pc.id, pc.name
            ORDER BY value DESC
        """, (self.env.company.id,))

        inventory_by_category = []
        for row in cr.fetchall():
            inventory_by_category.append({
                'category': row[0],
                'value': row[1],
                'quantity': row[2]
            })

        return {
            'inventory_by_category': inventory_by_category,
        }

    def _get_accounts_receivable_data(self):
        """Lấy accounts receivable data"""
        cr = self._cr

        # Aging Receivables
        cr.execute("""
            SELECT
                rp.name as customer,
                COALESCE(SUM(aml.balance), 0) as amount,
                CASE
                    WHEN am.date < CURRENT_DATE - INTERVAL '30 days' THEN '> 30'
                    WHEN am.date < CURRENT_DATE - INTERVAL '15 days' THEN '16-30'
                    WHEN am.date < CURRENT_DATE - INTERVAL '7 days' THEN '8-15'
                    ELSE '1-7'
                END as aging_bucket
            FROM account_move_line aml
            JOIN account_move am ON aml.move_id = am.id
            JOIN res_partner rp ON am.partner_id = rp.id
            WHERE aml.balance > 0
            AND aml.state != 'cancel'
            AND aml.company_id = %s
            GROUP BY rp.id, rp.name, aging_bucket
            ORDER BY amount DESC
        """, (self.env.company.id,))

        aging_receivables = {}
        for row in cr.fetchall():
            if row[2] not in aging_receivables:
                aging_receivables[row[2]] = []
            aging_receivables[row[2]].append({
                'customer': row[0],
                'amount': row[1]
            })

        return {
            'aging_receivables': aging_receivables,
        }

    def _get_accounts_payable_data(self):
        """Lấy accounts payable data"""
        cr = self._cr

        # Aging Payables
        cr.execute("""
            SELECT
                rp.name as vendor,
                COALESCE(SUM(-aml.balance), 0) as amount,
                CASE
                    WHEN am.date < CURRENT_DATE - INTERVAL '30 days' THEN '> 30'
                    WHEN am.date < CURRENT_DATE - INTERVAL '15 days' THEN '16-30'
                    WHEN am.date < CURRENT_DATE - INTERVAL '7 days' THEN '8-15'
                    ELSE '1-7'
                END as aging_bucket
            FROM account_move_line aml
            JOIN account_move am ON aml.move_id = am.id
            JOIN res_partner rp ON am.partner_id = rp.id
            WHERE aml.balance < 0
            AND aml.state != 'cancel'
            AND aml.company_id = %s
            GROUP BY rp.id, rp.name, aging_bucket
            ORDER BY amount DESC
        """, (self.env.company.id,))

        aging_payables = {}
        for row in cr.fetchall():
            if row[2] not in aging_payables:
                aging_payables[row[2]] = []
            aging_payables[row[2]].append({
                'vendor': row[0],
                'amount': row[1]
            })

        return {
            'aging_payables': aging_payables,
        }

    def _get_profit_loss_data(self, date_from, date_to):
        """Lấy profit & loss data"""
        cr = self._cr

        cr.execute("""
            SELECT
                aa.internal_type,
                COALESCE(SUM(aml.debit), 0) as total_debit,
                COALESCE(SUM(aml.credit), 0) as total_credit
            FROM account_move_line aml
            JOIN account_move am ON aml.move_id = am.id
            JOIN account_account aa ON aml.account_id = aa.id
            WHERE am.date BETWEEN %s AND %s
            AND am.state = 'posted'
            AND aa.internal_type IN ('income', 'expense')
            AND am.company_id = %s
            GROUP BY aa.internal_type
        """, (date_from, date_to, self.env.company.id))

        profit_loss = {}
        for row in cr.fetchall():
            if row[0] == 'income':
                profit_loss['revenue'] = row[2]  # Credit for income
            elif row[0] == 'expense':
                profit_loss['expenses'] = row[1]  # Debit for expenses

        profit_loss['net_profit'] = profit_loss.get('revenue', 0) - profit_loss.get('expenses', 0)

        return profit_loss

    def _get_balance_sheet_data(self, date_to):
        """Lấy balance sheet data"""
        cr = self._cr

        # Assets
        cr.execute("""
            SELECT COALESCE(SUM(balance), 0)
            FROM account_move_line aml
            JOIN account_account aa ON aml.account_id = aa.id
            WHERE aml.date <= %s
            AND aml.state != 'cancel'
            AND aa.internal_type = 'asset'
            AND aml.company_id = %s
        """, (date_to, self.env.company.id))
        total_assets = cr.fetchone()[0] or 0

        # Liabilities
        cr.execute("""
            SELECT COALESCE(SUM(-balance), 0)
            FROM account_move_line aml
            JOIN account_account aa ON aml.account_id = aa.id
            WHERE aml.date <= %s
            AND aml.state != 'cancel'
            AND aa.internal_type = 'liability'
            AND aml.company_id = %s
        """, (date_to, self.env.company.id))
        total_liabilities = cr.fetchone()[0] or 0

        # Equity
        cr.execute("""
            SELECT COALESCE(SUM(balance), 0)
            FROM account_move_line aml
            JOIN account_account aa ON aml.account_id = aa.id
            WHERE aml.date <= %s
            AND aml.state != 'cancel'
            AND aa.internal_type = 'equity'
            AND aml.company_id = %s
        """, (date_to, self.env.company.id))
        total_equity = cr.fetchone()[0] or 0

        return {
            'total_assets': total_assets,
            'total_liabilities': total_liabilities,
            'total_equity': total_equity,
        }

    def _get_financial_alerts(self):
        """Lấy financial alerts"""
        alerts = []

        # Low cash balance alert
        cash_balance = self._get_cash_balance()
        if cash_balance < self.env.company.min_cash_balance:
            alerts.append({
                'type': 'warning',
                'title': _('Low Cash Balance'),
                'message': _('Cash balance is below minimum threshold'),
                'value': cash_balance,
            })

        # Overdue receivables alert
        overdue_receivables = self._get_overdue_receivables()
        if overdue_receivables > 0:
            alerts.append({
                'type': 'warning',
                'title': _('Overdue Receivables'),
                'message': _('There are overdue customer payments'),
                'value': overdue_receivables,
            })

        # Expense budget alert
        budget_variance = self._check_budget_variance()
        if abs(budget_variance) > 0.15:  # 15% variance
            alerts.append({
                'type': 'error' if budget_variance > 0 else 'warning',
                'title': _('Budget Variance Alert'),
                'message': _('Expenses significantly over budget'),
                'value': budget_variance * 100,
            })

        return alerts

    def _get_cash_balance(self):
        """Lấy cash balance hiện tại"""
        cr = self._cr
        cr.execute("""
            SELECT COALESCE(SUM(balance), 0)
            FROM account_move_line aml
            JOIN account_account aa ON aml.account_id = aa.id
            WHERE aa.internal_type = 'liquidity'
            AND aml.state != 'cancel'
            AND aml.company_id = %s
        """, (self.env.company.id,))
        return cr.fetchone()[0] or 0

    def _get_overdue_receivables(self):
        """Lấy tổng receivables quá hạn"""
        cr = self._cr
        cr.execute("""
            SELECT COALESCE(SUM(balance), 0)
            FROM account_move_line aml
            JOIN account_move am ON aml.move_id = am.id
            WHERE aml.balance > 0
            AND am.date < CURRENT_DATE - INTERVAL '30 days'
            AND aml.state != 'cancel'
            AND aml.company_id = %s
        """, (self.env.company.id,))
        return cr.fetchone()[0] or 0

    def _check_budget_variance(self):
        """Kiểm tra variance so với budget"""
        # Implementation depends on budget module
        # Placeholder implementation
        return 0

# API endpoint cho real-time dashboard
class FinancialDashboardAPI(http.Controller):
    @http.route('/api/financial/dashboard', type='json', auth='user', methods=['GET'])
    def get_dashboard_data(self, **kwargs):
        """API endpoint cho financial dashboard data"""
        try:
            date_from = kwargs.get('date_from')
            date_to = kwargs.get('date_to')

            if date_from:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            if date_to:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()

            dashboard_data = request.env['financial.dashboard'].get_dashboard_data(date_from, date_to)
            return json.dumps(dashboard_data)
        except Exception as e:
            return json.dumps({'error': str(e)})
```

---

**Module Status**: ✅ **COMPLETED**
**File Size**: ~12,000 từ
**Language**: Tiếng Việt
**Target Audience**: Developers, Accountants, Financial Managers, Compliance Officers
**Completion**: 2025-11-08

*File này cung cấp comprehensive best practices cho accounting module, bao gồm Vietnamese accounting standards compliance, advanced security controls, performance optimization, workflow automation, audit trail systems, và real-time financial monitoring với Vietnamese regulatory requirements.*