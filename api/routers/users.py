from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import List
from uuid import uuid4

router = APIRouter()
_USERS = {}

class UserCreate(BaseModel):
    email: EmailStr
    tz: str = "UTC"

class Preferences(BaseModel):
    topics: List[str] = Field(default_factory=list)
    length: str = Field(default="standard", pattern="^(short|standard|deep)$")
    send_time: str = "07:30"
    frequency: str = Field(default="weekdays", pattern="^(weekdays|daily|custom)$")

@router.post("", summary="Create user")
def create_user(payload: UserCreate):
    user_id = str(uuid4())
    _USERS[user_id] = {"email": payload.email, "tz": payload.tz, "preferences": None}
    return {"id": user_id, "email": payload.email, "tz": payload.tz}

@router.put("/{user_id}/preferences", summary="Update preferences")
def update_preferences(user_id: str, prefs: Preferences):
    user = _USERS.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user["preferences"] = prefs.dict()
    return {"id": user_id, "preferences": user["preferences"]}
