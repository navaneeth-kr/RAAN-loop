from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, send_file, current_app, jsonify)
from extensions import db
from models import Invoice, Customer, Subscription, TaxConfig
from services.invoice_service import (
    create_invoice, confirm_invoice, cancel_invoice,
    mark_paid, get_invoices
)
from services.email_service import send_invoice_email
from services.pdf_service import generate_invoice_pdf
from services.billing_service import run_automatic_billing
from datetime import date, datetime

invoices_bp = Blueprint('invoices', __name__, url_prefix='/invoices')


# ── List / Search / Filter ────────────────────────────────────────────────────

@invoices_bp.route('/')
def list_invoices():
    status = request.args.get('status', '')
    search = request.args.get('search', '')
    customer_id = request.args.get('customer_id', type=int)
    subscription_id = request.args.get('subscription_id', type=int)
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    page = request.args.get('page', 1, type=int)

    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None

    pagination = get_invoices(
        status=status or None,
        customer_id=customer_id,
        subscription_id=subscription_id,
        search=search or None,
        start_date=start_date,
        end_date=end_date,
        page=page,
        per_page=20,
    )
    customers = Customer.query.order_by(Customer.name).all()

    # Summary stats
    stats = {
        'total': Invoice.query.count(),
        'draft': Invoice.query.filter_by(status=Invoice.STATUS_DRAFT).count(),
        'confirmed': Invoice.query.filter_by(status=Invoice.STATUS_CONFIRMED).count(),
        'paid': Invoice.query.filter_by(status=Invoice.STATUS_PAID).count(),
        'cancelled': Invoice.query.filter_by(status=Invoice.STATUS_CANCELLED).count(),
    }

    return render_template('invoices/list.html',
                           invoices=pagination.items,
                           pagination=pagination,
                           customers=customers,
                           stats=stats,
                           filters={
                               'status': status,
                               'search': search,
                               'customer_id': customer_id,
                               'subscription_id': subscription_id,
                               'start_date': start_date_str,
                               'end_date': end_date_str,
                           })


# ── Create ───────────────────────────────────────────────────────────────────

@invoices_bp.route('/create', methods=['GET', 'POST'])
def create():
    customers = Customer.query.order_by(Customer.name).all()
    subscriptions = Subscription.query.filter_by(status='active').all()
    tax_cfg = TaxConfig.query.filter_by(is_active=True).first()

    if request.method == 'POST':
        try:
            customer_id = int(request.form['customer_id'])
            subscription_id = request.form.get('subscription_id') or None
            if subscription_id:
                subscription_id = int(subscription_id)
            product_name = request.form['product_name'].strip()
            product_description = request.form.get('product_description', '').strip()
            quantity = int(request.form.get('quantity', 1))
            unit_price = float(request.form['unit_price'])
            discount_percent = float(request.form.get('discount_percent', 0))
            notes = request.form.get('notes', '').strip()
            invoice_date_str = request.form.get('invoice_date')
            invoice_date = (datetime.strptime(invoice_date_str, '%Y-%m-%d').date()
                            if invoice_date_str else date.today())

            inv = create_invoice(
                customer_id=customer_id,
                product_name=product_name,
                product_description=product_description,
                quantity=quantity,
                unit_price=unit_price,
                discount_percent=discount_percent,
                subscription_id=subscription_id,
                notes=notes,
                invoice_date=invoice_date,
            )
            flash(f'Invoice {inv.invoice_number} created successfully!', 'success')
            return redirect(url_for('invoices.detail', invoice_id=inv.id))
        except Exception as e:
            flash(f'Error creating invoice: {e}', 'danger')

    return render_template('invoices/create.html',
                           customers=customers,
                           subscriptions=subscriptions,
                           tax_cfg=tax_cfg,
                           today=date.today().isoformat())


# ── Detail ───────────────────────────────────────────────────────────────────

