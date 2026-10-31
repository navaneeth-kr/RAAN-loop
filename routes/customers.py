from flask import Blueprint, render_template, request, redirect, url_for, flash
from extensions import db
from models import Customer

customers_bp = Blueprint('customers', __name__, url_prefix='/customers')


@customers_bp.route('/')
def list_customers():
    search = request.args.get('search', '')
    query = Customer.query
    if search:
        query = query.filter(
            db.or_(
                Customer.name.ilike(f'%{search}%'),
                Customer.email.ilike(f'%{search}%'),
            )
        )
    customers = query.order_by(Customer.name).all()
    return render_template('customers/list.html', customers=customers, search=search)


@customers_bp.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        try:
            customer = Customer(
                name=request.form['name'].strip(),
                email=request.form['email'].strip(),
                phone=request.form.get('phone', '').strip(),
                address=request.form.get('address', '').strip(),
                city=request.form.get('city', '').strip(),
                country=request.form.get('country', '').strip(),
                postal_code=request.form.get('postal_code', '').strip(),
            )
            db.session.add(customer)
            db.session.commit()
            flash(f'Customer "{customer.name}" created!', 'success')
            return redirect(url_for('customers.list_customers'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {e}', 'danger')
    return render_template('customers/create.html')


@customers_bp.route('/<int:customer_id>/edit', methods=['GET', 'POST'])
def edit(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    if request.method == 'POST':
        try:
            customer.name = request.form['name'].strip()
            customer.email = request.form['email'].strip()
            customer.phone = request.form.get('phone', '').strip()
            customer.address = request.form.get('address', '').strip()
            customer.city = request.form.get('city', '').strip()
            customer.country = request.form.get('country', '').strip()
            customer.postal_code = request.form.get('postal_code', '').strip()
            db.session.commit()
            flash('Customer updated!', 'success')
            return redirect(url_for('customers.list_customers'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {e}', 'danger')
    return render_template('customers/edit.html', customer=customer)
