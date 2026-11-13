
import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

KNOWLEDGE_BASE = """
Verdant & Co policies (the only source of truth):

- Shipping: Orders ship within 24 hours, Monday to Saturday.
  Delivery takes 3-5 business days in metro cities and
  5-8 business days elsewhere in India.

- Address change: Only before the order has shipped,
  and only if the customer contacts us within 12 hours
  of placing it. After shipping, the address cannot
  be changed.

- Cancellation: An order can be cancelled before it ships.
  After shipping, the customer may refuse delivery,
  and a refund is issued once the parcel returns.

- Returns: Within 7 days of delivery for unopened,
  unused products. Opened products are accepted only
  if damaged or the wrong item was sent.

- Refunds: Approved refunds go to the original payment
  method within 5-7 business days after receiving
  the returned parcel.

- Cash on delivery: Available for orders under Rs. 3,000,
  with a Rs. 50 fee.

- Ingredients: All Verdant & Co products are
  fragrance-free and vegan.

- International delivery and medical/allergy procedures
  are not specified.
"""


def generate_reply(customer_message: str) -> str:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    model = os.getenv("GROQ_MODEL", "").strip()

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing from backend/.env"
        )

    if not model:
        raise RuntimeError(
            "GROQ_MODEL is missing from backend/.env"
        )

    client = Groq(api_key=api_key)

    completion = client.chat.completions.create(
        model=model,
        temperature=0.2,
        max_tokens=300,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an AI customer support assistant "
                    "drafting replies for Verdant & Co.\n\n"
                    "Use ONLY the following knowledge base:\n"
                    + KNOWLEDGE_BASE
                    + "\n\nRules:\n"
                    "1. Be polite, professional, and concise.\n"
                    "2. Never invent order status or tracking.\n"
                    "3. Never invent policies or refund eligibility.\n"
                    "4. If information is unavailable, explain "
                    "that a human support agent must confirm.\n"
                    "5. For allergy or medical concerns, avoid "
                    "medical advice and escalate to a human agent.\n"
                    "6. Do not claim a message has been sent.\n"
                    "7. This is a draft for human approval."
                )
            },
            {
                "role": "user",
                "content": customer_message
            }
        ]
    )

    response = completion.choices[0].message.content

    if not response or not response.strip():
        raise RuntimeError(
            "Groq returned an empty AI response."
        )

    return response.strip()
