from flask import Flask, redirect, url_for
from config import Config
from extensions import db, mail
from routes import invoices_bp, customers_bp, subscriptions_bp, admin_bp
from apscheduler.schedulers.background import BackgroundScheduler
import logging

logging.basicConfig(level=logging.INFO)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Extensions
    db.init_app(app)
    mail.init_app(app)

    # Register blueprints
    app.register_blueprint(invoices_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(subscriptions_bp)
    app.register_blueprint(admin_bp)

    # Home redirect
    @app.route('/')
    def index():
        return redirect(url_for('invoices.list_invoices'))

    # Create DB tables
    with app.app_context():
        db.create_all()
        _seed_demo_data(app)

    # Start auto-billing scheduler
    _start_scheduler(app)

    return app


def _start_scheduler(app):
    from services.billing_service import schedule_billing
    scheduler = BackgroundScheduler(daemon=True)
    schedule_billing(app, scheduler)
    scheduler.start()


def _seed_demo_data(app):
    """Insert demo data only on first run (empty DB)."""
    from models import Customer, Product, TaxConfig, Subscription
    from datetime import date

    if Customer.query.count() > 0:
        return  # Already seeded

    # Tax
    gst = TaxConfig(name='GST', rate=18.00, description='Goods & Services Tax', is_active=True)
    db.session.add(gst)

    # Products
    basic = Product(name='Basic Plan', description='Basic subscription plan',
                    unit_price=999.00, billing_cycle='monthly', is_active=True)
    pro = Product(name='Pro Plan', description='Professional subscription plan',
                  unit_price=2499.00, billing_cycle='monthly', is_active=True)
    enterprise = Product(name='Enterprise Plan', description='Enterprise yearly plan',
                         unit_price=24999.00, billing_cycle='yearly', is_active=True)
    db.session.add_all([basic, pro, enterprise])

    # Customers
    c1 = Customer(name='Acme Corp', email='billing@acme.com', phone='+1 555-0101',
                  address='100 Main Street', city='New York', country='USA')
    c2 = Customer(name='GlobalTech Ltd', email='accounts@globaltech.io', phone='+44 20 7946 0958',
                  address='10 Tech Park', city='London', country='UK')
    c3 = Customer(name='StartupXYZ', email='finance@startupxyz.com', phone='+91 98765 43210',
                  address='42 Innovation Hub', city='Bangalore', country='India')
    db.session.add_all([c1, c2, c3])
    db.session.flush()

    # Subscriptions
    today = date.today()
    from dateutil.relativedelta import relativedelta
    s1 = Subscription(subscription_number='SUB-000001', customer_id=c1.id,
                      product_id=basic.id, quantity=1, unit_price=999.00,
                      billing_cycle='monthly', start_date=today,
                      next_billing_date=today + relativedelta(months=1),
                      discount_percent=5.00)
    s2 = Subscription(subscription_number='SUB-000002', customer_id=c2.id,
                      product_id=pro.id, quantity=2, unit_price=2499.00,
                      billing_cycle='monthly', start_date=today,
                      next_billing_date=today + relativedelta(months=1))
    s3 = Subscription(subscription_number='SUB-000003', customer_id=c3.id,
                      product_id=enterprise.id, quantity=1, unit_price=24999.00,
                      billing_cycle='yearly', start_date=today,
                      next_billing_date=today + relativedelta(years=1))
    db.session.add_all([s1, s2, s3])
    db.session.commit()


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, use_reloader=False)
