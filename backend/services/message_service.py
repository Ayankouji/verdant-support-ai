from sqlalchemy.orm import Session
from ai_service import generate_reply
from services.conversation_service import get_or_create_customer, get_or_create_open_conversation, add_customer_message, create_draft

def process_customer_message(db: Session, external_id: str, name: str, phone: str, text: str, brand_id: str = "verdant-co", event_message_id: str | None = None):
    customer = get_or_create_customer(db, external_id, name, phone)
    conversation = get_or_create_open_conversation(db, customer, brand_id)
    message = add_customer_message(db, conversation, text, event_message_id)
    try:
        draft = create_draft(db, message, generate_reply(text), "pending")
    except Exception as exc:
        
        draft = create_draft(db, message, "", "failed", str(exc)[:1000])
    db.commit()
    db.refresh(message)
    db.refresh(conversation)
    return message, draft, conversation
