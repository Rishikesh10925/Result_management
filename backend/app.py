import logging
import os
import sys

from flask import Flask, jsonify, request, send_from_directory
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from models import User, db

DIST = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist')


def setup_logging(app):
    # stdout -> journald on EC2; LOG_FILE is what the CloudWatch agent ships
    handlers = [logging.StreamHandler(sys.stdout)]
    if app.config['LOG_FILE']:
        handlers.append(logging.FileHandler(app.config['LOG_FILE']))
    logging.basicConfig(level=logging.INFO, handlers=handlers,
                        format='%(asctime)s %(levelname)s %(name)s: %(message)s')


def create_app():
    app = Flask(__name__, static_folder=None)
    app.config.from_object(Config)
    # behind Nginx on EC2: trust one proxy hop for the client IP in logs
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
    setup_logging(app)
    db.init_app(app)

    login = LoginManager(app)
    login.user_loader(lambda uid: db.session.get(User, int(uid)))
    login.unauthorized_handler(lambda: (jsonify(error='Please log in.'), 401))

    from routes import admin, auth, faculty, student
    for m in (auth, student, faculty, admin):
        app.register_blueprint(m.bp)

    @app.before_request
    def json_only_writes():
        # Browsers cannot send cross-site JSON without a CORS preflight,
        # so requiring JSON on writes blocks CSRF from other sites.
        if request.method in ('POST', 'PUT', 'DELETE') and request.path.startswith('/api/') \
                and request.content_length and not request.is_json:
            return jsonify(error='JSON body required.'), 415

    @app.errorhandler(ValueError)
    def bad_input(e):
        return jsonify(error=str(e)), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify(error='Not found.'), 404

    @app.errorhandler(Exception)
    def server_error(e):
        if hasattr(e, 'code'):
            return jsonify(error=getattr(e, 'description', 'Error')), e.code
        app.logger.exception('unhandled error on %s %s', request.method, request.path)
        return jsonify(error='Something went wrong.'), 500

    @app.get('/api/health')
    def health():
        db.session.execute(db.text('select 1'))
        return jsonify(status='ok')

    # production: Flask serves the built React app (frontend/dist)
    @app.get('/', defaults={'path': ''})
    @app.get('/<path:path>')
    def frontend(path):
        if path and os.path.exists(os.path.join(DIST, path)):
            return send_from_directory(DIST, path)
        if os.path.exists(os.path.join(DIST, 'index.html')):
            return send_from_directory(DIST, 'index.html')
        return 'Frontend not built. Run "npm run build" in frontend/ or use "npm run dev".', 404

    @app.cli.command('seed')
    def seed_command():
        """Create tables and demo accounts (local testing only)."""
        from seed import seed
        seed()

    @app.cli.command('init-db')
    def init_db_command():
        """Create tables and an 'admin' user with ADMIN_PASSWORD (production)."""
        db.create_all()
        if db.engine.dialect.name == 'mysql':
            # tables made before sgpa/cgpa became DOUBLE (FLOAT lost digits)
            db.session.execute(db.text('ALTER TABLE semester_results MODIFY sgpa DOUBLE NOT NULL, MODIFY cgpa DOUBLE NULL'))
            db.session.commit()
        # recalculate stored results from the saved marks (restores full precision)
        from models import Result
        from services import result_service
        for row in Result.query.order_by(Result.student_id, Result.sem).all():
            res = result_service.calculate(row.student, row.sem)
            row.sgpa, row.cgpa = res['sgpa'], res['cgpa']
            db.session.commit()
        password = os.getenv('ADMIN_PASSWORD')
        if not password or len(password) < 8:
            raise SystemExit('Set ADMIN_PASSWORD (8+ characters) in .env first.')
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', name='Administrator', role='admin')
            admin.set_password(password)
            db.session.add(admin)
            db.session.commit()
        print('Tables ready. Log in as admin.')

    return app


app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=os.getenv('FLASK_DEBUG') == '1', port=5000)
