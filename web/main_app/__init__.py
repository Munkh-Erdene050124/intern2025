from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from flask_login import LoginManager, current_user
from .services import mwe_service, tsv2json
import os

UPLOAD_FOLDER = '../main_app/static/uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}
db = SQLAlchemy()
DB_NAME = "database.db"
data_path = './main_app/static/data/merge_lt_dict_v3.tsv'
json_path = './main_app/static/json/merge_lt_dict_v3.json'
doc_path = './main_app/static/data/dic_document_v2.tsv'
doc_json_path = './main_app/static/json/dic_document_v2.json'
coocur_path = './main_app/static/data/coocur_4v1.tsv'
coocur_json_path = './main_app/static/json/coocur_4v1.json'
df = mwe_service.read_tsv(data_path)
trie = mwe_service.create_trie(data_path)
tsv2json.run(data_path, json_path)
tsv2json.run(doc_path, doc_json_path)
tsv2json.run(coocur_path, coocur_json_path)


def page_not_found(error):
    return render_template('not_found.html', data={'user': current_user}), 404


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'bopisqxjiz-kmhipemylt-yjqdllkjmn'
    create_engine(f'sqlite:///{DB_NAME}')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    app.config['TEMPLATE_FOLDER'] = os.path.join(
        os.getcwd(), '../main_app/templates')
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
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
