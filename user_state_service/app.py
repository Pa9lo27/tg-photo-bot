from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class UserState(BaseModel):
    user_id: int
    state: str = "start"

@app.get("/")
def read_root():
    return {"message": "User State Service"}

@app.post("/state")
def set_state(user_state: UserState):
    return {"user_id": user_state.user_id, "state": user_state.state}

@app.get("/state/{user_id}")
def get_state(user_id: int):
    return {"user_id": user_id, "state": "active"}
