import json
from datetime import datetime
from pathlib import Path

from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)
JSON_FILE = Path(__file__).parent / "inlagg.json"


def read_entries():
	if not JSON_FILE.exists():
		return []

	with JSON_FILE.open("r", encoding="utf-8") as file:
		return json.load(file)


def save_entries(entries):
	with JSON_FILE.open("w", encoding="utf-8") as file:
		json.dump(entries, file, ensure_ascii=False, indent=2)


@app.route("/", methods=["GET", "POST"])
def index():
	if request.method == "POST":
		name = request.form.get("name", "").strip()
		email = request.form.get("email", "").strip()
		message = request.form.get("message", "").strip()
		email_parts = email.split("@")
		valid_email = (
			len(email_parts) == 2
			and email_parts[0]
			and "." in email_parts[1]
		)

		if name and message and valid_email:
			entries = read_entries()
			entries.append({
				"name": name,
				"email": email,
				"message": message,
				"time": datetime.now().strftime("%Y-%m-%d %H:%M"),
			})
			save_entries(entries)
		else:
			return render_template(
				"index.html",
				entries=read_entries(),
				error="Skriv en giltig e-postadress, till exempel namn@mail.com.",
			)

		return redirect(url_for("index"))

	return render_template("index.html", entries=read_entries())


if __name__ == "__main__":
	app.run(debug=True)