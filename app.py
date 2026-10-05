from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime
from pathlib import Path
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "digital_addiction.db"
DATA_PATH = BASE_DIR / "data" / "digital_addiction_dataset.csv"

FEATURES = [
    "daily_screen_time",
    "social_media_hours",
    "gaming_hours",
    "night_phone_usage",
    "sleep_hours",
    "notifications_per_day",
    "app_opens_per_day",
]

FEATURE_LABELS = {
    "daily_screen_time": "Daily Screen Time",
    "social_media_hours": "Social Media Hours",
    "gaming_hours": "Gaming Hours",
    "night_phone_usage": "Night-time Phone Usage",
    "sleep_hours": "Sleep Hours",
    "notifications_per_day": "Notifications Per Day",
    "app_opens_per_day": "App Opens Per Day",
}

model = None
model_accuracy = 0.0


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                daily_screen_time REAL NOT NULL,
                social_media_hours REAL NOT NULL,
                gaming_hours REAL NOT NULL,
                night_phone_usage REAL NOT NULL,
                sleep_hours REAL NOT NULL,
                notifications_per_day INTEGER NOT NULL,
                app_opens_per_day INTEGER NOT NULL,
                risk_class INTEGER NOT NULL,
                risk_label TEXT NOT NULL,
                probability REAL NOT NULL
            )
        """)
        conn.commit()


def train_model():
    global model, model_accuracy
    df = pd.read_csv(DATA_PATH)
    X = df[FEATURES]
    y = df["risk"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(max_iter=1000, random_state=42))
    ])
    model.fit(X_train, y_train)
    model_accuracy = accuracy_score(y_test, model.predict(X_test))


def predict(values):
    row = pd.DataFrame([values], columns=FEATURES)
    probability = float(model.predict_proba(row)[0][1])
    risk_class = int(probability >= 0.50)

    if probability < 0.35:
        label = "Low Risk"
    elif probability < 0.65:
        label = "Moderate Risk"
    else:
        label = "High Risk"

    return risk_class, label, probability


@app.route("/")
def index():
    return render_template(
        "index.html",
        accuracy=round(model_accuracy * 100, 1),
        labels=FEATURE_LABELS
    )


@app.route("/predict", methods=["POST"])
def predict_route():
    try:
        data = request.get_json(force=True)
        values = [float(data[f]) for f in FEATURES]

        # Basic sanity checks
        if not (0 <= values[0] <= 24):
            raise ValueError("Daily screen time must be between 0 and 24 hours.")
        if not (0 <= values[1] <= 24):
            raise ValueError("Social media hours must be between 0 and 24.")
        if not (0 <= values[2] <= 24):
            raise ValueError("Gaming hours must be between 0 and 24.")
        if not (0 <= values[3] <= 24):
            raise ValueError("Night-time phone usage must be between 0 and 24.")
        if not (0 <= values[4] <= 24):
            raise ValueError("Sleep hours must be between 0 and 24.")
        if not (0 <= values[5] <= 5000):
            raise ValueError("Notifications per day is out of range.")
        if not (0 <= values[6] <= 2000):
            raise ValueError("App opens per day is out of range.")

        risk_class, label, probability = predict(values)

        with get_db() as conn:
            conn.execute("""
                INSERT INTO predictions (
                    created_at, daily_screen_time, social_media_hours,
                    gaming_hours, night_phone_usage, sleep_hours,
                    notifications_per_day, app_opens_per_day,
                    risk_class, risk_label, probability
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                *values, risk_class, label, probability
            ))
            conn.commit()

        return jsonify({
            "success": True,
            "risk_class": risk_class,
            "label": label,
            "probability": round(probability * 100, 1),
            "accuracy": round(model_accuracy * 100, 1)
        })
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@app.route("/history")
def history():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM predictions ORDER BY id DESC LIMIT 100"
        ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.route("/stats")
def stats():
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
        high = conn.execute(
            "SELECT COUNT(*) FROM predictions WHERE risk_class = 1"
        ).fetchone()[0]
        avg = conn.execute(
            "SELECT AVG(probability) FROM predictions"
        ).fetchone()[0]
    return jsonify({
        "total": total,
        "high_risk": high,
        "low_or_moderate": total - high,
        "average_probability": round((avg or 0) * 100, 1)
    })


@app.route("/clear-history", methods=["DELETE"])
def clear_history():
    with get_db() as conn:
        conn.execute("DELETE FROM predictions")
        conn.commit()
    return jsonify({"success": True})


if __name__ == "__main__":
    init_db()
    train_model()
    print(f"Model test accuracy: {model_accuracy * 100:.1f}%")
    print("Open http://127.0.0.1:5000 in your browser.")
    app.run(host="127.0.0.1", port=5000, debug=False)
