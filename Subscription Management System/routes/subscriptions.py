from flask import Blueprint, render_template, request, redirect, url_for, flash
from extensions import db
from models import Subscription, Customer, Product
from datetime import date

subscriptions_bp = Blueprint('subscriptions', __name__, url_prefix='/subscriptions')


@subscriptions_bp.route('/')
def list_subscriptions():
    status = request.args.get('status', '')
    query = Subscription.query
    if status:
        query = query.filter_by(status=status)
    subscriptions = query.order_by(Subscription.created_at.desc()).all()
    return render_template('subscriptions/list.html',
                           subscriptions=subscriptions, status_filter=status)


@subscriptions_bp.route('/create', methods=['GET', 'POST'])
def create():
    customers = Customer.query.order_by(Customer.name).all()
    products = Product.query.filter_by(is_active=True).order_by(Product.name).all()
    if request.method == 'POST':
        try:
            start_date = date.fromisoformat(request.form['start_date'])
            sub = Subscription(
                subscription_number=_next_sub_number(),
                customer_id=int(request.form['customer_id']),
                product_id=int(request.form['product_id']),
                quantity=int(request.form.get('quantity', 1)),
                unit_price=float(request.form['unit_price']),
                billing_cycle=request.form.get('billing_cycle', 'monthly'),
                start_date=start_date,
                next_billing_date=start_date,
                discount_percent=float(request.form.get('discount_percent', 0)),
                notes=request.form.get('notes', '').strip(),
            )
            db.session.add(sub)
            db.session.commit()
            flash(f'Subscription {sub.subscription_number} created!', 'success')
            return redirect(url_for('subscriptions.list_subscriptions'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {e}', 'danger')
    return render_template('subscriptions/create.html',
                           customers=customers, products=products,
                           today=date.today().isoformat())


@subscriptions_bp.route('/<int:sub_id>')
def detail(sub_id):
    sub = Subscription.query.get_or_404(sub_id)
    return render_template('subscriptions/detail.html', sub=sub)


def _next_sub_number():
    from models import Subscription as S
    last = S.query.order_by(S.id.desc()).first()
    num = (last.id + 1) if last else 1
    return f'SUB-{num:06d}'

