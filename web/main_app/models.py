from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    fname = db.Column(db.String(150))
    lname = db.Column(db.String(150))
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True))


class UserDoc(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    doc_name = db.Column(db.String(200))
    doc_desc = db.Column(db.String(300))
    doc_content_path = db.Column(db.String(500))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True))
    __table_args__ = (db.UniqueConstraint(
        'doc_name', 'doc_desc', name='_docname_docdesc_uc'),)


class UserDocLegTerm(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    term_id = db.Column(db.Integer)
    term_name = db.Column(db.String(300))
    user_doc_id = db.Column(db.Integer, db.ForeignKey('user_doc.id'))
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True))
