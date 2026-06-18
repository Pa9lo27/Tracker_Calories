from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime, timedelta
import sqlite3

app = FastAPI()

DB_NAME = "calories.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS meals 
                      (id INTEGER PRIMARY KEY, user_id INTEGER, calories INTEGER, 
                       proteins REAL, fats REAL, carbs REAL, timestamp DATETIME)''')
    conn.commit()
    conn.close()

init_db()


class Meal(BaseModel):
    user_id: int
    calories: int
    proteins: float
    fats: float
    carbs: float


@app.post("/log_meal")
def log_meal(meal: Meal):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO meals (user_id, calories, proteins, fats, carbs, timestamp) VALUES (?,?,?,?,?,?)",
        (meal.user_id, meal.calories, meal.proteins, meal.fats, meal.carbs, datetime.now())
    )
    conn.commit()
    conn.close()
    return {"status": "success"}


@app.get("/analytics/today/{user_id}")
def get_today(user_id: int):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT SUM(calories), SUM(proteins), SUM(fats), SUM(carbs) FROM meals WHERE user_id=? AND timestamp LIKE ?",
        (user_id, f"{today}%")
    )
    row = cursor.fetchone()
    conn.close()
    return {
        "calories": row[0] or 0,
        "proteins": round(row[1] or 0, 1),
        "fats": round(row[2] or 0, 1),
        "carbs": round(row[3] or 0, 1)
    }


@app.get("/analytics/days/{user_id}/{days}")
def get_days(user_id: int, days: int):
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT AVG(daily_cal), AVG(daily_prot), AVG(daily_fat), AVG(daily_carb)
        FROM (
            SELECT DATE(timestamp) as day,
                   SUM(calories) as daily_cal,
                   SUM(proteins) as daily_prot,
                   SUM(fats) as daily_fat,
                   SUM(carbs) as daily_carb
            FROM meals
            WHERE user_id=? AND timestamp >= ?
            GROUP BY DATE(timestamp)
        )
    """, (user_id, since))
    row = cursor.fetchone()
    conn.close()
    return {
        "avg_calories": round(row[0] or 0),
        "avg_proteins": round(row[1] or 0, 1),
        "avg_fats": round(row[2] or 0, 1),
        "avg_carbs": round(row[3] or 0, 1)
    }