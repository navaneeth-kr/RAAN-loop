from extensions import db
from datetime import datetime, date
from dateutil.relativedelta import relativedelta


class Subscription(db.Model):
    __tablename__ = 'subscriptions'

    STATUS_ACTIVE = 'active'
    STATUS_PAUSED = 'paused'
    STATUS_CANCELLED = 'cancelled'
    STATUS_EXPIRED = 'expired'

    id = db.Column(db.Integer, primary_key=True)
    subscription_number = db.Column(db.String(20), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    billing_cycle = db.Column(db.String(20), default='monthly')  # monthly, yearly, weekly
    status = db.Column(db.String(20), default=STATUS_ACTIVE)
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    end_date = db.Column(db.Date, nullable=True)
    next_billing_date = db.Column(db.Date, nullable=False)
    last_billed_date = db.Column(db.Date, nullable=True)
    discount_percent = db.Column(db.Numeric(5, 2), default=0.00)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    invoices = db.relationship('Invoice', backref='subscription', lazy=True)

    def __repr__(self):
        return f'<Subscription {self.subscription_number}>'

    def calculate_next_billing_date(self, from_date=None):
        """Calculate the next billing date based on billing cycle."""
        base = from_date or self.next_billing_date or self.start_date
        if self.billing_cycle == 'weekly':
            return base + relativedelta(weeks=1)
        elif self.billing_cycle == 'monthly':
            return base + relativedelta(months=1)
        elif self.billing_cycle == 'yearly':
            return base + relativedelta(years=1)
        return base + relativedelta(months=1)

