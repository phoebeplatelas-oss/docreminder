from flask import Flask, render_template, request, redirect
import sqlite3
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from datetime import datetime, timedelta
from flask_mail import Mail, Message



app = Flask(__name__)
app.config['SCHEDULER_API_ENABLED'] = True


app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "phoebeplatelas@gmail.com"
app.config["MAIL_PASSWORD"] = ""  
mail = Mail(app)

jobstores = {
    "default": SQLAlchemyJobStore(url="sqlite:///jobs.db")
}

scheduler = BackgroundScheduler(jobstores=jobstores)
scheduler.start()

UPLOAD_FOLDER = os.path.join("static", "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db():
    conn = sqlite3.connect("photos.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            name TEXT,
            due_date TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/view")
def view():
    conn = get_db()
    photos = conn.execute("SELECT * FROM photos ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("view.html", photos=photos)

def send_reminder_email(name, due_date):
    with app.app_context():
        msg = Message(
            subject=f"Reminder: {name} due in a week",
            sender="phoebeplatelas@gmail.com",
            recipients=["phoebeplatelas@gmail.com"],
            body=f"{name} is due on {due_date}."
        )
        mail.send(msg)

@app.route("/upload", methods=["POST"])
def upload():
    photo = request.files["photo"]
    name = request.form.get("name")
    due_date = request.form.get("date")

    if photo.filename == "":
        return "No file selected", 400
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], photo.filename)
    photo.save(filepath)

    conn = get_db()
    conn.execute(
        "INSERT INTO photos (filename, name, due_date, created_at) VALUES (?, ?, ?, ?)",
        (photo.filename, name, due_date, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    due = datetime.strptime(due_date, "%Y-%m-%d")
    reminder_time =due - timedelta(days=7)

    if reminder_time > datetime.now():  
        scheduler.add_job(send_reminder_email,"date",run_date=reminder_time, args=[name, due_date])

    return redirect("/view")



init_db()
if __name__ == "__main__":
    app.run(debug=False)
