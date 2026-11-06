import os
import sys
import sqlite3
from contextlib import closing
from flask import Flask, render_template, request, redirect, url_for, flash

# Path handling: PyInstaller (sys.frozen) vs. ჩვეულებრივი Python
if getattr(sys, "frozen", False):
    RESOURCE_DIR = sys._MEIPASS                      # templates/static აქ არის
    APP_DIR = os.path.dirname(sys.executable)        # shop.db აქ შეინახება
else:
    RESOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
    APP_DIR = RESOURCE_DIR

DB_PATH = os.path.join(APP_DIR, "shop.db")

app = Flask(
    __name__,
    template_folder=os.path.join(RESOURCE_DIR, "templates"),
    static_folder=os.path.join(RESOURCE_DIR, "static"),
)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-service")


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with closing(get_db()) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                code TEXT NOT NULL UNIQUE,
                quantity INTEGER NOT NULL DEFAULT 0,
                price REAL NOT NULL DEFAULT 0
            )
        """)
        conn.commit()


init_db()


@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    with closing(get_db()) as conn:
        if q:
            rows = conn.execute(
                "SELECT * FROM parts WHERE name LIKE ? OR code LIKE ? ORDER BY name",
                (f"%{q}%", f"%{q}%"),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM parts ORDER BY name").fetchall()
    return render_template("index.html", parts=rows, q=q)


@app.route("/add", methods=["POST"])
def add_part():
    name = request.form.get("name", "").strip()
    code = request.form.get("code", "").strip()
    try:
        quantity = int(request.form.get("quantity", 0))
        price = float(request.form.get("price", 0))
    except ValueError:
        flash("რაოდენობა ან ფასი არასწორია.")
        return redirect(url_for("index"))

    if not name or not code:
        flash("სახელი და კოდი სავალდებულოა.")
        return redirect(url_for("index"))

    try:
        with closing(get_db()) as conn:
            conn.execute(
                "INSERT INTO parts (name, code, quantity, price) VALUES (?, ?, ?, ?)",
                (name, code, quantity, price),
            )
            conn.commit()
        flash("ნაწილი დაემატა.")
    except sqlite3.IntegrityError:
        flash("ამ კოდით ნაწილი უკვე არსებობს.")
    return redirect(url_for("index"))


@app.route("/update/<int:part_id>", methods=["POST"])
def update_part(part_id):
    try:
        quantity = int(request.form.get("quantity", 0))
        price = float(request.form.get("price", 0))
    except ValueError:
        flash("რაოდენობა ან ფასი არასწორია.")
        return redirect(url_for("index"))

    with closing(get_db()) as conn:
        conn.execute(
            "UPDATE parts SET quantity = ?, price = ? WHERE id = ?",
            (quantity, price, part_id),
        )
        conn.commit()
    return redirect(url_for("index"))


@app.route("/delete/<int:part_id>", methods=["POST"])
def delete_part(part_id):
    with closing(get_db()) as conn:
        conn.execute("DELETE FROM parts WHERE id = ?", (part_id,))
        conn.commit()
    flash("ნაწილი წაიშალა.")
    return redirect(url_for("index"))
run_server.py
python


from waitress import serve
from app import app, init_db

if __name__ == "__main__":
    init_db()
    serve(app, host="0.0.0.0", port=5000, threads=8)
templates/index.html
html


<!DOCTYPE html>
<html lang="ka">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AutoShop - ინვენტარი</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
    <header>
        <h1>AutoShop - ინვენტარი</h1>
    </header>

    <main>
        {% with messages = get_flashed_messages() %}
            {% for msg in messages %}
                <div class="flash">{{ msg }}</div>
            {% endfor %}
        {% endwith %}

        <section class="card">
            <h2>ახალი ნაწილი</h2>
            <form method="post" action="{{ url_for('add_part') }}" class="grid-form">
                <input name="name" placeholder="სახელი" required>
                <input name="code" placeholder="კოდი" required>
                <input name="quantity" type="number" min="0" value="0" placeholder="რაოდენობა">
                <input name="price" type="number" step="0.01" min="0" value="0" placeholder="ფასი">
                <button type="submit">დამატება</button>
            </form>
        </section>

        <section class="card">
            <h2>ძებნა</h2>
            <form method="get" action="{{ url_for('index') }}" class="search-form">
                <input name="q" value="{{ q }}" placeholder="სახელი ან კოდი">
                <button type="submit">ძებნა</button>
                <a href="{{ url_for('index') }}">გასუფთავება</a>
            </form>
        </section>

        <section class="card">
            <h2>ნაწილები ({{ parts|length }})</h2>
            <table>
                <thead>
                    <tr>
                        <th>სახელი</th>
                        <th>კოდი</th>
                        <th>რაოდენობა</th>
                        <th>ფასი</th>
                        <th>მოქმედება</th>
                    </tr>
                </thead>
                <tbody>
                    {% for p in parts %}
                    <tr>
                        <td>{{ p['name'] }}</td>
                        <td>{{ p['code'] }}</td>
                        <td>
                            <form method="post" action="{{ url_for('update_part', part_id=p['id']) }}" class="inline-form">
                                <input name="quantity" type="number" min="0" value="{{ p['quantity'] }}">
                                <input name="price" type="number" step="0.01" min="0" value="{{ p['price'] }}" class="price-input">
                                <button type="submit">შენახვა</button>
                            </form>
                        </td>
                        <td>{{ "%.2f"|format(p['price']) }}</td>
                        <td>
                            <form method="post" action="{{ url_for('delete_part', part_id=p['id']) }}" onsubmit="return confirm('წავშალო?');">
                                <button type="submit" class="danger">წაშლა</button>
                            </form>
                        </td>
                    </tr>
                    {% else %}
                    <tr><td colspan="5">ნაწილები ვერ მოიძებნა.</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </section>
    </main>
</body>
</html>
static/style.css
css


* { box-sizing: border-box; }
body { font-family: Arial, sans-serif; background: #f2f4f7; margin: 0; color: #222; }
header { background: #1f3b5a; color: #fff; padding: 16px 24px; }
header h1 { margin: 0; font-size: 22px; }
main { max-width: 1100px; margin: 20px auto; padding: 0 16px; }
.card { background: #fff; border-radius: 8px; padding: 16px 20px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,.1); }
.card h2 { margin-top: 0; font-size: 18px; }
.grid-form { display: grid; grid-template-columns: 2fr 1fr 1fr 1fr auto; gap: 8px; }
.search-form { display: flex; gap: 8px; align-items: center; }
input { padding: 8px; border: 1px solid #bbb; border-radius: 4px; font-size: 14px; }
.search-form input { flex: 1; }
button { padding: 8px 14px; background: #1f6feb; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
button:hover { background: #1858c0; }
button.danger { background: #c0392b; }
button.danger:hover { background: #a93226; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 8px; border-bottom: 1px solid #e3e6eb; }
.inline-form { display: flex; gap: 6px; align-items: center; }
.inline-form input { width: 90px; }
.price-input { width: 100px !important; }
.flash { background: #e8f5e9; border: 1px solid #a5d6a7; padding: 10
