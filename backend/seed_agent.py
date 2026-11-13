import os, sys
from dotenv import load_dotenv
from sqlalchemy import select
from database import Base, engine, SessionLocal
from models import Agent
from security import hash_password

load_dotenv()
email = os.getenv("AGENT_EMAIL")
password = os.getenv("AGENT_PASSWORD")
if not email or not password:
    sys.exit("Set AGENT_EMAIL and AGENT_PASSWORD in backend/.env before running.")
Base.metadata.create_all(bind=engine)
db = SessionLocal()
try:
    agent = db.scalar(select(Agent).where(Agent.email == email.lower()))
    if agent:
        print("Agent already exists:", email)
    else:
        db.add(Agent(email=email.lower(), password_hash=hash_password(password)))
        db.commit()
        print("Created agent:", email)
finally:
    db.close()
