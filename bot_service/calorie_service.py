from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime, timedelta
import sqlite3

app = FastAPI()

# Підключення до БД (створиться автоматично)
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
    cursor.execute("INSERT INTO meals (user_id, calories, proteins, fats, carbs, timestamp) VALUES (?,?,?,?,?,?)",
                   (meal.user_id, meal.calories, meal.proteins, meal.fats, meal.carbs, datetime.now()))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.get("/analytics/today/{user_id}")
def get_today(user_id: int):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(calories), SUM(proteins), SUM(fats), SUM(carbs) FROM meals WHERE user_id=? AND timestamp LIKE ?",
                   (user_id, f"{today}%"))
    row = cursor.fetchone()
    conn.close()
    return {"calories": row[0] or 0, "proteins": row[1] or 0, "fats": row[2] or 0, "carbs": row[3] or 0}

@app.get("/analytics/average/{user_id}")
def get_average(user_id: int):
    # Логіка середнього (спрощено)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Беремо за 7 і 30 днів
    conn.close()
    return {"avg_7": 1900, "avg_30": 2000} # Тут ти зможеш додати реальний SQL запит пізніше