import streamlit as st
import requests

st.title("Warehouse Operations Assistant")

API_URL = "http://localhost:8000/chat"

if "history" not in st.session_state:
    st.session_state.history = []

for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("lineage"):
            with st.expander("Source"):
                st.json(msg["lineage"])

prompt = st.chat_input("Ask about orders, pickers, shipments, or totes...")
if prompt:
    st.session_state.history.append({"role": "user", "content": prompt})
    response = requests.post(API_URL, json={"message": prompt}, timeout=30)
    data = response.json()
    st.session_state.history.append(
        {"role": "assistant", "content": data.get("answer", ""), "lineage": data.get("lineage")}
    )
    st.rerun()
