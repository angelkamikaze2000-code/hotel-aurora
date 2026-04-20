from flask import Flask

from .config import Config
from .extensions import db, jwt, migrate
from . import models
from .routes.ads import ads_bp
from .routes.admin import admin_bp
from .routes.auth import auth_bp
from .routes.payments import payments_bp
from .routes.reservations import reservations_bp
from .routes.rooms import rooms_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(rooms_bp, url_prefix="/api/rooms")
    app.register_blueprint(reservations_bp, url_prefix="/api/reservations")
    app.register_blueprint(ads_bp, url_prefix="/api/ads")
    app.register_blueprint(payments_bp, url_prefix="/api/payments")

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        return response

    @app.get("/api/health")
    def health():
        return {"status": "ok", "service": "hotel-aurora-backend"}

    return app
