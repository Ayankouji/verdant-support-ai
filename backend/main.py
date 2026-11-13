
import os
import logging
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

import logging
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select

from database import Base, engine, get_db
from models import (
    Customer,
    Conversation,
    Message,
    AIDraft,
)
from schemas import MessageInput, ApproveInput
from auth import router as auth_router, require_agent
from webhook import router as webhook_router
from services.message_service import process_customer_message
from ai_service import generate_reply




logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)




app = FastAPI(
    title="Verdant AI Support API",
    version="1.0.0"
)




origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:8501"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




app.include_router(auth_router)
app.include_router(webhook_router)




@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully")




@app.get("/")
def root():
    return {
        "message": "Verdant AI Support API is running",
        "status": "healthy"
    }




@app.get("/health")
def health():
    return {
        "status": "healthy"
    }




@app.get("/health/ai")
def ai_health():
    try:
        reply = generate_reply(
            "Reply with exactly: Verdant AI is working."
        )

        return {
            "status": "healthy",
            "ai_status": "working",
            "test_reply": reply
        }

    except Exception as exc:
        logger.exception("AI health check failed")

        raise HTTPException(
            status_code=503,
            detail=f"AI service unavailable: {str(exc)[:300]}"
        )




def serialize_message(message):

    draft = message.draft

    return {
        "id": message.id,
        "sender": message.sender,
        "text": message.text,
        "created_at": (
            message.created_at.isoformat()
            if message.created_at else None
        ),
        "draft": (
            {
                "id": draft.id,
                "draft_text": draft.draft_text,
                "status": draft.status,
                "error": draft.error
            }
            if draft else None
        )
    }


@app.post("/messages")
def send_customer_message(
    data: MessageInput,
    db: Session = Depends(get_db)
):

    try:
        message, draft, conversation = process_customer_message(
            db,
            data.customer.external_id,
            data.customer.name,
            data.customer.phone,
            data.text
        )

        logger.info(
            "Customer message processed. Conversation ID: %s",
            conversation.id
        )

        return {
            "conversation_id": conversation.id,
            "message": serialize_message(message)
        }

    except Exception:
        db.rollback()
        logger.exception("Customer message processing failed")

        raise HTTPException(
            status_code=500,
            detail="Unable to process customer message"
        )



@app.get("/customers/{external_id}/conversation")
def customer_conversation(
    external_id: str,
    db: Session = Depends(get_db)
):

    customer = db.scalar(
        select(Customer).where(
            Customer.external_id == external_id
        )
    )

    if not customer:
        return {
            "customer": None,
            "conversation": None
        }

    conv = db.scalar(
        select(Conversation)
        .where(
            Conversation.customer_id == customer.id,
            Conversation.status == "open"
        )
        .order_by(Conversation.updated_at.desc())
    )

    if not conv:
        return {
            "customer": {
                "id": customer.external_id,
                "name": customer.name,
                "phone": customer.phone
            },
            "conversation": None
        }

    messages = db.scalars(
        select(Message)
        .where(
            Message.conversation_id == conv.id
        )
        .order_by(Message.created_at)
    ).all()


    visible = [
        {
            "id": m.id,
            "sender": m.sender,
            "text": m.text,
            "created_at": (
                m.created_at.isoformat()
                if m.created_at else None
            )
        }
        for m in messages
        if m.sender in ("customer", "agent")
    ]

    return {
        "customer": {
            "id": customer.external_id,
            "name": customer.name,
            "phone": customer.phone
        },
        "conversation": {
            "id": conv.id,
            "messages": visible
        }
    }




@app.get("/conversations")
def list_conversations(
    db: Session = Depends(get_db),
    agent=Depends(require_agent)
):

    convs = db.scalars(
        select(Conversation)
        .options(
            joinedload(Conversation.customer),
            joinedload(Conversation.messages)
        )
        .order_by(Conversation.updated_at.desc())
    ).unique().all()

    result = []

    for conversation in convs:

        latest = (
            max(
                conversation.messages,
                key=lambda m: m.created_at or datetime.min.replace(
                    tzinfo=timezone.utc
                )
            )
            if conversation.messages else None
        )

        result.append({
            "id": conversation.id,
            "status": conversation.status,
            "updated_at": (
                conversation.updated_at.isoformat()
                if conversation.updated_at else None
            ),
            "customer": {
                "id": conversation.customer.external_id,
                "name": conversation.customer.name,
                "phone": conversation.customer.phone
            },
            "preview": latest.text[:120] if latest else ""
        })

    return result




@app.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    agent=Depends(require_agent)
):

    conv = db.scalar(
        select(Conversation)
        .options(
            joinedload(Conversation.customer),
            joinedload(Conversation.messages).joinedload(
                Message.draft
            )
        )
        .where(
            Conversation.id == conversation_id
        )
    )

    if not conv:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )

    return {
        "id": conv.id,
        "customer": {
            "id": conv.customer.external_id,
            "name": conv.customer.name,
            "phone": conv.customer.phone
        },
        "messages": [
            serialize_message(message)
            for message in sorted(
                conv.messages,
                key=lambda m: m.created_at or datetime.min.replace(
                    tzinfo=timezone.utc
                )
            )
        ]
    }




@app.post("/drafts/{draft_id}/approve")
def approve_draft(
    draft_id: int,
    data: ApproveInput,
    db: Session = Depends(get_db),
    agent=Depends(require_agent)
):

    draft = db.scalar(
        select(AIDraft)
        .options(
            joinedload(AIDraft.message)
        )
        .where(
            AIDraft.id == draft_id
        )
    )

    if not draft:
        raise HTTPException(
            status_code=404,
            detail="Draft not found"
        )

    if draft.status != "pending":
        raise HTTPException(
            status_code=409,
            detail="Draft is not pending approval"
        )

    now = datetime.now(timezone.utc)

    reply = Message(
        conversation_id=draft.message.conversation_id,
        sender="agent",
        text=data.text,
        created_at=now
    )

    draft.status = "used"
    draft.approved_at = now

    draft.message.conversation.updated_at = now

    db.add(reply)

    try:
        db.commit()
        db.refresh(reply)

    except Exception:
        db.rollback()
        logger.exception("Draft approval failed")

        raise HTTPException(
            status_code=500,
            detail="Unable to approve draft"
        )

    return {
        "status": "approved",
        "reply_id": reply.id
    }




@app.post("/drafts/{draft_id}/retry")
def retry_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    agent=Depends(require_agent)
):

    draft = db.scalar(
        select(AIDraft)
        .options(
            joinedload(AIDraft.message)
        )
        .where(
            AIDraft.id == draft_id
        )
    )

    if not draft:
        raise HTTPException(
            status_code=404,
            detail="Draft not found"
        )

    if draft.status != "failed":
        raise HTTPException(
            status_code=409,
            detail="Only failed drafts can be retried"
        )

    try:

        logger.info(
            "Retrying AI draft ID: %s",
            draft.id
        )

        draft_text = generate_reply(
            draft.message.text
        )

        draft.draft_text = draft_text
        draft.status = "pending"
        draft.error = None

        db.commit()

        logger.info(
            "AI draft retry successful. Draft ID: %s",
            draft.id
        )

    except Exception as exc:

        db.rollback()

        logger.exception(
            "AI draft retry failed. Draft ID: %s",
            draft.id
        )

        raise HTTPException(
            status_code=503,
            detail="AI generation failed; message retained for retry"
        )

    return {
        "status": "pending",
        "draft_id": draft.id
    }
