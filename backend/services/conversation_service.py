
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import select

from models import (
    Customer,
    Conversation,
    Message,
    AIDraft,
    WebhookEvent,
)


def get_or_create_customer(
    db: Session,
    external_id: str,
    name: str,
    phone: str
) -> Customer:

    customer = db.scalar(
        select(Customer).where(
            Customer.external_id == external_id
        )
    )

    if customer:
        customer.name = name
        customer.phone = phone
        return customer

    customer = Customer(
        external_id=external_id,
        name=name,
        phone=phone
    )

    db.add(customer)
    db.flush()

    return customer


def get_or_create_open_conversation(
    db: Session,
    customer: Customer,
    brand_id: str = "verdant-co"
) -> Conversation:

    conversation = db.scalar(
        select(Conversation)
        .where(
            Conversation.customer_id == customer.id,
            Conversation.brand_id == brand_id,
            Conversation.status == "open"
        )
        .order_by(Conversation.updated_at.desc())
    )

    if conversation:
        return conversation

    now = datetime.now(timezone.utc)

    conversation = Conversation(
        customer_id=customer.id,
        brand_id=brand_id,
        status="open",
        updated_at=now
    )

    db.add(conversation)
    db.flush()

    return conversation


def add_customer_message(
    db: Session,
    conversation: Conversation,
    text: str,
    external_id: str | None = None
) -> Message:

    now = datetime.now(timezone.utc)

    message = Message(
        conversation_id=conversation.id,
        sender="customer",
        text=text,
        external_id=external_id,
        created_at=now
    )

    db.add(message)

  
    conversation.updated_at = now

    db.flush()

    return message


def create_draft(
    db: Session,
    message: Message,
    draft_text: str = "",
    status: str = "pending",
    error: str | None = None
) -> AIDraft:

    draft = AIDraft(
        message_id=message.id,
        draft_text=draft_text,
        status=status,
        error=error
    )

    db.add(draft)
    db.flush()

    return draft
