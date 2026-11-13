import os
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

def request(method, path, token=None, **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.request(method, f"{API_BASE}{path}", headers=headers, timeout=45, **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        detail = getattr(getattr(exc, "response", None), "text", str(exc))
        st.error(f"API request failed: {detail}")
        return None

def login(email, password):
    return request("POST", "/auth/login", json={"email": email, "password": password})

def send_message(customer, text):
    return request("POST", "/messages", json={"customer": customer, "text": text})

def get_customer_conversation(external_id):
    return request("GET", f"/customers/{external_id}/conversation")

def get_conversations(token):
    return request("GET", "/conversations", token=token)

def get_conversation(token, conversation_id):
    return request("GET", f"/conversations/{conversation_id}", token=token)

def approve(token, draft_id, text):
    return request("POST", f"/drafts/{draft_id}/approve", token=token, json={"text": text})

def retry(token, draft_id):
    return request("POST", f"/drafts/{draft_id}/retry", token=token)
