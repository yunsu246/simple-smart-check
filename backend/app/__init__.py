from flask import Flask
from .api import apiBlueprint
from .config import Config
from .models import RevokedTokenModel
from .extensions import db, jwt, cors


# -------------------[ Flask App Settings ]----------------------------------
# Create Flask app
def create_app():
    app = Flask(__name__)
    # Set app.config from app.config.py
    app.config.from_object(Config)
    # Register modules to URL with Blueprint : Working as an API Router.
    app.register_blueprint(apiBlueprint)
    return app

# Register Flask app extensions
def register_extentions(app):
    # Initailize db connection from app.extensions.py
    db.init_app(app)
    # Initailize cors session from app.extensions.py
    cors.init_app(app, origins=Config.CORS_ORIGIN)
    # Initailize jwt session from app.extensions.py
    jwt.init_app(app)
# ---------------------------------------------------------------------------


# -------------------[ Flask App Instance Start ]----------------------------
app = create_app()
register_extentions(app)
# ---------------------------------------------------------------------------


# -----[ Execute with specific condition after Flask App starts. ]-----------
# Create DB tables when DB has no scheam/a query is called at the first time.
@app.before_first_request
def create_tables():
    db.create_all()

# Block api request with blacklisted access token
@jwt.token_in_blacklist_loader
def check_if_token_in_blacklist(decrypted_token):
    jti = decrypted_token['jti']
    return RevokedTokenModel.is_jti_blacklisted(jti)

@apiBlueprint.after_request
def add_header(response):
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    return response
# ---------------------------------------------------------------------------