"""Profile routes; named account to avoid shadowing Python's profile module."""

from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from extensions import db
from forms import PasswordForm, ProfileForm
from main import save_image

bp = Blueprint("profile", __name__)


@bp.get("/")
@login_required
def view_profile():
    return render_template("profile.html")


@bp.route("/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.username = form.username.data.strip()
        current_user.email = form.email.data.strip().lower() or None
        current_user.bio = form.bio.data
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Username or email is already in use.", "danger")
        else:
            return redirect(url_for("profile.view_profile"))
    return render_template("form.html", title="Edit profile", form=form)


@bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = PasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash("Password changed.", "success")
            return redirect(url_for("profile.view_profile"))
        flash("Current password is incorrect.", "danger")
    return render_template("form.html", title="Change password", form=form)


@bp.post("/avatar")
@login_required
def update_avatar():
    filename = save_image(request.files.get("avatar"))
    if filename:
        try:
            current_user.avatar = filename
            db.session.commit()
        except Exception:
            db.session.rollback()
            (Path(current_app.config["UPLOAD_FOLDER"]) / filename).unlink(missing_ok=True)
            raise
    return redirect(url_for("profile.view_profile"))


@bp.get("/avatar/image")
@login_required
def avatar_image():
    filename = current_user.avatar
    if not filename:
        abort(404)
    folder = Path(current_app.config["UPLOAD_FOLDER"])
    if not (folder / filename).is_file():
        folder = Path(current_app.root_path) / "static/avatars"
    return send_from_directory(folder, filename)
