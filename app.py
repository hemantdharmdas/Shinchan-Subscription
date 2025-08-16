# ───────────────────────────── app.py ─────────────────────────────
import os
import time
import requests
from flask import Flask, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, FileField
from wtforms.validators import DataRequired, Length, Regexp
from flask_wtf.file import FileAllowed, FileRequired
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# ------------------------------------------------------------------
# 1.  BASIC SETUP
# ------------------------------------------------------------------
load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///subscriptions.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = os.path.join("static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB

# Telegram bot credentials
TELEGRAM_BOT_TOKEN = "8193927885:AAFBidm4BsnguwXWptcYtABCBJqRZTXq54o"
TELEGRAM_CHAT_ID = "1618076958"

db = SQLAlchemy(app)

# ------------------------------------------------------------------
# 2.  DATABASE MODEL
# ------------------------------------------------------------------
class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    telegram = db.Column(db.String(100), nullable=False)
    instagram = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(10), nullable=False)
    payment_screenshot = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

# ------------------------------------------------------------------
# 3.  FORM DEFINITION
# ------------------------------------------------------------------
class SubscriptionForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=100)])
    telegram = StringField("Telegram Username", validators=[DataRequired(), Length(max=100)])
    instagram = StringField("Instagram Username", validators=[DataRequired(), Length(max=100)])
    phone = StringField("Phone Number", validators=[DataRequired(), Regexp(r"^\d{10}$")])
    payment_screenshot = FileField(
        "Payment Screenshot",
        validators=[FileRequired(), FileAllowed(["jpg", "jpeg", "png"], "Images only!")]
    )

# ------------------------------------------------------------------
# 4.  ROUTES
# ------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/subscribe")
def subscribe():
    form = SubscriptionForm()
    return render_template("subscribe.html", form=form)

# Helper to send Telegram photo
def send_telegram_notification(photo_path: str, caption: str) -> bool:
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    with open(photo_path, "rb") as photo_file:
        files = {"photo": photo_file}
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "caption": caption,
            "parse_mode": "HTML",
        }
        response = requests.post(api_url, data=data, files=files, timeout=15)
    return response.status_code == 200

@app.route("/submit_subscription", methods=["POST"])
def submit_subscription():
    form = SubscriptionForm()
    if not form.validate_on_submit():
        return jsonify(
            {"success": False, "message": "Form validation failed", "errors": form.errors}
        ), 400

    # 1. Save screenshot
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    filename = f"{int(time.time())}_{secure_filename(form.payment_screenshot.data.filename)}"
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    form.payment_screenshot.data.save(save_path)

    # 2. Write to DB
    new_sub = Subscription(
        name=form.name.data,
        telegram=form.telegram.data,
        instagram=form.instagram.data,
        phone=form.phone.data,
        payment_screenshot=filename,
    )
    db.session.add(new_sub)
    db.session.commit()

    # 3. Send Telegram notification
    caption = (
        "<b>New Subscription Received</b>\n"
        f"Name: {form.name.data}\n"
        f"Telegram: {form.telegram.data}\n"
        f"Instagram: {form.instagram.data}\n"
        f"Phone: {form.phone.data}"
    )
    if not send_telegram_notification(save_path, caption):
        return jsonify(
            {"success": False, "message": "Failed to send Telegram notification"}
        ), 500

    # 4. Success response (toast + redirect handled in JS)
    return jsonify(
        {
            "success": True,
            "message": "Form submitted successfully! Redirecting…",
            "redirect": "https://t.me/+o3POA0Le3_M0YzQ1",
        }
    )

# ------------------------------------------------------------------
# 5.  APP STARTUP
# ------------------------------------------------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
