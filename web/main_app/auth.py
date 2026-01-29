from flask import Blueprint, render_template, request, flash, url_for, redirect
import mail
from .models import User
from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user
from flask_mail import Message
import random

auth = Blueprint('auth', __name__)


@auth.route('/register', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        lname = request.form.get('lname')
        fname = request.form.get('fname')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_pass = request.form.get('confirm_pass')

        user = User.query.filter_by(email=email.lower()).first()
        if user:
            flash('И-мэйл бүртгэлтэй байна.', category='warning')
        elif len(email) < 5:
            flash('Таны и-мэйл хаяг 5 буюу дээш урттай байх шаардлагатай.',
                  category='error')
        elif len(lname) < 2:
            flash('Таны овог 2 буюу дээш урттай байх шаардлагатай.', category='error')
        elif len(fname) < 2:
            flash('Таны нэр 2 буюу дээш урттай байх шаардлагатай.', category='error')
        elif len(password) < 8:
            flash('Таны нууц үг 8 буюу дээш урттай байх шаардлагатай.',
                  category='error')
        elif password != confirm_pass:
            flash('Нууц үгнүүд таарахгүй байна.', category='error')
        else:
            new_user = User(email=email.lower(), fname=fname, lname=lname,
                            password=generate_password_hash(password))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember=True)
            flash('Амжилттай бүртгэгдлээ.', category='success')
            return redirect(url_for('auth.login'))
    return render_template('register.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email.lower()).first()
        if user:
            if check_password_hash(user.password, password):
                flash('Амжилттай нэвтэрлээ.', category='success')
                login_user(user, remember=True)
                return redirect(url_for('views.priv_home'))
            else:
                flash('Нууц үг буруу байна, та дахин оролдоно уу.', category='error')
        else:
            flash('Бүртгэл олдсонгүй.', category='error')
    return render_template('login.html')


@auth.route('/forgot-pass', methods=['GET', 'POST'])
def forgot_pass():
    if request.method == 'POST':
        email = request.form.get('email')

        user = User.query.filter_by(email=email.lower()).first()
        if user:
            msg = Message('DAS нууц үг сэргээх',
                          sender='19B1NUM0700@stud.num.edu.mn', recipients=[user.email])
            rand_num = random.randint(10000, 99999)
            msg.body = "Сайн байна уу " + \
                user.lname[0]+"."+user.fname + \
                ", \n\tТаны нууц үг сэргээх нэг удаагийн нууц үг: " + rand_num
            mail.send(msg)
            flash('Таны и-мейл хаяг руу нэг удаагийн код илгээсэн.',
                  category='success')
        else:
            flash('Бүртгэл олдсонгүй.', category='error')
    return render_template('forgot_pass.html')


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('views.home'))
