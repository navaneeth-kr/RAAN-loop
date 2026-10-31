from flask import Blueprint, render_template, request, redirect, url_for, flash
from extensions import db
from models import TaxConfig, Product

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# ── Tax Configuration ─────────────────────────────────────────────────────────

@admin_bp.route('/tax')
def tax_list():
    taxes = TaxConfig.query.order_by(TaxConfig.created_at.desc()).all()
    return render_template('admin/tax_list.html', taxes=taxes)


@admin_bp.route('/tax/create', methods=['GET', 'POST'])
def tax_create():
    if request.method == 'POST':
        try:
            tax = TaxConfig(
                name=request.form['name'].strip(),
                rate=float(request.form['rate']),
                description=request.form.get('description', '').strip(),
                is_active=request.form.get('is_active') == 'on',
            )
            db.session.add(tax)
            db.session.commit()
            flash(f'Tax "{tax.name}" ({tax.rate}%) created!', 'success')
            return redirect(url_for('admin.tax_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {e}', 'danger')
    return render_template('admin/tax_form.html', tax=None)


@admin_bp.route('/tax/<int:tax_id>/edit', methods=['GET', 'POST'])
def tax_edit(tax_id):
    tax = TaxConfig.query.get_or_404(tax_id)
    if request.method == 'POST':
        try:
            tax.name = request.form['name'].strip()
            tax.rate = float(request.form['rate'])
            tax.description = request.form.get('description', '').strip()
            tax.is_active = request.form.get('is_active') == 'on'
            db.session.commit()
            flash('Tax updated!', 'success')
            return redirect(url_for('admin.tax_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {e}', 'danger')
    return render_template('admin/tax_form.html', tax=tax)


@admin_bp.route('/tax/<int:tax_id>/delete', methods=['POST'])
def tax_delete(tax_id):
    tax = TaxConfig.query.get_or_404(tax_id)
    db.session.delete(tax)
    db.session.commit()
    flash('Tax deleted.', 'warning')
    return redirect(url_for('admin.tax_list'))


# ── Products ──────────────────────────────────────────────────────────────────

@admin_bp.route('/products')
def product_list():
    products = Product.query.order_by(Product.name).all()
    return render_template('admin/product_list.html', products=products)


@admin_bp.route('/products/create', methods=['GET', 'POST'])
def product_create():
    if request.method == 'POST':
        try:
            p = Product(
                name=request.form['name'].strip(),
                description=request.form.get('description', '').strip(),
                unit_price=float(request.form['unit_price']),
                billing_cycle=request.form.get('billing_cycle', 'monthly'),
                is_active=request.form.get('is_active') == 'on',
            )
            db.session.add(p)
            db.session.commit()
            flash(f'Product "{p.name}" created!', 'success')
            return redirect(url_for('admin.product_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {e}', 'danger')
    return render_template('admin/product_form.html', product=None)


@admin_bp.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
def product_edit(product_id):
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        try:
            product.name = request.form['name'].strip()
            product.description = request.form.get('description', '').strip()
            product.unit_price = float(request.form['unit_price'])
            product.billing_cycle = request.form.get('billing_cycle', 'monthly')
            product.is_active = request.form.get('is_active') == 'on'
            db.session.commit()
            flash('Product updated!', 'success')
            return redirect(url_for('admin.product_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {e}', 'danger')
    return render_template('admin/product_form.html', product=product)
