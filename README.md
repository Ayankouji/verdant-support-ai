# Verdant & Co – AI Customer Support

A take-home assessment implementation: customers send messages, Groq drafts a policy-grounded reply, and a signed-in human agent edits and approves it. Drafts are never shown to customers or sent automatically.

## Stack
- Python, FastAPI, Streamlit
- PostgreSQL (SQLite is used by default for local quick-start)
- SQLAlchemy
- Groq API
- HMAC-SHA256 webhook verification
- JWT-based agent authentication

## Project layout
- `backend/`: API, database models, webhook, AI service and agent authentication
- `frontend/`: Streamlit customer and agent interface
- `docs/`: architecture notes

## Local setup

### 1. Backend
```powershell
cd backend
python -m venv venv
.env\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```
Edit `.env`. Set `GROQ_API_KEY`, `GROQ_MODEL`, and a strong `JWT_SECRET`. For the first local run, `DATABASE_URL=sqlite:///./verdant.db` works without a hosted database.

Create a test agent by adding these values to `backend/.env`:
```env
AGENT_EMAIL=agent@example.com
AGENT_PASSWORD=ChangeThisPassword123!
```
Then run:
```powershell
python seed_agent.py
uvicorn main:app --reload
```
API docs: http://127.0.0.1:8000/docs

### 2. Frontend
Open a second terminal:
```powershell
cd frontend
python -m venv venv
.env\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
streamlit run app.py
```
Open http://localhost:8501. Switch between Customer and Agent in the sidebar.

## Webhook test

The assessment test secret is `verdant-demo-secret-2026`. Generate the signature over the exact raw JSON bytes; do not parse and re-serialize the body before signing.

Example Python signing helper:
```python
import hmac, hashlib, json, requests
payload = {
  "event_id": "evt_local_001",
  "type": "message.received",
  "brand_id": "verdant-co",
  "timestamp": "2026-11-03T10:15:22Z",
  "customer": {"id": "cust_1042", "name": "Aisha Khan", "phone": "+919800000001"},
  "message": {"id": "msg_local_001", "type": "text", "text": "What is your return policy?"}
}
body = json.dumps(payload, separators=(",", ":")).encode()
sig = hmac.new(b"verdant-demo-secret-2026", body, hashlib.sha256).hexdigest()
r = requests.post("http://127.0.0.1:8000/webhook", data=body,
                  headers={"Content-Type":"application/json", "X-Signature":"sha256="+sig})
print(r.status_code, r.text)
```

## Deployment outline
1. Create a Supabase PostgreSQL project and set `DATABASE_URL` on Render.
2. Deploy `backend/` as a Render Web Service. Build command: `pip install -r requirements.txt`; start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`.
3. Set backend environment variables on Render: `DATABASE_URL`, `GROQ_API_KEY`, `GROQ_MODEL`, `WEBHOOK_SECRET`, `JWT_SECRET`, `ACCESS_TOKEN_MINUTES`, `CORS_ORIGINS`, `AGENT_EMAIL`, `AGENT_PASSWORD`.
4. Run `python seed_agent.py` once against the deployed database (use Render Shell or a one-off job).
5. Deploy the Streamlit app from the `frontend/` directory using Streamlit Community Cloud. Set `API_BASE_URL` in its secrets/settings to the Render URL.
6. Test the deployed webhook and complete customer-to-agent approval flow.

## Important notes and limitations
- Configure a Groq model that is currently enabled for your account; model availability changes.
- The local default database is SQLite for easy setup. Use PostgreSQL in deployment.
- This is a compact assessment starter, not a hardened multi-tenant production service. Before real production use, add database migrations, rate limiting, structured logs/monitoring, robust retry/background jobs, CSRF/session hardening, agent account provisioning controls, and tenant isolation.
- The webhook persists inbound messages before AI generation; failed AI drafts remain visible to agents for retry.
- No real WhatsApp integration or outbound message sending is implemented, as the assessment does not require it.

## Assessment README answers (adapt after implementation)
1. If processing fails overnight, the inbound message is persisted before AI generation. The draft is marked failed with an error so the agent can see the conversation and retry; production monitoring and alerting should notify the team.
2. For 20 brands, add a brands table and enforce `brand_id` scoping across customers, conversations, agents and knowledge bases, ideally with database-level row security and tenant-aware authorization. This starter includes a `brand_id` on conversations but does not yet implement full tenant isolation.
