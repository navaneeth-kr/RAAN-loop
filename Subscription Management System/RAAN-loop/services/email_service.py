from flask import current_app, render_template
from flask_mail import Message
from extensions import mail, db
from models.invoice import Invoice, InvoiceHistory
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def send_invoice_email(invoice_id):
    """
    Send an invoice email to the customer.
    Attaches a plain-text summary; PDF can be attached optionally.
    """
    inv = Invoice.query.get(invoice_id)
    if not inv:
        raise ValueError('Invoice not found.')
    if inv.status == Invoice.STATUS_DRAFT:
        raise ValueError('Cannot email a Draft invoice. Please confirm it first.')

    customer = inv.customer
    company = current_app.config.get('COMPANY_NAME', 'Our Company')

    subject = f'Invoice {inv.invoice_number} from {company}'
    recipients = [customer.email]

    html_body = render_template(
        'invoices/email_invoice.html',
        invoice=inv,
        customer=customer,
        company_name=company,
        company_address=current_app.config.get('COMPANY_ADDRESS'),
        company_phone=current_app.config.get('COMPANY_PHONE'),
        company_email=current_app.config.get('COMPANY_EMAIL'),
    )

    msg = Message(subject=subject, recipients=recipients, html=html_body)

    try:
        mail.send(msg)
        with db.session.begin():
            inv_fresh = Invoice.query.with_for_update().get(invoice_id)
            inv_fresh.email_sent_at = datetime.utcnow()
            db.session.add(InvoiceHistory(
                invoice_id=inv.id,
                action='emailed',
                description=f'Invoice emailed to {customer.email}.',
            ))
        logger.info(f'Invoice {inv.invoice_number} emailed to {customer.email}.')
        return True
    except Exception as e:
        logger.error(f'Failed to send invoice email: {e}')
        raise

