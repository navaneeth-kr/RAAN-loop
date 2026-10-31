from extensions import db
from models.invoice import Invoice, InvoiceHistory
from models.subscription import Subscription
from models.tax_config import TaxConfig
from datetime import date, datetime, timedelta
from flask import current_app
import logging

logger = logging.getLogger(__name__)


def get_active_tax():
    """Return the first active tax config, or None."""
    return TaxConfig.query.filter_by(is_active=True).first()


def generate_invoice_number():
    """Generate a unique, sequential invoice number."""
    prefix = datetime.utcnow().strftime('INV-%Y%m-')
    last = (Invoice.query
            .filter(Invoice.invoice_number.like(f'{prefix}%'))
            .order_by(Invoice.id.desc())
            .first())
    if last:
        try:
            seq = int(last.invoice_number.split('-')[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f'{prefix}{seq:05d}'


def create_invoice(customer_id, product_name, product_description, quantity,
                   unit_price, discount_percent=0, subscription_id=None,
                   billing_period_start=None, billing_period_end=None,
                   notes=None, invoice_date=None, due_days=None):
    """
    Create a new invoice (status=draft) inside a DB transaction.
    Returns the created Invoice object.
    """
    if due_days is None:
        due_days = current_app.config.get('INVOICE_DUE_DAYS', 30)

    invoice_date = invoice_date or date.today()
    due_date = invoice_date + timedelta(days=due_days)

    # Fetch active tax
    tax_cfg = get_active_tax()

    with db.session.begin():
        inv = Invoice(
            invoice_number=generate_invoice_number(),
            customer_id=customer_id,
            subscription_id=subscription_id,
            billing_period_start=billing_period_start,
            billing_period_end=billing_period_end,
            product_name=product_name,
            product_description=product_description,
            quantity=quantity,
            unit_price=unit_price,
            discount_percent=discount_percent,
            tax_name=tax_cfg.name if tax_cfg else None,
            tax_rate=tax_cfg.rate if tax_cfg else 0,
            invoice_date=invoice_date,
            due_date=due_date,
            status=Invoice.STATUS_DRAFT,
            notes=notes,
        )
        inv.compute_totals()
        db.session.add(inv)
        db.session.flush()  # get inv.id

        history = InvoiceHistory(
            invoice_id=inv.id,
            action='created',
            description=f'Invoice {inv.invoice_number} created as Draft.',
        )
        db.session.add(history)

    db.session.refresh(inv)
    return inv


def confirm_invoice(invoice_id):
    """Transition invoice from Draft → Confirmed."""
    with db.session.begin():
        inv = Invoice.query.with_for_update().get(invoice_id)
        if not inv:
            raise ValueError('Invoice not found.')
        if inv.status != Invoice.STATUS_DRAFT:
            raise ValueError(f'Cannot confirm invoice in status "{inv.status}".')

        inv.status = Invoice.STATUS_CONFIRMED
        inv.confirmed_at = datetime.utcnow()
        db.session.add(InvoiceHistory(
            invoice_id=inv.id,
            action='confirmed',
            description='Invoice confirmed.',
        ))
    db.session.refresh(inv)
    return inv


def mark_paid(invoice_id):
    """Transition invoice from Confirmed → Paid."""
    with db.session.begin():
        inv = Invoice.query.with_for_update().get(invoice_id)
        if not inv:
            raise ValueError('Invoice not found.')
        if inv.status != Invoice.STATUS_CONFIRMED:
            raise ValueError(f'Cannot mark invoice in status "{inv.status}" as paid.')

        inv.status = Invoice.STATUS_PAID
        inv.paid_at = datetime.utcnow()
        db.session.add(InvoiceHistory(
            invoice_id=inv.id,
            action='paid',
            description='Invoice marked as Paid.',
        ))
    db.session.refresh(inv)
    return inv


def cancel_invoice(invoice_id, reason=None):
    """Cancel an invoice (Draft or Confirmed only)."""
    with db.session.begin():
        inv = Invoice.query.with_for_update().get(invoice_id)
        if not inv:
            raise ValueError('Invoice not found.')
        if inv.status == Invoice.STATUS_PAID:
            raise ValueError('Cannot cancel a paid invoice.')
        if inv.status == Invoice.STATUS_CANCELLED:
            raise ValueError('Invoice is already cancelled.')

        inv.status = Invoice.STATUS_CANCELLED
        inv.cancelled_at = datetime.utcnow()
        db.session.add(InvoiceHistory(
            invoice_id=inv.id,
            action='cancelled',
            description=f'Invoice cancelled. Reason: {reason or "N/A"}',
        ))
    db.session.refresh(inv)
    return inv


def get_invoices(status=None, customer_id=None, subscription_id=None,
                 search=None, start_date=None, end_date=None,
                 page=1, per_page=20):
    """Fetch invoices with filters and pagination."""
    from models.customer import Customer
    query = Invoice.query.join(Customer)

    if status:
        query = query.filter(Invoice.status == status)
    if customer_id:
        query = query.filter(Invoice.customer_id == customer_id)
    if subscription_id:
        query = query.filter(Invoice.subscription_id == subscription_id)
    if search:
        like = f'%{search}%'
        query = query.filter(
            db.or_(
                Invoice.invoice_number.ilike(like),
                Customer.name.ilike(like),
                Customer.email.ilike(like),
                Invoice.product_name.ilike(like),
            )
        )
    if start_date:
        query = query.filter(Invoice.invoice_date >= start_date)
    if end_date:
        query = query.filter(Invoice.invoice_date <= end_date)

    return query.order_by(Invoice.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )


def duplicate_exists(subscription_id, billing_period_start):
    """Check if an invoice already exists for this subscription and billing period."""
    return Invoice.query.filter_by(
        subscription_id=subscription_id,
        billing_period_start=billing_period_start,
    ).filter(Invoice.status != Invoice.STATUS_CANCELLED).first() is not None

