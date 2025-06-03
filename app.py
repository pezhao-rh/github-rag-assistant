from rag import store_document, answer_query_with_rag
import streamlit as st

st.title("Rag Bot")

with st.sidebar:
    st.header("Settings")
    filepath = st.text_input("Enter file path:")

    if st.button("Process"):
        if filepath:
            with st.spinner("Processing..."):
                try:
                    store_document(filepath)
                    st.success("Document Added")
                except Exception as e:
                    st.error("Error storing text: {e}")


if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input():

    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        answer = answer_query_with_rag(prompt)
        response = st.write(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
    