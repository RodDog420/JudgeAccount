import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    
    SECRET_KEY = os.environ.get('SECRET_KEY') 
    
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') 
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False   
    
    # Email configuration for Gmail SMTP
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or 'Admin@JudgeAccount.com'
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = 'Admin@JudgeAccount.com'
    
    # Admin email for notifications
    ADMIN_EMAIL = 'Admin@JudgeAccount.com'
