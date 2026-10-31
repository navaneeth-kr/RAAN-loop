from extensions import db
from datetime import datetime


class TaxConfig(db.Model):
    __tablename__ = 'tax_configs'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)       # e.g., "GST", "VAT"
    rate = db.Column(db.Numeric(5, 2), nullable=False)     # e.g., 18.00 for 18%
    description = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    applies_to = db.Column(db.String(50), default='all')   # all / specific
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<TaxConfig {self.name} {self.rate}%>'

