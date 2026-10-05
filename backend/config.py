import os

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))


def database_url():
    # MySQL locally / Amazon RDS in production. Falls back to SQLite when
    # DB_HOST is not set so the app can run without a database server.
    host = os.getenv('DB_HOST')
    if not host:
        return 'sqlite:///' + os.path.join(os.path.dirname(__file__), 'resultcloud.db')
    return 'mysql+pymysql://{}:{}@{}:{}/{}'.format(
        os.getenv('DB_USER'), os.getenv('DB_PASSWORD'), host,
        os.getenv('DB_PORT', '3306'), os.getenv('DB_NAME', 'resultcloud'))


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-only-change-me')
    SQLALCHEMY_DATABASE_URI = database_url()
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True}
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    S3_BUCKET = os.getenv('S3_BUCKET')
    AWS_REGION = os.getenv('AWS_REGION', 'ap-south-1')
    LOG_FILE = os.getenv('LOG_FILE')  # e.g. /var/log/resultcloud/app.log for CloudWatch agent
