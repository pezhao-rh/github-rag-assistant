import os
from langchain.text_splitter import Language, RecursiveCharacterTextSplitter
import ollama
import chromadb
import uuid
import shutil

client = chromadb.PersistentClient(path=".chroma")
#client = chromadb.EphemeralClient()
collection = client.get_or_create_collection(name="docs")

file_extension_to_language = {
    "cpp": Language.CPP,
    "c": Language.C,
    "go": Language.GO,
    "java": Language.JAVA,
    "kt": Language.KOTLIN,
    "js": Language.JS,
    "jsx": Language.JS,
    "ts": Language.TS,
    "tsx": Language.TS, 
    "php": Language.PHP,
    "proto": Language.PROTO,
    "py": Language.PYTHON,
    "rst": Language.RST,
    "rb": Language.RUBY,
    "rs": Language.RUST,
    "scala": Language.SCALA,
    "swift": Language.SWIFT,
    "md": Language.MARKDOWN,
    "markdown": Language.MARKDOWN,
    "tex": Language.LATEX,
    "latex": Language.LATEX,
    "html": Language.HTML,
    "htm": Language.HTML,
    "sol": Language.SOL,
    "cs": Language.CSHARP,
    "cob": Language.COBOL,
    "cbl": Language.COBOL,
    "lua": Language.LUA,
    "pl": Language.PERL,
    "pm": Language.PERL,
    "hs": Language.HASKELL,
}

def load_document(filepath):
    # extract file contents
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            print(f"Reading {filepath}")
            return content
    except Exception as e:
        print(f"Error opening {filepath}: {e}")
        return None
    
def chunk_document(filepath, chunk_size=1000, chunk_overlap=100):

    text = load_document(filepath)

    # check language of file
    _, ext = os.path.splitext(filepath)
    ext = ext.lstrip('.')
    language = None
    if ext in file_extension_to_language:
        language = file_extension_to_language[ext]
    
    # initiate text splitter
    text_splitter = None
    if language is None:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size = chunk_size,
            chunk_overlap = chunk_overlap
        )
    else:
        text_splitter = RecursiveCharacterTextSplitter.from_language(
            chunk_size = chunk_size,
            chunk_overlap = chunk_overlap,
            language = language
        )
    
    # extract chunks
    chunks = text_splitter.create_documents([text])

    return chunks

def get_embedding(chunk):
    # embedding using ollama minilm
    response = ollama.embed(model="all-minilm", input=chunk)
    embedding = response["embeddings"]
    return embedding[0]

def store_document(filepath):
    chunks = chunk_document(filepath)
    doc_uuid = str(uuid.uuid4())

    # store chunks in vector db
    for i, d in enumerate(chunks):
        embedding = get_embedding(d.page_content)
        chunk_id = f"{doc_uuid}-{i}"
        collection.add(
            ids=[chunk_id],
            embeddings=[embedding],
            documents=[d.page_content],
            metadatas=[{"file": filepath}]
        )

def store_documents(files):
    for file in files:
        store_document(file)

def retrieve_chunks(query, n):
    # retrieve relevant chunks from db
    embedding = get_embedding(query)
    results = collection.query(
        query_embeddings = [embedding],
        n_results=n
    )
    data = results['documents'][0]
    return data

def answer_query_with_rag(query, n=3):
    data = retrieve_chunks(query, n)
    context = '\n'.join(data)

    # prompt = """
    # Context information is below.
    # -------------
    # {context}
    # -------------
    # Given the context information, respond to this prompt: {query}
    # Avoid starting your response with phrases like "According to the context information", "Based on the provided context", or similar. Just directly provide the answer.
    # """

    prompt = """
    You are a highly knowledgeable AI assistant specializing in understanding and explaining codebases and technical documentation from **GitHub repositories**. Your task is to answer the user's question by rigorously analyzing the context provided. 

    Context:
    ---
    {context}
    ---

    Question: {query}
    Avoid starting your response with phrases like "According to the context information", "Based on the provided context", or similar. Just directly provide the answer.
    """

    output = ollama.generate(
        model="llama3:latest",
        prompt=prompt.format(context=context, query=query)
    )
    print(prompt.format(context=context, query=query))
    return output['response']

def answer_query_no_rag():
    prompt = """
    "You are a helpful AI assistant. To answer questions about a GitHub repository, I need you to first provide a repository URL in the 'Settings' section of the sidebar and click 'Ingest'. Once the repository is processed, I'll be able to answer your questions."
    """

    output = ollama.generate(
        model="llama3:latest",
        prompt=prompt
    )
    return output['response']

def main():
    # store_document("pokemon.txt")
    query = "Which Pokemon resemble penguins?"
    answer = answer_query_with_rag(query)
    print(answer)

if __name__ == "__main__":
    main()
