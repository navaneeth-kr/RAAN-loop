from extensions import db
from datetime import datetime, date
import uuid


class Invoice(db.Model):
    __tablename__ = 'invoices'

    STATUS_DRAFT = 'draft'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_PAID = 'paid'
    STATUS_CANCELLED = 'cancelled'

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(30), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'), nullable=True)

    # Billing period (prevents duplicates per subscription/period)
    billing_period_start = db.Column(db.Date, nullable=True)
    billing_period_end = db.Column(db.Date, nullable=True)

    # Product snapshot (at time of invoice)
    product_name = db.Column(db.String(150), nullable=False)
    product_description = db.Column(db.Text)
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)

    # Financial fields
    subtotal = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    discount_percent = db.Column(db.Numeric(5, 2), default=0.00)
    discount_amount = db.Column(db.Numeric(10, 2), default=0.00)
    tax_name = db.Column(db.String(50))
    tax_rate = db.Column(db.Numeric(5, 2), default=0.00)
    tax_amount = db.Column(db.Numeric(10, 2), default=0.00)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)

    # Dates
    invoice_date = db.Column(db.Date, nullable=False, default=date.today)
    due_date = db.Column(db.Date, nullable=False)

    # Status
    status = db.Column(db.String(20), default=STATUS_DRAFT)
    notes = db.Column(db.Text)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    paid_at = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    email_sent_at = db.Column(db.DateTime, nullable=True)

    # History log
    history = db.relationship('InvoiceHistory', backref='invoice', lazy=True,
                              order_by='InvoiceHistory.created_at')

    def __repr__(self):
        return f'<Invoice {self.invoice_number} [{self.status}]>'

    @staticmethod
    def generate_invoice_number():
        """Generate a unique invoice number: INV-YYYYMM-XXXXX"""
        prefix = datetime.utcnow().strftime('INV-%Y%m-')
        unique_part = str(uuid.uuid4().int)[:5].upper()
        return prefix + unique_part

    def compute_totals(self):
        """Recalculate subtotal, discount, tax, and total."""
        subtotal = float(self.unit_price) * int(self.quantity)
        discount_amount = subtotal * float(self.discount_percent or 0) / 100
        after_discount = subtotal - discount_amount
        tax_amount = after_discount * float(self.tax_rate or 0) / 100
        total = after_discount + tax_amount

        self.subtotal = round(subtotal, 2)
        self.discount_amount = round(discount_amount, 2)
        self.tax_amount = round(tax_amount, 2)
        self.total_amount = round(total, 2)

    def is_overdue(self):
        return self.status in (self.STATUS_DRAFT, self.STATUS_CONFIRMED) and self.due_date < date.today()


class InvoiceHistory(db.Model):
    __tablename__ = 'invoice_history'

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)      # created, confirmed, paid, cancelled, emailed
    description = db.Column(db.Text)
    performed_by = db.Column(db.String(100), default='System')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

