from agent import create_github_agent, answer_query_no_rag
from github import clone_and_build_tree, delete_repository
import streamlit as st

st.set_page_config(
    page_title="Github Assistant",
    initial_sidebar_state="auto",
)

st.title("Github RAG Assistant")

# initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "diagram" not in st.session_state:
    st.session_state.diagram = None

if "ingested" not in st.session_state:
    st.session_state.ingested = False

if "user_rag_system" not in st.session_state:
    st.session_state.user_rag_system = None


# sidebar
with st.sidebar:
    st.header("Settings")
    link = st.text_input("Enter Github Repository URL:")

    # save button
    if st.button("Save") and link:
        if not st.session_state.ingested:
            with st.spinner("Processing..."):
                try:
                    st.session_state.user_rag_system = create_github_agent()
                    
                    repo_path, file_list, diagram = clone_and_build_tree(link)
                    st.session_state.user_rag_system.store_documents(file_list)
                    st.session_state.diagram = diagram
                    delete_repository(repo_path)
                    st.success("Successfully Processed Repository")
                    st.session_state.ingested = True

                except Exception as e:
                    st.error(f"Error processing repository: {e}")
                    st.session_state.user_rag_system = None
        else:
            st.warning("Already processed repository")

    # display repository diagram
    if st.session_state.ingested and st.session_state.diagram:
        st.header("Saved Repository")
        st.markdown(f"{st.session_state.diagram}")

    # reset button
    if st.session_state.ingested:
        st.markdown("---")
        if st.button("Reset"):
            with st.spinner("Clearing..."):
                try:
                    if st.session_state.user_rag_system:
                        st.session_state.user_rag_system.reset_vector_db()
                    
                    # Clear all session state
                    st.session_state.messages = []
                    st.session_state.diagram = None
                    st.session_state.ingested = False
                    st.session_state.user_rag_system = None
                    
                    st.success("Successfully cleared repository and conversation history")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error clearing data: {e}")

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

        if st.session_state.ingested and st.session_state.user_rag_system:
            answer, retrieved_sources = st.session_state.user_rag_system.answer_query(prompt)
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
    