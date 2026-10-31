import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///subscription_management.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Mail config
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')

    # Invoice config
    INVOICE_DUE_DAYS = int(os.environ.get('INVOICE_DUE_DAYS', 30))
    COMPANY_NAME = os.environ.get('COMPANY_NAME', 'Subscription Co.')
    COMPANY_ADDRESS = os.environ.get('COMPANY_ADDRESS', '123 Business Ave, Suite 100')
    COMPANY_PHONE = os.environ.get('COMPANY_PHONE', '+1 800 000 0000')
    COMPANY_EMAIL = os.environ.get('COMPANY_EMAIL', 'billing@company.com')

