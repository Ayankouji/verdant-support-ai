# Architecture

Streamlit is the browser UI and calls FastAPI over HTTP. FastAPI is the only component that accesses the database and Groq.

Customer message flow:
1. Streamlit Customer View calls `POST /messages`, or an external chat provider calls `POST /webhook`.
2. Webhook requests are authenticated with HMAC-SHA256 over the raw request body.
3. The backend identifies/creates the customer and their open conversation, then persists the customer message.
4. Groq drafts a reply from the fixed Verdant & Co policy knowledge base.
5. The draft is stored as pending, or failed with an error if the provider is unavailable.
6. An authenticated agent reviews and approves the text. Approval creates a separate agent message.
7. Customer conversation API returns customer and approved agent messages only; AI drafts are excluded.

The sample is single-brand in its current authorization and UI implementation. A production multi-brand version must scope all queries and agent permissions by brand.
