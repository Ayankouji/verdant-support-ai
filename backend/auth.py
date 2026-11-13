from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import select
from database import get_db
from models import Agent
from schemas import LoginInput
from security import verify_password, create_access_token, decode_access_token

router = APIRouter(prefix="/auth", tags=["authentication"])
bearer = HTTPBearer(auto_error=False)

@router.post("/login")
def login(data: LoginInput, db: Session = Depends(get_db)):
    agent = db.scalar(select(Agent).where(Agent.email == data.email.lower()))
    if not agent or not agent.is_active or not verify_password(data.password, agent.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"access_token": create_access_token(agent.email), "token_type": "bearer", "email": agent.email}

def require_agent(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Agent authentication required")
    try:
        email = decode_access_token(credentials.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    agent = db.scalar(select(Agent).where(Agent.email == email, Agent.is_active.is_(True)))
    if not agent:
        raise HTTPException(status_code=401, detail="Agent account not found or inactive")
    return agent
