from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError

from extensions import db
from forms import LoginForm, RegisterForm
from models import User, utcnow

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.strip()).first()
        if user is None or not user.check_password(form.password.data):
            flash("Invalid username or password.", "danger")
        else:
            user.last_login = utcnow()
            db.session.commit()
            login_user(user)
            target = request.args.get("next", "")
            # Only local absolute paths; reject protocol-relative URLs and backslashes.
            if not target.startswith("/") or target.startswith("//") or "\\" in target:
                target = url_for("main.dashboard")
            return redirect(target)
    return render_template("login.html", form=form)


@bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(username=form.username.data.strip(), email=form.email.data.strip().lower())
        user.set_password(form.password.data)
        try:
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Username or email is already in use.", "danger")
        else:
            flash("Account created. Please log in.", "success")
            return redirect(url_for("auth.login"))
    return render_template("register.html", form=form)


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
