import random
from datetime import timedelta, date
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import SystemSetting, ActivityLog
from core.notifications import notify_invoice_generated, send_notification
from subscriptions.models import Subscription, Invoice, TaxRate

class Command(BaseCommand):
    help = "Automated Recurring Billing Engine: Identifies due subscriptions, generates recurring invoices, prevents duplicates, and advances billing cycles."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate billing cycle run without creating invoices or modifying database records.'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        today = timezone.now().date()
        self.stdout.write(self.style.NOTICE(f"--- Running Recurring Billing Automation [{today}] (Dry Run: {dry_run}) ---"))

        system_settings = SystemSetting.get_settings()
        prefix = system_settings.invoice_prefix or "BL-INV-"

        # Subscriptions eligible for recurring billing
        due_subscriptions = Subscription.objects.filter(
            status__in=['active', 'confirmed'],
            next_billing_date__lte=today
        ).select_related('customer', 'plan', 'variant')

        count_generated = 0
        count_skipped = 0

        for sub in due_subscriptions:
            # 1. Duplicate Prevention: Check if invoice was already generated for today or current period
            if Invoice.objects.filter(subscription=sub, issued_date=today).exists():
                self.stdout.write(self.style.WARNING(f"  [SKIPPED] Subscription {sub.subscription_id}: Invoice already issued today."))
                count_skipped += 1
                continue

            # 2. Financial calculation
            subtotal = sub.current_amount or Decimal('0.00')

            # Default tax rate
            default_tax = TaxRate.objects.filter(is_default=True, is_active=True).first()
            tax_amount = Decimal('0.00')
            if default_tax:
                tax_amount = round(subtotal * (default_tax.rate_percent / Decimal('100.00')), 2)

            total_amount = subtotal + tax_amount

            # Due date (Net 15 standard payment term)
            due_date = today + timedelta(days=15)

            # Generate unique invoice number
            inv_number = f"{prefix}{today.strftime('%Y%m')}-{random.randint(1000, 9999)}"
            while Invoice.objects.filter(invoice_number=inv_number).exists():
                inv_number = f"{prefix}{today.strftime('%Y%m')}-{random.randint(1000, 9999)}"

            if dry_run:
                self.stdout.write(f"  [SIMULATED] Would generate {inv_number} for {sub.customer.full_name} (${total_amount})")
                count_generated += 1
                continue

            # 3. Create invoice in DB
            invoice = Invoice.objects.create(
                invoice_number=inv_number,
                customer=sub.customer,
                subscription=sub,
                amount=subtotal,
                tax_rate=default_tax,
                tax_amount=tax_amount,
                discount_amount=Decimal('0.00'),
                total_amount=total_amount,
                status='pending',
                issued_date=today,
                due_date=due_date,
                notes=f"Automated recurring billing for {sub.plan.name} ({sub.billing_cycle}). Payment terms: {sub.payment_terms}."
            )

            # 4. Advance subscription next_billing_date
            freq = sub.plan.billing_frequency.lower() if sub.plan else 'monthly'
            if freq == 'daily':
                next_date = today + timedelta(days=1)
            elif freq == 'weekly':
                next_date = today + timedelta(days=7)
            elif freq == 'yearly':
                next_date = today + timedelta(days=365)
            else:  # default monthly
                next_date = today + timedelta(days=30)

            # Check if subscription reaches non-renewing expiration
            if sub.expiry_date and next_date > sub.expiry_date and not sub.auto_renew:
                sub.status = 'closed'
                sub.closed_at = timezone.now()
                self.stdout.write(self.style.NOTICE(f"  Subscription {sub.subscription_id} reached end of term and was closed."))
            else:
                sub.next_billing_date = next_date

            sub.save(update_fields=['next_billing_date', 'status', 'closed_at'])

            # 5. Log activity & trigger notifications
            ActivityLog.objects.create(
                action=f"Recurring invoice {invoice.invoice_number} generated for {sub.customer.full_name}",
                category="system",
                details=f"Subscription: {sub.subscription_id}, Amount: ${total_amount}"
            )
            notify_invoice_generated(invoice)

            self.stdout.write(self.style.SUCCESS(f"  [GENERATED] {inv_number} -> {sub.customer.full_name} (${total_amount}) - Next billing: {sub.next_billing_date}"))
            count_generated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Recurring Billing Finished: {count_generated} invoices generated, {count_skipped} skipped."
        ))
