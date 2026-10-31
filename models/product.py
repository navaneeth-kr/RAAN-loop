from extensions import db
from datetime import datetime


class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    billing_cycle = db.Column(db.String(20), default='monthly')  # monthly, yearly, one-time
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    subscriptions = db.relationship('Subscription', backref='product', lazy=True)

    def __repr__(self):
        return f'<Product {self.name}>'

