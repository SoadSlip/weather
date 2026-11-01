import os
import time
import requests
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
CORS(app)

DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "weatherdb")
DB_USER = os.getenv("DB_USER", "weather")
DB_PASSWORD = os.getenv("DB_PASSWORD", "weatherpass")
DB_PORT = os.getenv("DB_PORT", "5432")


def get_db_connection(retries=10, delay=2):
    """Подключение к БД с ретраями (важно при старте контейнеров)."""
    last_err = None
    for attempt in range(retries):
        try:
            conn = psycopg2.connect(
                host=DB_HOST, dbname=DB_NAME, user=DB_USER,
                password=DB_PASSWORD, port=DB_PORT,
            )
            return conn
        except psycopg2.OperationalError as e:
            last_err = e
            time.sleep(delay)
    raise last_err


def init_db():
    """Создаём таблицу истории запросов."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id SERIAL PRIMARY KEY,
                city VARCHAR(255) NOT NULL,
                temperature NUMERIC,
                description VARCHAR(255),
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
    conn.commit()
    conn.close()


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()})


@app.route("/api/weather", methods=["GET"])
def get_weather():
    city = request.args.get("city", "").strip()
    if not city:
        return jsonify({"error": "Параметр 'city' обязателен"}), 400

    try:
        resp = requests.get(
            f"https://wttr.in/{city}?format=j1&lang=ru",
            timeout=20,
            headers={"User-Agent": "weather-app-devops-petproject/1.0"},
        )
        resp.raise_for_status()
        data = resp.json()

        current = data["current_condition"][0]
        area = (data.get("nearest_area") or [{}])[0]

        result = {
            "city": city.title(),
            "country": (area.get("country") or [{}])[0].get("value", ""),
            "temperature": float(current["temp_C"]),
            "humidity": int(current["humidity"]),
            "wind_speed": float(current["windspeedKmph"]),
            "weather_code": 0,
            "description": current["weatherDesc"][0]["value"],
        }

        # Сохраняем в БД
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO search_history (city, temperature, description) VALUES (%s, %s, %s)",
                    (result["city"], result["temperature"], result["description"]),
                )
            conn.commit()
            conn.close()
        except Exception as e:
            app.logger.warning(f"Не удалось сохранить историю: {e}")

        return jsonify(result)

    except requests.RequestException as e:
        return jsonify({"error": f"Ошибка внешнего API: {str(e)}"}), 502

@app.route("/api/history", methods=["GET"])
def history():
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, city, temperature, description, created_at "
                "FROM search_history ORDER BY created_at DESC LIMIT 20"
            )
            rows = cur.fetchall()
        conn.close()
        for r in rows:
            r["created_at"] = r["created_at"].isoformat()
            r["temperature"] = float(r["temperature"]) if r["temperature"] is not None else None
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def weather_code_to_text(code):
    mapping = {
        0: "Ясно", 1: "Преимущественно ясно", 2: "Переменная облачность", 3: "Пасмурно",
        45: "Туман", 48: "Изморозь",
        51: "Морось слабая", 53: "Морось", 55: "Морось сильная",
        61: "Дождь слабый", 63: "Дождь", 65: "Дождь сильный",
        71: "Снег слабый", 73: "Снег", 75: "Снег сильный",
        80: "Ливень", 81: "Ливень сильный", 82: "Ливень очень сильный",
        95: "Гроза", 96: "Гроза с градом", 99: "Сильная гроза с градом",
    }
    return mapping.get(code, "Неизвестно")


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
