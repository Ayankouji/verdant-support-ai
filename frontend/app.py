import streamlit as st
from api_client import login, send_message, get_customer_conversation, get_conversations, get_conversation, approve, retry

st.set_page_config(page_title="Verdant & Co Support", page_icon="🌿", layout="wide")
st.title("🌿 Verdant & Co | AI Support")

view = st.sidebar.radio("Workspace", ["Customer", "Agent"])
st.sidebar.caption("AI drafts are visible only to signed-in agents.")

if view == "Customer":
    st.header("Customer view")
    st.caption("Test customer messaging. No customer login is required.")
    customers = {
        "Aisha Khan": {"external_id": "cust_1042", "name": "Aisha Khan", "phone": "+919800000001"},
        "Rahul Sharma": {"external_id": "cust_1043", "name": "Rahul Sharma", "phone": "+919800000002"},
        "Priya Patel": {"external_id": "cust_1044", "name": "Priya Patel", "phone": "+919800000003"}
    }
    choice = st.selectbox("Choose a test customer", list(customers))
    customer = customers[choice]
    conversation_data = get_customer_conversation(customer["external_id"])
    if conversation_data and conversation_data.get("conversation"):
        for msg in conversation_data["conversation"]["messages"]:
            with st.chat_message("user" if msg["sender"] == "customer" else "assistant"):
                st.write(msg["text"])
    else:
        st.info("No messages yet. Start a conversation below.")
    with st.form("customer_message", clear_on_submit=True):
        text = st.text_area("Your message", placeholder="Where is my order?")
        submitted = st.form_submit_button("Send message")
    if submitted:
        if text.strip():
            result = send_message(customer, text.strip())
            if result:
                st.success("Message received. Your support team will review the reply.")
                st.rerun()
        else:
            st.warning("Enter a message first.")

else:
    st.header("Agent dashboard")
    if "agent_token" not in st.session_state:
        with st.form("agent_login"):
            email = st.text_input("Agent email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in")
        if submitted:
            result = login(email, password)
            if result:
                st.session_state.agent_token = result["access_token"]
                st.rerun()
        st.info("Sign in with the test agent credentials configured by the developer.")
    else:
        token = st.session_state.agent_token
        if st.sidebar.button("Sign out"):
            del st.session_state["agent_token"]
            st.rerun()
        conversations = get_conversations(token)
        if conversations is not None:
            if not conversations:
                st.info("No conversations yet. Send a test message in Customer view.")
            else:
                labels = {f'{c["customer"]["name"]} — {c["preview"][:65]}': c["id"] for c in conversations}
                selected = st.selectbox("Conversations (newest activity first)", list(labels))
                data = get_conversation(token, labels[selected])
                if data:
                    st.subheader(data["customer"]["name"])
                    for msg in data["messages"]:
                        with st.chat_message("user" if msg["sender"] == "customer" else "assistant"):
                            st.write(msg["text"])
                        draft = msg.get("draft")
                        if draft:
                            if draft["status"] == "pending":
                                st.markdown("**AI suggested reply – review before approving**")
                                edited = st.text_area("Edit reply", value=draft["draft_text"], key=f'draft_{draft["id"]}')
                                if st.button("Approve reply", key=f'approve_{draft["id"]}'):
                                    result = approve(token, draft["id"], edited)
                                    if result:
                                        st.success("Reply approved and saved.")
                                        st.rerun()
                            elif draft["status"] == "failed":
                                st.warning(f'AI generation failed: {draft.get("error") or "Unknown error"}')
                                if st.button("Retry AI draft", key=f'retry_{draft["id"]}'):
                                    result = retry(token, draft["id"])
                                    if result:
                                        st.success("Draft regenerated.")
                                        st.rerun()
