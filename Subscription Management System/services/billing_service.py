"""
Automatic billing service.
- Scans active subscriptions.
- Generates invoices when next_billing_date <= today.
- Prevents duplicate invoices.
- Does NOT skip billing periods (catches up missed cycles).
"""
from extensions import db
from models.subscription import Subscription
from models.invoice import Invoice
from services.invoice_service import create_invoice, duplicate_exists
from datetime import date
import logging

logger = logging.getLogger(__name__)


def run_automatic_billing(app):
    """Run inside an app context. Generates all overdue invoices."""
    with app.app_context():
        today = date.today()
        active_subs = Subscription.query.filter(
            Subscription.status == Subscription.STATUS_ACTIVE,
            Subscription.next_billing_date <= today,
        ).all()

        generated = []
        skipped = []

        for sub in active_subs:
            try:
                invoices_for_sub = _process_subscription(sub, today)
                generated.extend(invoices_for_sub)
            except Exception as e:
                logger.error(f'Billing error for subscription {sub.subscription_number}: {e}')
                skipped.append({'subscription': sub.subscription_number, 'error': str(e)})

        logger.info(f'Auto-billing complete: {len(generated)} invoices generated, {len(skipped)} skipped.')
        return {'generated': generated, 'skipped': skipped}


def _process_subscription(sub, today):
    """
    Process a single subscription.
    Loop through missed billing periods to avoid skipping any.
    """
    generated = []
    billing_date = sub.next_billing_date

    while billing_date <= today:
        period_start = billing_date
        period_end = sub.calculate_next_billing_date(from_date=billing_date)

        # Duplicate guard
        if duplicate_exists(sub.id, period_start):
            logger.info(f'Duplicate skipped: sub={sub.id} period={period_start}')
            billing_date = sub.calculate_next_billing_date(from_date=billing_date)
            continue

        # Create invoice
        inv = create_invoice(
            customer_id=sub.customer_id,
            product_name=sub.product.name,
            product_description=sub.product.description,
            quantity=sub.quantity,
            unit_price=float(sub.unit_price),
            discount_percent=float(sub.discount_percent or 0),
            subscription_id=sub.id,
            billing_period_start=period_start,
            billing_period_end=period_end,
            invoice_date=billing_date,
        )
        generated.append(inv.invoice_number)
        logger.info(f'Invoice {inv.invoice_number} generated for sub {sub.subscription_number}.')

        # Advance billing date
        billing_date = period_end

    # Update subscription's next billing date and last billed date
    with db.session.begin():
        sub_fresh = Subscription.query.with_for_update().get(sub.id)
        sub_fresh.next_billing_date = billing_date
        sub_fresh.last_billed_date = today

    return generated


def schedule_billing(app, scheduler):
    """Register the billing job with APScheduler (daily at midnight)."""
    scheduler.add_job(
        func=run_automatic_billing,
        trigger='cron',
        hour=0,
        minute=0,
        id='auto_billing',
        replace_existing=True,
        args=[app],
    )
    logger.info('Auto-billing scheduler registered.')

