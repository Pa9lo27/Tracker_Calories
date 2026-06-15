
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# База даних в оперативній пам'яті (словник)
states_db = {}

class UserState(BaseModel):
    user_id: int
    state: str = "start"

@app.get("/")
def read_root():
    return {"message": "User State Service is running"}

@app.post("/state")
def set_state(user_state: UserState):
    states_db[user_state.user_id] = user_state.state
    return {"status": "success", "user_id": user_state.user_id, "state": user_state.state}

@app.get("/state/{user_id}")
def get_state(user_id: int):
    # Якщо юзера немає в базі, вважаємо, що його стан "start"
    current_state = states_db.get(user_id, "start")
    return {"user_id": user_id, "state": current_state}