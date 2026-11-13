import json
from fastapi import APIRouter, Request, Header, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from database import get_db
from models import WebhookEvent
from security import verify_webhook_signature
from services.message_service import process_customer_message

router = APIRouter(tags=["webhook"])

@router.post("/webhook")
async def receive_webhook(request: Request, x_signature: str | None = Header(default=None), db: Session = Depends(get_db)):
    raw = await request.body()
    if not verify_webhook_signature(raw, x_signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    try:
        payload = json.loads(raw)
        if payload.get("type") != "message.received":
            raise HTTPException(status_code=400, detail="Unsupported event type")
        event_id = payload["event_id"]
        customer = payload["customer"]
        message = payload["message"]
        if message.get("type") != "text":
            raise HTTPException(status_code=400, detail="Only text messages are supported")
        if db.scalar(select(WebhookEvent).where(WebhookEvent.event_id == event_id)):
            return {"status": "duplicate_ignored", "event_id": event_id}
        db.add(WebhookEvent(event_id=event_id))
        db.flush()
        process_customer_message(
            db,
            external_id=customer["id"],
            name=customer["name"],
            phone=customer["phone"],
            text=message["text"],
            brand_id=payload.get("brand_id", "verdant-co"),
            event_message_id=message["id"]
        )
        return {"status": "processed", "event_id": event_id}
    except HTTPException:
        db.rollback()
        raise
    except (KeyError, TypeError, ValueError) as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=f"Invalid webhook payload: {exc}")
