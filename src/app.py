from rag_llamastack import store_documents, answer_query_with_rag, answer_query_no_rag
from github import clone_and_build_tree, delete_repository
import streamlit as st

st.title("Github RAG Assistant")

if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "diagram" not in st.session_state:
    st.session_state.diagram = None

if "ingested" not in st.session_state:
    st.session_state.ingested = False


# sidebar
with st.sidebar:
    st.header("Settings")
    link = st.text_input("Enter Github Repository URL:")

    if st.button("Ingest") and link:
        if not st.session_state.ingested:
            with st.spinner("Processing..."):
                try:
                    repo_path, file_list, diagram = clone_and_build_tree(link)
                    store_documents(file_list)
                    st.session_state.diagram = diagram
                    delete_repository(repo_path)
                    st.success("Successfully Processed Repository")
                    st.session_state.ingested = True
                except Exception as e:
                    st.error(f"Error processing repository: {e}")
        else:
            st.warning("Aleady processed repository")

    if st.session_state.ingested == True and st.session_state.diagram:
        st.header("Saved Repository")
        st.markdown(f"{st.session_state.diagram}")

# main page

# display message history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # show sources
        if message["role"] == "assistant" and "sources" in message and message["sources"] and len(message["sources"]) > 0:
            with st.expander("View Sources"):
                for idx, source in enumerate(message["sources"]):
                    st.markdown(f"`{source['file']}`")
                    st.code(source["text"])
                    st.markdown("---")
# user input
if prompt := st.chat_input():

    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        
        answer = None
        retrieved_sources = None

        if st.session_state.ingested:
            answer, retrieved_sources = answer_query_with_rag(prompt)
        else:
            answer = answer_query_no_rag()

        st.write(answer)

        # show sources
        if retrieved_sources and len(retrieved_sources) > 0:
            with st.expander("View Sources"):
                for idx, source in enumerate(retrieved_sources):
                    st.markdown(f"`{source['file']}`")
                    st.code(source["text"])
                    st.markdown("---")

    st.session_state.messages.append({"role": "assistant", "content": answer, "sources": retrieved_sources})
    