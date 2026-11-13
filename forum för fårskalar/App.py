import mysql.connector
from flask import Flask, flash, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = "byt-denna-nyckel"

databas = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "farforum",
}


def ensure_likes_table(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS likes (
            user_id INT NOT NULL,
            post_id INT NOT NULL,
            reaction ENUM('like', 'dislike') NOT NULL,
            PRIMARY KEY (user_id, post_id)
        )
        """
    )

    cursor.execute("SHOW COLUMNS FROM likes LIKE 'reaction'")
    if cursor.fetchone() is None:
        cursor.execute(
            "ALTER TABLE likes ADD COLUMN reaction ENUM('like', 'dislike') NOT NULL DEFAULT 'like' AFTER post_id"
        )
        cursor.execute(
            "UPDATE likes SET reaction = 'like' WHERE reaction IS NULL OR reaction = ''"
        )


def set_reaction(post_id, reaction, success_message):
    if "user_id" not in session:
        flash("Logga in för att reagera på inlägg.")
        return redirect("/logga-in")

    connection = mysql.connector.connect(**databas)
    cursor = connection.cursor()
    ensure_likes_table(cursor)
    cursor.execute("SELECT id FROM posts WHERE id = %s", (post_id,))
    if cursor.fetchone() is None:
        cursor.close()
        connection.close()
        flash("Inlägget finns inte.")
        return redirect("/")

    cursor.execute(
        "SELECT reaction FROM likes WHERE user_id = %s AND post_id = %s",
        (session["user_id"], post_id),
    )
    existing_reaction = cursor.fetchone()

    if existing_reaction and existing_reaction[0] == reaction:
        flash("Du har redan valt den här reaktionen.")
        cursor.close()
        connection.close()
        return redirect("/")

    cursor.execute(
        """
        INSERT INTO likes (user_id, post_id, reaction) VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE reaction = VALUES(reaction)
        """,
        (session["user_id"], post_id, reaction),
    )
    connection.commit()
    cursor.close()
    connection.close()

    flash(success_message)
    return redirect("/")


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if "user_id" not in session:
            return redirect("/logga-in")

        text = request.form["message"].strip()
        if text:
            connection = mysql.connector.connect(**databas)
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO posts (user_id, message) VALUES (%s, %s)",
                (session["user_id"], text),
            )
            connection.commit()
            cursor.close()
            connection.close()
            flash("Ditt inlägg har publicerats.")

        return redirect("/")

    connection = mysql.connector.connect(**databas)
    cursor = connection.cursor(dictionary=True)
    ensure_likes_table(cursor)
    cursor.execute(
        """
        SELECT posts.id, posts.message, posts.created_at, users.username,
            -- TODO: Select users.profile_picture after adding the column.
            COALESCE(SUM(CASE WHEN likes.reaction = 'like' THEN 1 ELSE 0 END), 0) AS like_count,
            COALESCE(SUM(CASE WHEN likes.reaction = 'dislike' THEN 1 ELSE 0 END), 0) AS dislike_count,
            COALESCE(MAX(CASE WHEN likes.user_id = %s AND likes.reaction = 'like' THEN 1 ELSE 0 END), 0) AS liked_by_user,
            COALESCE(MAX(CASE WHEN likes.user_id = %s AND likes.reaction = 'dislike' THEN 1 ELSE 0 END), 0) AS disliked_by_user
        FROM posts
        JOIN users ON posts.user_id = users.id
        LEFT JOIN likes ON likes.post_id = posts.id
        GROUP BY posts.id, posts.message, posts.created_at, users.username
        ORDER BY posts.id DESC
        """,
        (session.get("user_id"), session.get("user_id")),
    )
    posts = cursor.fetchall()
    cursor.close()
    connection.close()

    return render_template("index.html", posts=posts)


@app.route("/inlagg/<int:post_id>/gilla", methods=["POST"])
def like_post(post_id):
    return set_reaction(post_id, "like", "Inlägget är gillat.")


@app.route("/inlagg/<int:post_id>/ogilla", methods=["POST"])
def dislike_post(post_id):
    return set_reaction(post_id, "dislike", "Inlägget är ogillat.")


@app.route("/registrera", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        profile_picture = request.files.get("profile_picture")

        connection = mysql.connector.connect(**databas)
        cursor = connection.cursor()
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user:
            flash("Användarnamnet används redan.")
        elif len(password) < 8:
            flash("Lösenordet måste ha minst 8 tecken.")
        else:
            password_hash = generate_password_hash(password)
            # TODO: Validate and save profile_picture, then store its filename in the database.
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (username, password_hash),
            )
            connection.commit()
            session["user_id"] = cursor.lastrowid
            session["username"] = username
            cursor.close()
            connection.close()
            flash("Kontot är skapat!")
            return redirect("/")

        cursor.close()
        connection.close()

    return render_template("register.html")


@app.route("/logga-in", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        connection = mysql.connector.connect(**databas)
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, username, password_hash FROM users WHERE username = %s",
            (username,),
        )
        user = cursor.fetchone()
        cursor.close()
        connection.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            # TODO: Load the saved profile-picture filename into the session.
            flash("Du är inloggad.")
            return redirect("/")

        flash("Fel användarnamn eller lösenord.")

    return render_template("login.html")


@app.route("/logga-ut", methods=["POST"])
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
