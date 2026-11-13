import os, hmac, hashlib
from datetime import datetime, timedelta, timezone
import jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-change-this-secret")
JWT_ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)

def create_access_token(subject: str) -> str:
    expiry = datetime.now(timezone.utc) + timedelta(minutes=int(os.getenv("ACCESS_TOKEN_MINUTES", "480")))
    return jwt.encode({"sub": subject, "exp": expiry}, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_access_token(token: str) -> str:
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    subject = payload.get("sub")
    if not subject:
        raise ValueError("Invalid token subject")
    return subject

def verify_webhook_signature(raw_body: bytes, supplied_header: str | None) -> bool:
    secret = os.getenv("WEBHOOK_SECRET", "verdant-demo-secret-2026").encode()
    if not supplied_header or not supplied_header.startswith("sha256="):
        return False
    supplied = supplied_header.removeprefix("sha256=").strip()
    expected = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, supplied)
