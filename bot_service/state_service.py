from fastapi import FastAPI
from pydantic import BaseModel
import redis

app = FastAPI()

r = redis.Redis(host='redis', port=6379, decode_responses=True)

class UserState(BaseModel):
    user_id: int
    state: str = "start"

@app.get("/")
def read_root():
    return {"message": "User State Service is running"}

@app.post("/state")
def set_state(user_state: UserState):
    r.set(f"state:{user_state.user_id}", user_state.state)
    return {"status": "success", "user_id": user_state.user_id, "state": user_state.state}

@app.get("/state/{user_id}")
def get_state(user_id: int):
    state = r.get(f"state:{user_id}")
    return {"user_id": user_id, "state": state if state else "start"}