@invoices_bp.route('/<int:invoice_id>')
def detail(invoice_id):
    inv = Invoice.query.get_or_404(invoice_id)
    return render_template('invoices/detail.html', invoice=inv)


# ── Confirm ──────────────────────────────────────────────────────────────────

@invoices_bp.route('/<int:invoice_id>/confirm', methods=['POST'])
def confirm(invoice_id):
    try:
        inv = confirm_invoice(invoice_id)
        flash(f'Invoice {inv.invoice_number} confirmed!', 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    return redirect(url_for('invoices.detail', invoice_id=invoice_id))


# ── Mark Paid ────────────────────────────────────────────────────────────────

@invoices_bp.route('/<int:invoice_id>/mark-paid', methods=['POST'])
def mark_paid_view(invoice_id):
    try:
        inv = mark_paid(invoice_id)
        flash(f'Invoice {inv.invoice_number} marked as Paid!', 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    return redirect(url_for('invoices.detail', invoice_id=invoice_id))


# ── Cancel ───────────────────────────────────────────────────────────────────

@invoices_bp.route('/<int:invoice_id>/cancel', methods=['POST'])
def cancel(invoice_id):
    reason = request.form.get('reason', '')
    try:
        inv = cancel_invoice(invoice_id, reason=reason)
        flash(f'Invoice {inv.invoice_number} cancelled.', 'warning')
    except ValueError as e:
        flash(str(e), 'danger')
    return redirect(url_for('invoices.detail', invoice_id=invoice_id))


# ── Send Email ───────────────────────────────────────────────────────────────

@invoices_bp.route('/<int:invoice_id>/send-email', methods=['POST'])
def send_email(invoice_id):
    try:
        send_invoice_email(invoice_id)
        flash('Invoice emailed successfully!', 'success')
    except Exception as e:
        flash(f'Email error: {e}', 'danger')
    return redirect(url_for('invoices.detail', invoice_id=invoice_id))


# ── Print (HTML) ─────────────────────────────────────────────────────────────

@invoices_bp.route('/<int:invoice_id>/print')
def print_invoice(invoice_id):
    inv = Invoice.query.get_or_404(invoice_id)
    return render_template('invoices/print.html',
                           invoice=inv,
                           company_name=current_app.config.get('COMPANY_NAME'),
                           company_address=current_app.config.get('COMPANY_ADDRESS'),
                           company_phone=current_app.config.get('COMPANY_PHONE'),
                           company_email=current_app.config.get('COMPANY_EMAIL'))


# ── Download PDF ─────────────────────────────────────────────────────────────

@invoices_bp.route('/<int:invoice_id>/pdf')
def download_pdf(invoice_id):
    inv = Invoice.query.get_or_404(invoice_id)
    try:
        pdf_buffer = generate_invoice_pdf(inv)
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{inv.invoice_number}.pdf',
        )
    except Exception as e:
        flash(f'PDF generation error: {e}', 'danger')
        return redirect(url_for('invoices.detail', invoice_id=invoice_id))


# ── Auto Billing (manual trigger) ────────────────────────────────────────────

@invoices_bp.route('/run-billing', methods=['POST'])
def trigger_billing():
    try:
        result = run_automatic_billing(current_app._get_current_object())
        gen = len(result['generated'])
        flash(f'Auto-billing complete: {gen} invoice(s) generated.', 'success')
    except Exception as e:
        flash(f'Billing error: {e}', 'danger')
    return redirect(url_for('invoices.list_invoices'))


# ── AJAX: get subscription details ───────────────────────────────────────────

@invoices_bp.route('/api/subscription/<int:sub_id>')
def subscription_info(sub_id):
    sub = Subscription.query.get_or_404(sub_id)
    return jsonify({
        'customer_id': sub.customer_id,
        'customer_name': sub.customer.name,
        'product_name': sub.product.name,
        'product_description': sub.product.description or '',
        'unit_price': float(sub.unit_price),
        'quantity': sub.quantity,
        'discount_percent': float(sub.discount_percent or 0),
    })

