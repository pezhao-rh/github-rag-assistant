# RAG implementation using LlamaStack's Agent and RAG tool.

from llama_stack_client import LlamaStackClient
from llama_stack_client import Agent, AgentEventLogger
from llama_stack_client.types import Document
import uuid
import mimetypes
import os
from rich.pretty import pprint
import re
import ast

client = LlamaStackClient(base_url="http://localhost:8321")
doc_count = 0

embed_lm = next(m for m in client.models.list() if m.model_type == "embedding")
embedding_model = embed_lm.identifier

vector_db_id = f"v{uuid.uuid4().hex}"
client.vector_dbs.register(
    vector_db_id=vector_db_id,
    embedding_model=embedding_model,
    embedding_dimension=embed_lm.metadata["embedding_dimension"],
    provider_id="faiss",
)

model = "llama3.1:8b-instruct-fp16"
llm = next(m for m in client.models.list() if m.model_type == "llm" and m.identifier == model)

rag_agent = Agent(
    client,
    model=model,
    instructions=(
        "You are a highly knowledgeable AI assistant specializing in understanding and explaining codebases and technical documentation from GitHub repositories. "
        "Your primary function is to answer questions, provide summaries, explain complex functions, and help navigate the codebase. "
        "Leverage the RAG tool to retrieve relevant information. "
        "Always prioritize factual information found through the RAG tool. "
        "Provide clear, concise, and accurate explanations. When explaining code, try to break down complex logic into understandable parts. "
        "If the RAG tool cannot provide the necessary information, state that you do not have sufficient context from the repository to answer the question."
    ),
    tools=[
        {
            "name": "builtin::rag/knowledge_search",
            "args": {"vector_db_ids": [vector_db_id]},
            # Defaults
            "query_config": {
                "chunk_size_in_tokens": 512,
                "chunk_overlap_in_tokens": 50,
                "chunk_template": "Result {index}\nContent: {chunk.content}\nMetadata: {metadata}\n",
            },

        }
    ],
)

session_id = rag_agent.create_session(session_name=f"s{uuid.uuid4().hex}")

def load_document(filepath):
    # extract file contents
    print(f"Reading {filepath}")
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            return content
    except Exception as e:
        print(f"Error opening {filepath}, will not store: {e}")
        return None
    
def store_documents(files):
    for file in files:
        store_document(file)


def store_document(filepath):
    global doc_count, vector_db_id, client
    mime_type, _ = mimetypes.guess_type(filepath)
    document = Document(
        document_id=f"num-{doc_count}",
        content=load_document(filepath),
        mime_type=mime_type,
        metadata={"file": filepath}
    )
    doc_count += 1

    client.tool_runtime.rag_tool.insert(
    documents=[document],
    vector_db_id=vector_db_id,
    chunk_size_in_tokens=512,
)
    
def get_content_and_filename(item):
    # getting content and file name from a TextContentItem object
    match = re.search(
        r"Content:\s*(.*?)\nMetadata:\s*(\{.*?\})\n",
        item.text,
        re.DOTALL
    )
    if match:
        content = match.group(1).strip()
        metadata_str = match.group(2).strip()
        try:
            metadata = ast.literal_eval(metadata_str)
            if isinstance(metadata, dict):
                file_name = metadata.get('file')
                return content, os.path.basename(file_name)
        except (ValueError, SyntaxError) as e:
            print(f"Warning: Could not parse metadata string: {metadata_str}. Error: {e}")
        
    return None, None

def answer_query_with_rag(query):
    global rag_agent, session_id

    # ask agent
    response = rag_agent.create_turn(
        messages=[{"role": "user", "content": query}],
        session_id=session_id,
        stream=False
    )

    # retrieve sources
    sources = []
    tool_step = next(step for step in response.steps if step.step_type == "tool_execution")
    for responses in tool_step.tool_responses:
        for item in responses.content:
            text, file_name = get_content_and_filename(item)
            if file_name:
                sources.append({"file": file_name, "text": text})

    return response.output_message.content, sources

def answer_query_no_rag():
    prompt = """
    "You are a helpful AI assistant. To answer questions about a GitHub repository, I need you to first provide a repository URL in the 'Settings' section of the sidebar and click 'Ingest'. Once the repository is processed, I'll be able to answer your questions."
    """

    response = rag_agent.create_turn(
        messages=[{"role": "user", "content": prompt}],
        session_id=session_id,
        stream=False
    )
    return response.output_message.content 

def single_document_rag_test():
    store_document("pokemon.txt")
    query = "What is Piplup? Describe this Pokemon."
    answer = answer_query_with_rag(query)
    # print(answer)


def main():
    single_document_rag_test()

if __name__ == "__main__":
    main()
