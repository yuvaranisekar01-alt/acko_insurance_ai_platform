import streamlit as st
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src", "module01_chatbot"))
from rag_chatbot import build_rag_chain, ask  # noqa: E402


CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "chroma_db")


@st.cache_resource
def load_chain():
    return build_rag_chain(persist_directory=CHROMA_DIR)


rag_chain = load_chain()

st.title("💬 Acko Insurance Assistant")
st.caption("Ask me anything about your motor or health insurance policy.")

if "messages" not in st.session_state:
    st.session_state.messages = []

# render chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# chat input
user_question = st.chat_input("Type your question here...")

if user_question:
    st.session_state.messages.append({"role": "user", "content": user_question})
    with st.chat_message("user"):
        st.markdown(user_question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            answer = ask(rag_chain, user_question)
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})

