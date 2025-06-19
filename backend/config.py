import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(basedir, 'instance', 'app.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = "jwt_secret_key"
    JWT_TOKEN_LOCATION = ["headers"] 

    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = "projectappmail1998@gmail.com"
    MAIL_PASSWORD = "hirm xovn cikd jskq"  
    MAIL_DEFAULT_SENDER = "projectappmail1998@gmail.com"