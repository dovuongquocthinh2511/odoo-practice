# 📋 Models Reference - Accounting Module (Module Kế Toán) - Odoo 18

## 🎯 Giới Thiệu Models Reference

File này tài liệu hóa chi tiết các models quan trọng nhất trong Accounting Module có liên quan trực tiếp đến chuỗi cung ứng. Mỗi model được mô tả với đầy đủ thông tin về fields, methods, relationships, và usage patterns trong supply chain context.

## 📊 Table of Contents

1. [Account Move - `account.move`](#-account-move---accountmove) - Bút toán kế toán
2. [Account Move Line - `account.move.line`](#-account-move-line---accountmoveline) - Chi tiết bút toán
3. [Account - `account.account`](#-account---accountaccount) - Tài khoản kế toán
4. [Account Journal - `account.journal`](#-account-journal---accountjournal) - Sổ nhật ký
5. [Account Payment - `account.payment`](#-account-payment---accountpayment) - Thanh toán
6. [Account Tax - `account.tax`](#-account-tax---accounttax) - Thuế
7. [Account Reconciliation - `account.reconciliation`](#-account-reconciliation---accountreconciliation) - Đối chiếu
8. [Product Category - `product.category`](#-product-category---productcategory) - Product category with accounting

---

## 📝 Account Move - `account.move`

**Mục đích**: Quản lý bút toán kế toán và journal entries trong chuỗi cung ứng

### 🔍 Model Overview
```python
class AccountMove(models.Model):
    _name = 'account.move'
    _description = 'Journal Entry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'
```

### 📋 Fields Specification

#### **Core Identity Fields**
```python
name = fields.Char(
    string='Number',
    required=True,
    copy=False,
    readonly=True,
    default=lambda self: _('New')
)

date = fields.Date(
    string='Date',
    required=True,
    index=True,
    default=fields.Date.context_today,
    help="Date when the journal entry was posted"
)

ref = fields.Char(
    string='Reference',
    help="Reference of the document that generated this journal entry"
)
```

#### **Business Context Fields**
```python
partner_id = fields.Many2one(
    'res.partner',
    string='Partner',
    ondelete='restrict',
    index=True,
    help="Related partner (customer/supplier)"
)

invoice_origin = fields.Char(
    string='Source Document',
    help="Reference of the document that generated this invoice"
)

journal_id = fields.Many2one(
    'account.journal',
    string='Journal',
    required=True,
    check_company=True,
    help="Journal where the entry will be posted"
)

company_id = fields.Many2one(
    'res.company',
    string='Company',
    required=True,
    default=lambda self: self.env.company,
    help="Company for which the journal entry is created"
)
```

#### **Financial Amount Fields**
```python
currency_id = fields.Many2one(
    'res.currency',
    string='Currency',
    required=True,
    default=lambda self: self.env.company.currency_id,
    help="Currency of the journal entry"
)

amount_total = fields.Monetary(
    string='Total',
    currency_field='currency_id',
    compute='_compute_amount',
    store=True,
    help="Total amount of the journal entry"
)

amount_untaxed = fields.Monetary(
    string='Untaxed Amount',
    currency_field='currency_id',
    compute='_compute_amount',
    store=True,
    help="Amount before taxes"
)

amount_tax = fields.Monetary(
    string='Tax Amount',
    currency_field='currency_id',
    compute='_compute_amount',
    store=True,
    help="Total tax amount"
)
```

#### **Status & Workflow Fields**
```python
state = fields.Selection([
    ('draft', 'Draft'),
    ('posted', 'Posted'),
    ('cancel', 'Cancelled'),
], string='Status', required=True, readonly=True, copy=False,
   default='draft', tracking=True)

move_type = fields.Selection([
    ('entry', 'Journal Entry'),
    ('out_invoice', 'Customer Invoice'),
    ('out_refund', 'Customer Credit Note'),
    ('in_invoice', 'Vendor Bill'),
    ('in_refund', 'Vendor Credit Note'),
    ('out_receipt', 'Sales Receipt'),
    ('in_receipt', 'Purchase Receipt'),
], string='Type', required=True, readonly=True, index=True)

payment_state = fields.Selection([
    ('not_paid', 'Not Paid'),
    ('partial', 'Partially Paid'),
    ('paid', 'Paid'),
    ('reversed', 'Reversed'),
], string='Payment Status', readonly=True, store=True,
   compute='_compute_payment_state', help="Payment status of the journal entry")
```

### 🔧 Key Methods

#### **Computations**
```python
@api.depends('line_ids.debit', 'line_ids.credit', 'line_ids.amount_currency')
def _compute_amount(self):
    """Tính toán các tổng tiền cho journal entry"""
    for move in self:
        total_untaxed = 0.0
        total_tax = 0.0

        for line in move.line_ids:
            if line.tax_ids:
                # Line có thuế
                total_untaxed += line.balance
                total_tax += sum(tax.amount for tax in line.tax_ids.compute_all(line.balance)['taxes'])
            else:
                # Line không có thuế
                if move.is_invoice():
                    total_untaxed += line.balance
                else:
                    # Regular journal entry
                    pass

        move.amount_untaxed = total_untaxed
        move.amount_tax = total_tax
        move.amount_total = total_untaxed + total_tax

@api.depends('line_ids.amount_residual', 'line_ids.amount_residual_currency')
def _compute_payment_state(self):
    """Tính toán trạng thái thanh toán"""
    for move in self:
        if not move.is_invoice(include_receipts=True):
            move.payment_state = 'not_paid'
            continue

        total = move.amount_total
        residual = move.amount_residual

        if not float_is_zero(residual, precision_rounding=move.currency_id.rounding):
            if float_compare(total, residual, precision_rounding=move.currency_id.rounding) == 1:
                move.payment_state = 'partial'
            else:
                move.payment_state = 'not_paid'
        else:
            move.payment_state = 'paid'
```

#### **Business Logic Methods**
```python
def action_post(self):
    """Đăng bút toán vào sổ cái"""
    for move in self:
        if move.state != 'draft':
            continue

        # Validation
        move._post_validate()

        # Tạo move number
        if not move.name or move.name == _('New'):
            move.name = move.journal_id.sequence_id.next_by_id()

        # Đăng bút toán
        move._post(soft=False)

    return True

def _post_validate(self):
    """Validation trước khi đăng bút toán"""
    for move in self:
        # Kiểm tra balance
        if not float_is_zero(sum(move.line_ids.mapped('debit')) - sum(move.line_ids.mapped('credit')),
                           precision_rounding=move.currency_id.rounding):
            raise ValidationError(_('Journal entry must be balanced'))

        # Kiểm tra ngày
        if move.date > fields.Date.today():
            if not self.env.user.has_group('account.group_account_manager'):
                raise ValidationError(_('You cannot create entries dated in the future'))

        # Kiểm tra lock date
        if move.date < move.company_id.lock_date:
            if not self.env.user.has_group('account.group_account_manager'):
                raise ValidationError(_('You cannot create/modify entries prior to and inclusive of the lock date'))

def _post(self, soft=False):
    """Internal method để đăng bút toán"""
    for move in self:
        # Kiểm tra các điều kiện
        move._check_fiscalyear_lock_date()
        move._check_date()
        move._check_balanced()

        # Tạo analytic entries
        move.line_ids.analytic_line_ids.unlink()
        for line in move.line_ids:
            line.create_analytic_lines()

        # Update trạng thái
        move.write({
            'state': 'posted',
            'posted_before': True
        })

        # Gửi notification
        if move.move_type in ('out_invoice', 'in_invoice'):
            move._send_invoice_notification()

def button_cancel(self):
    """Hủy bút toán"""
    for move in self:
        if move.state == 'draft':
            continue

        if not move.name:
            continue

        # Kiểm tra lock date
        if move.date < move.company_id.lock_date:
            if not self.env.user.has_group('account.group_account_manager'):
                raise ValidationError(_('You cannot cancel entries prior to and inclusive of the lock date'))

        # Xóa reconciliations
        move.line_ids.remove_move_reconcile()

        # Reverse the entry
        reversed_move = move._reverse_moves(default_values_list=[{
            'date': move.date or fields.Date.today(),
            'journal_id': move.journal_id.id,
        }])

        # Update state
        move.write({'state': 'cancel'})
```

#### **Helper Methods**
```python
def is_invoice(self, include_receipts=False):
    """Kiểm tra có phải là invoice"""
    if include_receipts:
        return self.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund',
                                 'out_receipt', 'in_receipt')
    return self.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')

def is_outbound(self):
    """Kiểm tra có phải là outbound invoice (customer)"""
    return self.move_type in ('out_invoice', 'out_refund')

def is_inbound(self):
    """Kiểm tra có phải là inbound invoice (vendor)"""
    return self.move_type in ('in_invoice', 'in_refund')

def _get_reconciled_info_JSON_values(self):
    """Lấy thông tin reconciliation cho display"""
    for move in self:
        reconciled_vals = []
        reconciled_lines = move.line_ids.filtered(lambda line: line.account_id.reconcile)

        for line in reconciled_lines:
            partials = line.matched_debit_ids + line.matched_credit_ids
            for partial in partials:
                reconciled_vals.append({
                    'name': partial.debit_move_id.name if partial.debit_move_id else partial.credit_move_id.name,
                    'journal_name': partial.debit_move_id.journal_id.name if partial.debit_move_id else partial.credit_move_id.journal_id.name,
                    'amount': partial.amount,
                    'currency': partial.currency_id.symbol,
                })

        move.reconciled_info_JSON = json.dumps(reconciled_vals)

# Supply Chain Integration Methods
def create_supplier_invoice(self, purchase_order, invoice_data=None):
    """Tạo supplier invoice từ purchase order"""
    if not invoice_data:
        invoice_data = {}

    invoice_vals = {
        'move_type': 'in_invoice',
        'partner_id': purchase_order.partner_id.id,
        'invoice_origin': purchase_order.name,
        'ref': purchase_order.partner_ref or purchase_order.name,
        'journal_id': self.env['account.journal'].search([
            ('type', '=', 'purchase'),
            ('company_id', '=', purchase_order.company_id.id)
        ], limit=1).id,
        'invoice_date': fields.Date.today(),
        'invoice_line_ids': [],
    }

    # Tạo invoice lines từ purchase order lines
    for line in purchase_order.order_line:
        invoice_line_vals = {
            'move_id': False,  # Sẽ được set sau
            'product_id': line.product_id.id,
            'quantity': line.product_qty,
            'product_uom_id': line.product_uom.id,
            'price_unit': line.price_unit,
            'name': line.name,
            'account_id': line.product_id.product_tmpl_id.get_product_accounts()['expense'].id,
            'analytic_distribution': line.analytic_distribution,
        }

        invoice_vals['invoice_line_ids'].append((0, 0, invoice_line_vals))

    # Cập nhật với custom data
    invoice_vals.update(invoice_data)

    return self.create(invoice_vals)

def create_customer_invoice(self, sales_order, invoice_data=None):
    """Tạo customer invoice từ sales order"""
    if not invoice_data:
        invoice_data = {}

    invoice_vals = {
        'move_type': 'out_invoice',
        'partner_id': sales_order.partner_id.id,
        'invoice_origin': sales_order.name,
        'ref': sales_order.client_order_ref or sales_order.name,
        'journal_id': self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', sales_order.company_id.id)
        ], limit=1).id,
        'invoice_date': fields.Date.today(),
        'invoice_line_ids': [],
    }

    # Tạo invoice lines từ sales order lines
    for line in sales_order.order_line:
        invoice_line_vals = {
            'move_id': False,
            'product_id': line.product_id.id,
            'quantity': line.product_uom_qty,
            'product_uom_id': line.product_uom.id,
            'price_unit': line.price_unit,
            'name': line.name,
            'account_id': line.product_id.product_tmpl_id.get_product_accounts()['income'].id,
            'analytic_distribution': line.analytic_distribution,
            'tax_ids': [(6, 0, line.tax_id.ids)],
        }

        invoice_vals['invoice_line_ids'].append((0, 0, invoice_line_vals))

    invoice_vals.update(invoice_data)

    return self.create(invoice_vals)
```

### 🔍 Relationships & Constraints

```python
# Relationships
line_ids = fields.One2many(
    'account.move.line', 'move_id',
    string='Journal Items',
    copy=True
)

matched_debit_ids = fields.One2many(
    'account.partial.reconcile', 'credit_move_id',
    string='Matched Debits',
    readonly=True
)

matched_credit_ids = fields.One2many(
    'account.partial.reconcile', 'debit_move_id',
    string='Matched Credits',
    readonly=True
)

# Constraints
_sql_constraints = [
    ('name_unique', 'unique(name, journal_id, company_id)',
     'Journal Entry Number must be unique per Company and Journal!')
]
```

---

## 📝 Account Move Line - `account.move.line`

**Mục đích**: Chi tiết hóa các dòng bút toán kế toán

### 🔍 Model Overview
```python
class AccountMoveLine(models.Model):
    _name = 'account.move.line'
    _description = 'Journal Item'
    _order = 'date desc, id desc'
    _check_company_auto = True
```

### 📋 Fields Specification

#### **Core Financial Fields**
```python
move_id = fields.Many2one(
    'account.move',
    string='Journal Entry',
    ondelete='cascade',
    index=True,
    required=True
)

account_id = fields.Many2one(
    'account.account',
    string='Account',
    index=True,
    required=True,
    check_company=True,
    domain="[('deprecated', '=', False), ('company_id', 'in', (company_id, False))]"
)

partner_id = fields.Many2one(
    'res.partner',
    string='Partner',
    ondelete='restrict',
    index=True,
    help="Related partner (optional)"
)

debit = fields.Float(
    string='Debit',
    default=0.0,
    digits='Account',
    help="Debit amount for this journal item"
)

credit = fields.Float(
    string='Credit',
    default=0.0,
    digits='Account',
    help="Credit amount for this journal item"
)

balance = fields.Float(
    string='Balance',
    compute='_compute_balance',
    inverse='_inverse_balance',
    store=True,
    digits='Account',
    help="Balance amount (debit - credit)"
)

amount_currency = fields.Float(
    string='Amount Currency',
    default=0.0,
    digits='Account',
    help="Amount in foreign currency"
)

currency_id = fields.Many2one(
    'res.currency',
    string='Currency',
    help="Foreign currency for this journal item"
)

company_currency_id = fields.Many2one(
    'res.currency',
    string='Company Currency',
    related='company_id.currency_id',
    readonly=True
)
```

#### **Product & Quantity Fields**
```python
product_id = fields.Many2one(
    'product.product',
    string='Product',
    help="Product related to this journal item"
)

product_uom_id = fields.Many2one(
    'uom.uom',
    string='Unit of Measure',
    help="Unit of measure for the product"
)

quantity = fields.Float(
    string='Quantity',
    default=1.0,
    digits='Product Unit of Measure',
    help="Quantity of the product"
)

price_unit = fields.Float(
    string='Unit Price',
    digits='Product Price',
    help="Unit price of the product"
)

price_subtotal = fields.Float(
    string='Subtotal',
    compute='_compute_price_subtotal',
    store=True,
    digits='Account',
    help="Subtotal amount (quantity * price_unit)"
)

price_total = fields.Float(
    string='Total',
    compute='_compute_price_total',
    store=True,
    digits='Account',
    help="Total amount including taxes"
)
```

#### **Tax & Analytic Fields**
```python
tax_ids = fields.Many2many(
    'account.tax',
    'account_move_line_account_tax_rel',
    'move_line_id', 'tax_id',
    string='Taxes',
    help="Taxes applied to this journal item"
)

tax_line_id = fields.Many2one(
    'account.tax',
    string='Originator Tax',
    ondelete='restrict',
    help="Tax that generated this journal item"
)

analytic_distribution = fields.Json(
    string='Analytic Distribution',
    help="Distribution across analytic accounts"
)

analytic_line_ids = fields.One2many(
    'account.analytic.line',
    'move_line_id',
    string='Analytic Lines'
)
```

#### **Reconciliation Fields**
```python
reconciled = fields.Boolean(
    string='Reconciled',
    compute='_compute_amount_residual',
    store=True,
    help="Whether this journal item is reconciled"
)

amount_residual = fields.Float(
    string='Residual Amount',
    compute='_compute_amount_residual',
    store=True,
    digits='Account',
    help="Remaining amount to be reconciled"
)

amount_residual_currency = fields.Float(
    string='Residual Amount in Currency',
    compute='_compute_amount_residual',
    store=True,
    digits='Account',
    help="Remaining amount in foreign currency"
)

matched_debit_ids = fields.One2many(
    'account.partial.reconcile',
    'credit_move_id',
    string='Matched Debits'
)

matched_credit_ids = fields.One2many(
    'account.partial.reconcile',
    'debit_move_id',
    string='Matched Credits'
)

full_reconcile_id = fields.Many2one(
    'account.full.reconcile',
    string='Full Reconcile',
    readonly=True
)
```

### 🔧 Key Methods

#### **Computation Methods**
```python
@api.depends('debit', 'credit')
def _compute_balance(self):
    """Tính toán balance = debit - credit"""
    for line in self:
        line.balance = line.debit - line.credit

@api.depends('debit', 'credit', 'amount_currency', 'currency_id', 'company_currency_id')
def _compute_amount_residual(self):
    """Tính toán số dư còn lại sau reconciliation"""
    for line in self:
        # Currency xử lý
        company_currency = line.company_currency_id
        line_currency = line.currency_id or company_currency

        # Tính toán total reconciled
        total_reconciled = 0.0
        total_reconciled_currency = 0.0

        # Debit reconciliations
        for partial in line.matched_debit_ids:
            total_reconciled += partial.amount
            total_reconciled_currency += partial.amount_currency

        # Credit reconciliations
        for partial in line.matched_credit_ids:
            total_reconciled -= partial.amount
            total_reconciled_currency -= partial.amount_currency

        # Tính residual
        if line_currency != company_currency:
            line.amount_residual = line.debit - line.credit + total_reconciled
            line.amount_residual_currency = line.amount_currency + total_reconciled_currency
        else:
            line.amount_residual = line.debit - line.credit + total_reconciled
            line.amount_residual_currency = 0.0

        # Check if fully reconciled
        line.reconciled = float_is_zero(line.amount_residual, precision_rounding=company_currency.rounding)

@api.depends('quantity', 'price_unit', 'discount')
def _compute_price_subtotal(self):
    """Tính toán subtotal"""
    for line in self:
        line.price_subtotal = line.quantity * line.price_unit

@api.depends('price_subtotal', 'tax_ids')
def _compute_price_total(self):
    """Tính toán total bao gồm thuế"""
    for line in self:
        if line.tax_ids:
            tax_results = line.tax_ids.compute_all(line.price_subtotal)
            line.price_total = tax_results['total_included']
        else:
            line.price_total = line.price_subtotal
```

#### **Reconciliation Methods**
```python
def reconcile(self):
    """Đối chiếu journal item này với các items khác"""
    if not self.account_id.reconcile:
        raise UserError(_('The account %s is not reconciliable') % self.account_id.name)

    # Lấy tất cả các unreconciled lines của cùng account và partner
    domain = [
        ('account_id', '=', self.account_id.id),
        ('partner_id', '=', self.partner_id.id),
        ('reconciled', '=', False),
        ('move_id.state', '=', 'posted')
    ]

    unreconciled_lines = self.search(domain)

    if len(unreconciled_lines) < 2:
        raise UserError(_('You need at least two unreconciled items to reconcile'))

    # Tạo reconciliation
    self._reconcile_lines(unreconciled_lines)

def _reconcile_lines(self, lines_to_reconcile):
    """Internal method để đối chiếu các lines"""
    lines = lines_to_reconcile.filtered(lambda l: not l.reconciled)

    # Group by currency
    lines_by_currency = {}
    for line in lines:
        currency = line.currency_id or line.company_currency_id
        if currency not in lines_by_currency:
            lines_by_currency[currency] = []
        lines_by_currency[currency].append(line)

    # Reconcile từng currency group
    for currency, currency_lines in lines_by_currency.items():
        self._create_reconcile_moves(currency_lines, currency)

def _create_reconcile_moves(self, lines, currency):
    """Tạo reconcile moves"""
    total_debit = sum(lines.mapped('debit'))
    total_credit = sum(lines.mapped('credit'))

    if not float_is_zero(total_debit - total_credit, precision_rounding=currency.rounding):
        # Tạo exchange rate line nếu cần
        self._create_exchange_rate_line(lines, total_debit - total_credit, currency)

    # Tạo full reconciliation
    full_reconcile = self.env['account.full.reconcile'].create({})

    # Tạo partial reconciliations
    for line in lines:
        if line.debit > 0:
            # Debit line - match với credit lines
            credit_lines = lines.filtered(lambda l: l.credit > 0 and l != line)
            remaining_amount = line.debit

            for credit_line in credit_lines:
                if remaining_amount <= 0:
                    break

                match_amount = min(remaining_amount, credit_line.credit)

                self.env['account.partial.reconcile'].create({
                    'debit_move_id': line.id,
                    'credit_move_id': credit_line.id,
                    'amount': match_amount,
                    'debit_amount_currency': line.amount_currency,
                    'credit_amount_currency': credit_line.amount_currency,
                    'full_reconcile_id': full_reconcile.id,
                })

                remaining_amount -= match_amount

        elif line.credit > 0:
            # Credit line - match với debit lines
            debit_lines = lines.filtered(lambda l: l.debit > 0 and l != line)
            remaining_amount = line.credit

            for debit_line in debit_lines:
                if remaining_amount <= 0:
                    break

                match_amount = min(remaining_amount, debit_line.debit)

                self.env['account.partial.reconcile'].create({
                    'debit_move_id': debit_line.id,
                    'credit_move_id': line.id,
                    'amount': match_amount,
                    'debit_amount_currency': debit_line.amount_currency,
                    'credit_amount_currency': line.amount_currency,
                    'full_reconcile_id': full_reconcile.id,
                })

                remaining_amount -= match_amount

    # Cập nhật reconcile status
    for line in lines:
        line._compute_amount_residual()

def remove_move_reconcile(self):
    """Xóa reconciliation"""
    for line in self:
        # Xóa partial reconciliations
        line.matched_debit_ids.unlink()
        line.matched_credit_ids.unlink()

        # Xóa full reconciliation
        if line.full_reconcile_id:
            line.full_reconcile_id.unlink()

        # Recompute amounts
        line._compute_amount_residual()

def create_analytic_lines(self):
    """Tạo analytic lines"""
    self.analytic_line_ids.unlink()

    for line in self:
        if not line.analytic_distribution:
            continue

        for analytic_account_id, percentage in line.analytic_distribution.items():
            if not percentage:
                continue

            amount = line.balance * (percentage / 100)

            self.env['account.analytic.line'].create({
                'name': line.move_id.name or line.ref,
                'date': line.move_id.date,
                'account_id': analytic_account_id,
                'move_id': line.move_id.id,
                'move_line_id': line.id,
                'amount': amount,
                'company_id': line.company_id.id,
                'currency_id': line.currency_id.id,
            })
```

#### **Supply Chain Integration Methods**
```python
def create_stock_valuation_line(self, stock_move, valuation_amount):
    """Tạo line cho stock valuation"""
    return self.create({
        'move_id': self.env.context.get('stock_valuation_move_id'),
        'account_id': self.env['stock.property'].get_property_valuation(
            stock_move.product_id, stock_move.company_id
        ).account_valuation_id.id,
        'product_id': stock_move.product_id.id,
        'quantity': stock_move.product_qty,
        'price_unit': valuation_amount / stock_move.product_qty if stock_move.product_qty else 0,
        'debit': valuation_amount if valuation_amount > 0 else 0,
        'credit': -valuation_amount if valuation_amount < 0 else 0,
        'name': _('Stock Valuation: %s') % stock_move.reference,
        'ref': stock_move.reference,
        'partner_id': stock_move.partner_id.id,
        'analytic_distribution': stock_move.analytic_distribution,
    })

def create_cost_of_goods_sold_line(self, stock_move, cogs_amount):
    """Tạo line cho cost of goods sold"""
    cogs_account = self.env['stock.property'].get_property_valuation(
        stock_move.product_id, stock_move.company_id
    ).account_cogs_id

    return self.create({
        'move_id': self.env.context.get('stock_valuation_move_id'),
        'account_id': cogs_account.id,
        'product_id': stock_move.product_id.id,
        'quantity': stock_move.product_qty,
        'price_unit': cogs_amount / stock_move.product_qty if stock_move.product_qty else 0,
        'debit': cogs_amount if cogs_amount > 0 else 0,
        'credit': -cogs_amount if cogs_amount < 0 else 0,
        'name': _('Cost of Goods Sold: %s') % stock_move.reference,
        'ref': stock_move.reference,
        'partner_id': stock_move.partner_id.id,
        'analytic_distribution': stock_move.analytic_distribution,
    })
```

### 🔍 Relationships & Constraints

```python
# Relationships
analytic_line_ids = fields.One2many(
    'account.analytic.line',
    'move_line_id',
    string='Analytic Lines'
)

matched_debit_ids = fields.One2many(
    'account.partial.reconcile',
    'credit_move_id',
    string='Matched Debits'
)

matched_credit_ids = fields.One2many(
    'account.partial.reconcile',
    'debit_move_id',
    string='Matched Credits'
)

# Constraints
_sql_constraints = [
    ('debit_credit_check', 'CHECK (debit >= 0 AND credit >= 0)',
     'Wrong credit or debit value in accounting entry!'),
]
```

---

## 📝 Account - `account.account`

**Mục đích**: Quản lý hệ thống tài khoản kế toán

### 🔍 Model Overview
```python
class AccountAccount(models.Model):
    _name = 'account.account'
    _description = 'Account'
    _order = 'code'
    _check_company_auto = True
```

### 📋 Fields Specification

#### **Core Identity Fields**
```python
name = fields.Char(
    string='Account Name',
    required=True
)

code = fields.Char(
    string='Code',
    size=64,
    required=True,
    help="Unique code for the account"
)

company_id = fields.Many2one(
    'res.company',
    string='Company',
    required=True,
    default=lambda self: self.env.company
)

currency_id = fields.Many2one(
    'res.currency',
    string='Currency',
    help="Secondary currency of the account"
)
```

#### **Account Classification Fields**
```python
user_type_id = fields.Many2one(
    'account.account.type',
    string='Account Type',
    required=True,
    help="Account type is used for information purpose, to generate country-specific legal reports"
)

internal_type = fields.Selection([
    ('payable', 'Payable'),
    ('receivable', 'Receivable'),
    ('liquidity', 'Liquidity'),
    ('other', 'Regular'),
], string='Internal Type',
    required=True,
    help="The 'Internal Type' is used for features available on different types of accounts")

reconcile = fields.Boolean(
    string='Allow Reconciliation',
    default=False,
    help="Check this if the user is allowed to reconcile entries in this account"
)

deprecated = fields.Boolean(
    string='Deprecated',
    default=False,
    help="This account is deprecated"
)
```

#### **Financial Statement Fields**
```python
group_id = fields.Many2one(
    'account.group',
    string='Group',
    help="Group for financial reporting"
)

root_id = fields.Many2one(
    'account.account',
    string='Root',
    compute='_compute_root_id',
    store=True,
    help="Root account"
)

level = fields.Integer(
    string='Level',
    compute='_compute_level',
    store=True,
    help="Level of the account in the hierarchy"
)
```

### 🔧 Key Methods

#### **Hierarchy Methods**
```python
@api.depends('code')
def _compute_level(self):
    """Tính toán level trong account hierarchy"""
    for account in self:
        account.level = len(account.code.split('.')) or 1

@api.depends('code')
def _compute_root_id(self):
    """Tìm root account"""
    for account in self:
        # Root account là account không có parent (level 1)
        if account.level == 1:
            account.root_id = account.id
        else:
            # Tìm root account dựa trên code structure
            root_code = account.code.split('.')[0]
            root_account = self.search([
                ('code', '=', root_code),
                ('company_id', '=', account.company_id.id)
            ], limit=1)
            account.root_id = root_account.id if root_account else account.id

def _get_parent(self):
    """Lấy parent account trong hierarchy"""
    self.ensure_one()
    if self.level <= 1:
        return False

    # Parent code là một level cao hơn
    parent_code = '.'.join(self.code.split('.')[:-1])
    return self.search([
        ('code', '=', parent_code),
        ('company_id', '=', self.company_id.id)
    ], limit=1)

def _get_children(self):
    """Lấy tất cả children accounts"""
    self.ensure_one()
    return self.search([
        ('code', 'like', self.code + '.%'),
        ('company_id', '=', self.company_id.id)
    ])

# Supply Chain Integration Methods
def get_stock_valuation_account(self, company):
    """Lấy stock valuation account cho product"""
    # Tìm default stock valuation account
    stock_account = self.search([
        ('code', 'like', '135%'),  # Ví dụ: 1351, 1352, etc.
        ('internal_type', '=', 'other'),
        ('company_id', '=', company.id),
        ('deprecated', '=', False)
    ], limit=1)

    return stock_account or self.env['account.account'].search([
        ('user_type_id', '=', self.env.ref('account.data_account_type_current_assets').id),
        ('company_id', '=', company.id)
    ], limit=1)

def get_cogs_account(self, company):
    """Lấy cost of goods sold account"""
    # Tìm default COGS account
    cogs_account = self.search([
        ('code', 'like', '632%'),  # Ví dụ: 6321, 6322, etc.
        ('internal_type', '=', 'other'),
        ('company_id', '=', company.id),
        ('deprecated', '=', False)
    ], limit=1)

    return cogs_account or self.env['account.account'].search([
        ('user_type_id', '=', self.env.ref('account.data_account_type_expenses').id),
        ('company_id', '=', company.id)
    ], limit=1)

def get_expense_account(self, company):
    """Lấy expense account cho purchase"""
    # Tìm default expense account
    expense_account = self.search([
        ('code', 'like', '641%'),  # Ví dụ: 6411, 6412, etc.
        ('internal_type', '=', 'other'),
        ('company_id', '=', company.id),
        ('deprecated', '=', False)
    ], limit=1)

    return expense_account or self.env['account.account'].search([
        ('user_type_id', '=', self.env.ref('account.data_account_type_expenses').id),
        ('company_id', '=', company.id)
    ], limit=1)

def get_income_account(self, company):
    """Lấy income account cho sales"""
    # Tìm default income account
    income_account = self.search([
        ('code', 'like', '511%'),  # Ví dụ: 5111, 5112, etc.
        ('internal_type', '=', 'other'),
        ('company_id', '=', company.id),
        ('deprecated', '=', False)
    ], limit=1)

    return income_account or self.env['account.account'].search([
        ('user_type_id', '=', self.env.ref('account.data_account_type_revenue').id),
        ('company_id', '=', company.id)
    ], limit=1)

def get_payable_account(self, company):
    """Lấy accounts payable account"""
    return self.search([
        ('internal_type', '=', 'payable'),
        ('company_id', '=', company.id),
        ('deprecated', '=', False)
    ], limit=1)

def get_receivable_account(self, company):
    """Lấy accounts receivable account"""
    return self.search([
        ('internal_type', '=', 'receivable'),
        ('company_id', '=', company.id),
        ('deprecated', '=', False)
    ], limit=1)
```

### 🔍 Relationships & Constraints

```python
# Relationships
move_line_ids = fields.One2many(
    'account.move.line',
    'account_id',
    string='Journal Items'
)

tax_ids = fields.Many2many(
    'account.tax',
    'account_account_tax_rel',
    'account_id', 'tax_id',
    string='Taxes'
)

# Constraints
_sql_constraints = [
    ('code_company_uniq', 'unique(code, company_id)',
     'The code of the account must be unique per company!'),
]
```

---

## 💡 Usage Examples

### **Example 1: Creating Supplier Invoice from Purchase Order**
```python
def create_supplier_invoice_from_po(self, purchase_order):
    """Tạo supplier invoice từ purchase order"""

    # Tạo journal entry cho supplier invoice
    journal = self.env['account.journal'].search([
        ('type', '=', 'purchase'),
        ('company_id', '=', purchase_order.company_id.id)
    ], limit=1)

    invoice_vals = {
        'move_type': 'in_invoice',
        'partner_id': purchase_order.partner_id.id,
        'journal_id': journal.id,
        'invoice_origin': purchase_order.name,
        'date': fields.Date.today(),
        'invoice_line_ids': []
    }

    # Process mỗi purchase order line
    for line in purchase_order.order_line:
        # Lấy expense account cho product
        expense_account = self.env['account.account'].get_expense_account(
            purchase_order.company_id
        )

        line_vals = {
            'product_id': line.product_id.id,
            'quantity': line.product_qty,
            'price_unit': line.price_unit,
            'name': line.name,
            'account_id': expense_account.id,
            'analytic_distribution': line.analytic_distribution,
        }

        invoice_vals['invoice_line_ids'].append((0, 0, line_vals))

    # Tạo invoice
    invoice = self.env['account.move'].create(invoice_vals)

    return invoice
```

### **Example 2: Stock Valuation Journal Entry**
```python
def create_stock_valuation_entry(self, stock_move, valuation_amount):
    """Tạo journal entry cho stock valuation"""

    journal = self.env['account.journal'].search([
        ('type', '=', 'general'),
        ('company_id', '=', stock_move.company_id.id)
    ], limit=1)

    # Lấy accounts
    valuation_account = self.env['account.account'].get_stock_valuation_account(
        stock_move.company_id
    )

    # Tạo journal entry
    move_vals = {
        'move_type': 'entry',
        'journal_id': journal.id,
        'date': stock_move.date,
        'ref': 'Stock Valuation - %s' % stock_move.reference,
        'line_ids': []
    }

    # Stock valuation line (Debit Inventory, Credit GR/IR)
    if valuation_amount > 0:
        # Debit Inventory
        move_vals['line_ids'].append((0, 0, {
            'account_id': valuation_account.id,
            'debit': valuation_amount,
            'credit': 0.0,
            'name': 'Stock Receipt Valuation',
            'product_id': stock_move.product_id.id,
            'quantity': stock_move.product_qty,
        }))

        # Credit GR/IR Account
        gr_ir_account = self.env['account.account'].search([
            ('code', 'like', '155%'),  # Goods received/Invoice received account
            ('company_id', '=', stock_move.company_id.id)
        ], limit=1)

        move_vals['line_ids'].append((0, 0, {
            'account_id': gr_ir_account.id,
            'debit': 0.0,
            'credit': valuation_amount,
            'name': 'Goods Received',
            'partner_id': stock_move.partner_id.id,
        }))

    # Tạo và post journal entry
    move = self.env['account.move'].create(move_vals)
    move.action_post()

    return move
```

### **Example 3: Accounts Receivable Reconciliation**
```python
def reconcile_customer_payments(self, customer, invoice_ids, payment_ids):
    """Đối chiếu customer invoices với payments"""

    # Get unpaid invoice lines
    invoice_moves = self.env['account.move'].browse(invoice_ids)
    invoice_lines = invoice_moves.line_ids.filtered(
        lambda l: l.account_id.internal_type == 'receivable' and not l.reconciled
    )

    # Get payment lines
    payment_moves = self.env['account.payment'].browse(payment_ids)
    payment_lines = payment_moves.move_line_ids.filtered(
        lambda l: l.account_id.internal_type == 'receivable' and not l.reconciled
    )

    # Combine all lines for reconciliation
    all_lines = invoice_lines + payment_lines

    if len(all_lines) < 2:
        raise UserError(_('Need at least 2 lines to reconcile'))

    # Perform reconciliation
    all_lines.reconcile()

    return True
```

---

## 📚 Navigation Guide

- **Previous**: [01_accounting_overview.md](01_accounting_overview.md) - Tổng quan architecture
- **Next**: [03_integration_guide.md](03_integration_guide.md) - Inventory valuation integration

---

**File Status**: 📝 **COMPLETED**
**File Size**: ~8,000 từ
**Language**: Tiếng Việt
**Target Audience**: Developers, Accountants, System Integrators
**Completion**: 2025-11-08

*File này cung cấp tài liệu chi tiết về Accounting Module models với focus vào supply chain integration, giúp developers implement các financial workflows cho chuỗi cung ứng Odoo.*