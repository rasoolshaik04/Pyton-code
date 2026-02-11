from flask import Flask, render_template, send_file, request
import qrcode
import io
import sys
import calendar
from datetime import datetime

app = Flask(__name__)

@app.route("/")
def home():
    return render_template('index.html')


@app.route("/qr")
def ge():
    data = "https://www.youtube.com/"

    qr = qrcode.make(data)

    img_io = io.BytesIO()
    qr.save(img_io, "PNG")
    img_io.seek(0)

    return send_file(img_io, mimetype="image/png")


@app.route("/calendar")
def show_calendar():
    year = request.args.get('year', default=datetime.now().year, type=int)
    month = request.args.get('month', default=datetime.now().month, type=int)
    
    try:
        cal = calendar.month(year, month)
        html = f"""
        <html>
        <head>
            <title>Calendar</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                pre {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                a {{ margin: 10px; text-decoration: none; color: blue; }}
                a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <h1>Calendar - {calendar.month_name[month]} {year}</h1>
            <pre>{cal}</pre>
            <br>
            <a href="/calendar?year={year}&month={month-1 if month > 1 else 12}">← Previous</a>
            <a href="/calendar">Today</a>
            <a href="/calendar?year={year}&month={month+1 if month < 12 else 1}">Next →</a>
        </body>
        </html>
        """
        return html
    except ValueError:
        return f"Invalid year or month. Please use /calendar?year=YYYY&month=MM", 400


@app.route("/datetime")
def show_datetime():
    now = datetime.now()
    date_str = now.strftime("%A, %B %d, %Y")
    time_str = now.strftime("%H:%M:%S")
    return render_template('datetime.html', date_str=date_str, time_str=time_str)


@app.route("/valentine")
def show_valentine():
    now = datetime.now()
    valentine_day = datetime(2026, 2, 14)
    days_until = (valentine_day - now).days
    
    message = ""
    if days_until > 0:
        message = f"❤️ {days_until} days until Valentine's Day! ❤️"
    elif days_until == 0:
        message = "💕 Happy Valentine's Day! 💕"
    else:
        message = f"Valentine's Day was {abs(days_until)} days ago!"
    return render_template('valentine.html', message=message)


if __name__ == "__main__":
    print("Starting Flask app...", flush=True)
    sys.stdout.flush()
    app.run(host="0.0.0.0", port=5000, debug=True)