import os
import time
import requests
from flask import Flask, render_template, jsonify
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
app.config["UPLOAD_FOLDER"] = os.path.join("static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB

# Telegram bot credentials
TELEGRAM_BOT_TOKEN = "8193927885:AAFBidm4BsnguwXWptcYtABCBJqRZTXq54o"
TELEGRAM_CHAT_ID = "1618076958"

# ------------------------------------------------------------------
# 2.  FORM DEFINITION
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
# 3.  ROUTES
# ------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/subscribe")
def subscribe():
    form = SubscriptionForm()
    return render_template("subscribe.html", form=form)

# Helper to send Telegram photo with retry & longer timeout
def send_telegram_notification(photo_path: str, caption: str) -> bool:
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    with open(photo_path, "rb") as photo_file:
        files = {"photo": photo_file}
        data = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "HTML"}
        for _ in range(3):  # retry up to 3 times
            try:
                response = requests.post(api_url, data=data, files=files, timeout=60)
                if response.status_code == 200:
                    return True
            except requests.exceptions.RequestException as e:
                print(f"Telegram request failed: {e}, retrying...")
                time.sleep(2)
    return False

@app.route("/submit_subscription", methods=["POST"])
def submit_subscription():
    form = SubscriptionForm()
    if not form.validate_on_submit():
        return jsonify(
            {"success": False, "message": "Form validation failed", "errors": form.errors}
        ), 400

    # Save screenshot
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    filename = f"{int(time.time())}_{secure_filename(form.payment_screenshot.data.filename)}"
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    form.payment_screenshot.data.save(save_path)

    # Send Telegram notification
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

    # Success response (JS handles toast + redirect)
    return jsonify(
        {
            "success": True,
            "message": "Form submitted successfully! Redirecting…",
            "redirect": "https://t.me/+o3POA0Le3_M0YzQ1",
        }
    )

# ------------------------------------------------------------------
# 4.  APP STARTUP
# ------------------------------------------------------------------
# if __name__ == "__main__":
#     app.run(debug=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

