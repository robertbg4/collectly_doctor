from flask import Flask, redirect
from flask_wtf import CSRFProtect

from config import SECRET_KEY
from app.controllers import main_blueprint


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = SECRET_KEY

    csrf = CSRFProtect(app)

    with app.app_context():
        app.register_blueprint(main_blueprint)

        @app.errorhandler(404)
        def page_not_found(e):
            return redirect("/appointments", 301)

    return app
