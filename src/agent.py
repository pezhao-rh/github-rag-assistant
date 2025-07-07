from llama_stack_client import LlamaStackClient, Agent
from llama_stack_client.types import Document
import uuid
import mimetypes
import os
import re
import ast
from typing import Optional

LLAMA_STACK_ENDPOINT = os.getenv("LLAMA_STACK_ENDPOINT", "http://localhost:8321")

# Global shared resources (not user-specific)
client = LlamaStackClient(base_url=LLAMA_STACK_ENDPOINT)

embed_lm = next(m for m in client.models.list() if m.model_type == "embedding")
embedding_model = embed_lm.identifier

providers = client.providers.list()
vector_io_provider = None
for x in providers:
    if x.api == "vector_io":
        vector_io_provider = x.provider_id

llm = next(m for m in client.models.list() if m.model_type == "llm")


class GithubAgent:
    """A RAG-powered agent specialized for GitHub repository analysis.

    Each instance maintains its own vector database, RAG agent, and session state.
    
    Attributes:
        vector_db_id (str): Unique identifier for this agent's vector database
        doc_id_to_filename (dict): Mapping of document IDs to original filenames
        doc_count (int): Counter for documents stored in the vector database
        rag_agent (Agent): LlamaStack agent instance for query processing
        session_id (str): Unique session identifier for conversation continuity
    """
    
    def __init__(self):
        """Initialize a new RAG system with its own vector database and agent."""
        self.vector_db_id = f"v{uuid.uuid4().hex}"
        self.doc_id_to_filename = {}
        self.doc_count = 0
        
        # Create user-specific vector database
        client.vector_dbs.register(
            vector_db_id=self.vector_db_id,
            embedding_model=embedding_model,
            embedding_dimension=embed_lm.metadata["embedding_dimension"],
            provider_id=vector_io_provider,
        )
        
        # Create user-specific RAG agent and session
        self._create_agent()
    
    def _create_agent(self) -> None:
        """Create a new RAG agent and session using the current vector database."""
        self.rag_agent = Agent(
            client,
            model=llm.identifier,
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
                    "args": {
                        "vector_db_ids": [self.vector_db_id],
                        "chunk_size_in_tokens": 512,
                        "chunk_overlap_in_tokens": 50,
                        "chunk_template": "Result {index}\nContent: {chunk.content}\nMetadata: {metadata}\n",
                    },
                }
            ],
            max_infer_iters=5,
            sampling_params={
                "strategy": {"type": "top_p", "temperature": 0.7, "top_p": 0.95},
                "max_tokens": 2048,
            },
        )
        
        self.session_id = self.rag_agent.create_session(session_name=f"s{uuid.uuid4().hex}")
    
    def reset_vector_db(self) -> None:
        """Reset the vector database and recreate the agent with the new database."""
        try:
            client.vector_dbs.unregister(vector_db_id=self.vector_db_id)
            print(f"Successfully unregistered vector database: {self.vector_db_id}")
        except Exception as e:
            print(f"Warning: Could not unregister vector database {self.vector_db_id}: {e}")
        
        self.vector_db_id = f"v{uuid.uuid4().hex}"
        client.vector_dbs.register(
            vector_db_id=self.vector_db_id,
            embedding_model=embedding_model,
            embedding_dimension=embed_lm.metadata["embedding_dimension"],
            provider_id=vector_io_provider,
        )
        print(f"Created new vector database: {self.vector_db_id}")
        
        self._create_agent()
        self.doc_id_to_filename = {}
        self.doc_count = 0
    
    def store_document(self, filepath: str) -> None:
        """Store a single document in the current vector database, skipping files that cannot be loaded or stored.
        
        Args:
            filepath (str): Path to the file to be stored in the vector database
        """
        mime_type, _ = mimetypes.guess_type(filepath)
        doc_id = f"num-{self.doc_count}"
        
        content = load_document(filepath)
        if content is None:
            return
        
        try:
            document = Document(
                document_id=doc_id,
                content=content,
                mime_type=mime_type,
                metadata={"file": filepath}
            )
            
            self.doc_id_to_filename[doc_id] = filepath
            self.doc_count += 1

            client.tool_runtime.rag_tool.insert(
                documents=[document],
                vector_db_id=self.vector_db_id,
                chunk_size_in_tokens=512,
            )
        except Exception as e:
            print(f"Error storing document {filepath}, will not store: {e}")

    
    def store_documents(self, files: list[str]) -> None:
        """Store multiple documents in the current vector database, skipping files that cannot be loaded or stored.
        
        Args:
            files (list[str]): List of file paths to be stored in the vector database
        """
        for file in files:
            self.store_document(file)
    
    def answer_query(self, query: str) -> tuple[str, list[dict[str, str]]]:
        """Answer a query using the GithubAgent with RAG.
        
        Args:
            query (str): The user's question about the GitHub repository
            
        Returns:
            tuple[str, list[dict[str, str]]]: A tuple containing:
                - str: The agent's response to the query
                - list[dict[str, str]]: List of source documents used, where each dict contains:
                    - 'file': The filename of the source document
                    - 'text': The relevant text excerpt from that file
        """
        try:
            response = self.rag_agent.create_turn(
                messages=[{"role": "user", "content": query}],
                session_id=self.session_id,
                stream=False
            )
        except RuntimeError as e:
            # reset session to reset token context
            self.session_id = self.rag_agent.create_session(session_name=f"s{uuid.uuid4().hex}")
            response = self.rag_agent.create_turn(
                messages=[{"role": "user", "content": query}],
                session_id=self.session_id,
                stream=False
            )

        sources = self._get_sources(response)
        reply = response.output_message.content

        return reply, sources

    def _get_content_and_filename(self, item) -> tuple[Optional[str], Optional[str]]:
        """Extract content and filename from a TextContentItem object.
        
        Handles different LlamaStack configurations:
        - Ollama configuration: Parses metadata from structured text format
        - vLLM configuration: Uses document ID mapping to resolve filenames
        
        Args:
            item: TextContentItem from the RAG tool response
            
        Returns:
            tuple[Optional[str], Optional[str]]: A tuple containing:
                - Optional[str]: The extracted content text, or None if parsing failed
                - Optional[str]: The base filename (without path), or None if not found
        """
        # for Ollama LlamaStack configuration
        match1 = re.search(
            r"Content:\s*(.*?)\nMetadata:\s*(\{.*?\})\n",
            item.text,
            re.DOTALL
        )
        if match1:
            content = match1.group(1).strip()
            metadata_str = match1.group(2).strip()
            try:
                metadata = ast.literal_eval(metadata_str)
                if isinstance(metadata, dict):
                    file_name = metadata.get('file')
                    if file_name:
                        return content, os.path.basename(file_name)
            except (ValueError, SyntaxError) as e:
                print(f"Warning: Could not parse metadata string: {metadata_str}. Error: {e}")
        
        # for vLLM LlamaStack configuration
        match2 = re.search(
            r"Document_id:\s*(.*?)\nContent:\s*(.*?)\n",
            item.text,
            re.DOTALL
        )
        if match2:
            document_id = match2.group(1).strip()
            content = match2.group(2).strip()
            file_name = self.doc_id_to_filename.get(document_id)
            if file_name:
                return content, os.path.basename(file_name)

        return None, None
    
    def _get_sources(self, chat_response) -> list[dict[str, str]]:
        """Extract sources from a chat response, if any tools were used.
        
        Args:
            chat_response: The response object from the RAG agent containing
                          tool execution steps and retrieved content
                          
        Returns:
            list[dict[str, str]]: List of source documents, where each dict contains:
                - 'file': The source filename
                - 'text': The relevant text excerpt that was retrieved
        """
        sources = []
        for step in chat_response.steps:
            if step.step_type == "tool_execution" and step.tool_responses:
                for responses in step.tool_responses:
                    for item in responses.content:
                        text, file_name = self._get_content_and_filename(item)
                        if file_name:
                            sources.append({"file": file_name, "text": text})
        return sources


def create_github_agent() -> GithubAgent:
    """Create a new GithubAgent instance for a user session, with its own vector database.
    
    Returns:
        GithubAgent: A fully initialized agent ready to ingest repository
                    documents and answer questions
    """
    return GithubAgent()


def answer_query_no_rag() -> str:
    """Fallback response when no repository is loaded.
    
    Returns:
        str: A brief, helpful message explaining how to get started
             by providing a repository URL in the settings
    """
    prompt = """
    You are a helpful AI assistant. To answer questions about a GitHub repository, I need you to first provide a repository URL in the Settings section. Once the repository is processed, I'll be able to answer your questions. Be brief and concise.
    """

    response = client.inference.chat_completion(
        model_id=llm.identifier,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": ""},
        ],
        stream=False
    )

    return response.completion_message.content

def load_document(filepath: str) -> Optional[str]:
    """Load document content from file.
    
    Args:
        filepath (str): Path to the file to be loaded
        
    Returns:
        Optional[str]: The complete file content as a string, or None if
                      the file could not be read (e.g., permission denied,
                      file not found, encoding issues)
    """
    print(f"Reading {filepath}")
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            return content
    except Exception as e:
        print(f"Error opening {filepath}, will not store: {e}")
        return None