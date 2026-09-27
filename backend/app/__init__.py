from flask import Flask, jsonify

from app.config import Config
from app.extensions import db, jwt, mail, cors, limiter


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    limiter.init_app(app)

    from app.auth import auth_bp
    from app.profile_mgmt import profile_bp
    from app.skills import skills_bp
    from app.ai_engine import ai_bp
    from app.sessions import sessions_bp
    from app.feedback import feedback_bp
    from app.notifications import notifications_bp
    from app.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(skills_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(sessions_bp)
    app.register_blueprint(feedback_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(admin_bp)

    from app.cli import register_cli
    register_cli(app)

    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    @app.errorhandler(404)
    def not_found(e):
        return jsonify(error="not found"), 404

    @app.errorhandler(429)
    def rate_limited(e):
        return jsonify(error="too many requests, please slow down"), 429

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception(e)
        return jsonify(error="internal server error"), 500

    return app
