from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from flask_login import LoginManager, current_user
from pathlib import Path
import os
# services import moved inside create_app to avoid circular context issues if needed, 
# but keeping here as per original structure but careful about config usage
from .services import mwe_service, tsv2json

# Path setup
APP_DIR = Path(__file__).resolve().parent  # .../v2/web/main_app
WEB_DIR = APP_DIR.parent                   # .../v2/web
V2_DIR = WEB_DIR.parent                    # .../v2

# Define critical paths
TSV_DICT_PATH = V2_DIR / "tsv-data" / "merge_lt_dict_v3.tsv"
UPLOAD_FOLDER = APP_DIR / "static" / "uploads"

# Constants
NLP_URL = "http://speech.mn:8081/nlp-web-demo/process"
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}
DB_NAME = "database.db"

db = SQLAlchemy()

# Data paths for internal app usage (coocur etc) - keeping relatively static for now 
# or updating if they exist in tsv-data. 
# User only strictly requested merge_lt_dict_v3 from tsv-data.
# The original code loaded these globally. We will move loading to create_app or specific views 
# to ensure config is ready, BUT original code uses global 'df' and 'trie'.
# We need to initialize them AFTER config is set or lazily.
# FOR NOW: We will keep global var declaration but initialize them in create_app or use simple global logic 
# IF the file exists. 
# However, to use V2_DIR, we can just load them here if simple script execution isn't a constraint.
# Use the new path for the main dictionary.

data_path = str(TSV_DICT_PATH)
# Other paths kept as legacy relative to main_app if they are specific to web visualization
doc_path = str(APP_DIR / 'static/data/dic_document_v2.tsv')
doc_json_path = str(APP_DIR / 'static/json/dic_document_v2.json')
coocur_path = str(APP_DIR / 'static/data/coocur_4v1.tsv')
coocur_json_path = str(APP_DIR / 'static/json/coocur_4v1.json')
json_path = str(APP_DIR / 'static/json/merge_lt_dict_v3.json') # This might need to be regen'd from the new source

# Global objects (initially None or loaded if path exists)
df = None
trie = None

def load_global_data():
    global df, trie
    # Ensure fallback if file missing during dev
    if os.path.exists(data_path):
        df = mwe_service.read_tsv(data_path)
        trie = mwe_service.create_trie(data_path)
        tsv2json.run(data_path, json_path)
    if os.path.exists(doc_path):
        tsv2json.run(doc_path, doc_json_path)
    if os.path.exists(coocur_path):
        tsv2json.run(coocur_path, coocur_json_path)

load_global_data()

def page_not_found(error):
    return render_template('not_found.html', data={'user': current_user}), 404


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'bopisqxjiz-kmhipemylt-yjqdllkjmn'
    
    # DB setup
    db_path = WEB_DIR / "instance" / DB_NAME
    if not db_path.parent.exists():
        db_path.parent.mkdir(parents=True)
        
    create_engine(f'sqlite:///{db_path}')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['TEMPLATE_FOLDER'] = str(APP_DIR / 'templates')
    
    # Config injection
    app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
    app.config['LT_DICT_PATH'] = str(TSV_DICT_PATH)
    app.config['NLP_URL'] = NLP_URL
    
    app.config['MAX_CONTENT_LENGTH'] = 20 * 1000 * 1000
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 465
    app.config['MAIL_USERNAME'] = 'bagabandi.erd9920@gmail.com'
    app.config['MAIL_PASSWORD'] = 'B@gaa-010520'
    app.config['MAIL_USE_TLS'] = False
    app.config['MAIL_USE_SSL'] = True
    app.register_error_handler(404, page_not_found)
    db.init_app(app)

    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    from .models import User, UserDoc
    with app.app_context():
        from . import views
        db.create_all()
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Та уг хуудас руу хандахын тулд нэвтрэх шаардлагатай."
    login_manager.login_message_category = "warning"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    app.add_url_rule(
        "/uploads/<name>", endpoint="download_file", build_only=True
    )

    return app
