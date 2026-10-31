import logging
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.models import User
from subscriptions.models import Notification

logger = logging.getLogger(__name__)

def send_notification(user, title, message, category='system', link='', send_email=True):
    """
    Creates an in-app notification and optionally dispatches an email notification.
    Ensures email failure never breaks transactional business operations.
    """
    if not user:
        return None

    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        category=category,
        link=link
    )

    if send_email and user.email:
        try:
            subject = f"[{getattr(settings, 'COMPANY_NAME', 'Brightloop')}] {title}"
            email_body = f"""Hello {user.get_full_name() or user.username},

{message}

---
You received this notification regarding your Brightloop Software account.
Access your portal: {settings.LOGIN_URL}
"""
            send_mail(
                subject=subject,
                message=email_body,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'billing@brightloop.io'),
                recipient_list=[user.email],
                fail_silently=True
            )
        except Exception as e:
            logger.warning(f"Failed to dispatch email to {user.email}: {e}")

    return notification


def notify_customer_registered(customer):
    """Alerts customer upon successful registration."""
    if customer.user:
        send_notification(
            user=customer.user,
            title="Welcome to Brightloop Software",
            message=f"Welcome {customer.full_name}! Your customer account has been created successfully. Explore our plans and manage subscriptions from your portal.",
            category='system',
            link='/portal/'
        )


def notify_subscription_status(subscription, action_label, extra_note=""):
    """Sends lifecycle alerts for subscriptions."""
    user = getattr(subscription.customer, 'user', None)
    if not user:
        user = User.objects.filter(is_staff=True).first()

    title = f"Subscription {subscription.subscription_id}: {action_label}"
    msg = f"Your subscription for '{subscription.plan.name}' has been {action_label.lower()}."
    if extra_note:
        msg += f" Note: {extra_note}"
    msg += f" Current status: {subscription.get_status_display()}."

    send_notification(
        user=user,
        title=title,
        message=msg,
        category='subscription',
        link=f"/subscriptions/{subscription.pk}/" if user.is_staff else f"/portal/subscriptions/{subscription.pk}/"
    )


def notify_invoice_generated(invoice):
    """Notifies customer when a new invoice is issued."""
    user = getattr(invoice.customer, 'user', None)
    if not user:
        user = User.objects.filter(is_staff=True).first()

    send_notification(
        user=user,
        title=f"New Invoice Issued: {invoice.invoice_number}",
        message=f"Invoice {invoice.invoice_number} for ${invoice.total_amount} is now available. Due date: {invoice.due_date}.",
        category='billing',
        link=f"/invoices/{invoice.pk}/" if user.is_staff else f"/portal/invoices/{invoice.pk}/"
    )


def notify_payment_success(payment):
    """Notifies customer upon verified payment completion."""
    user = getattr(payment.customer, 'user', None)
    if not user:
        user = User.objects.filter(is_staff=True).first()

    inv_ref = f"for invoice {payment.invoice.invoice_number}" if payment.invoice else ""
    send_notification(
        user=user,
        title=f"Payment Received: {payment.payment_id}",
        message=f"Your payment of ${payment.amount} {inv_ref} via {payment.get_payment_method_display()} has been confirmed.",
        category='payment',
        link=f"/payments/{payment.pk}/" if user.is_staff else f"/portal/invoices/{payment.invoice.pk if payment.invoice else ''}"
    )
