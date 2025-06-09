# RAG implementation using Ollama and ChromaDB

import os
from langchain.text_splitter import Language, RecursiveCharacterTextSplitter
import ollama
import chromadb
import uuid
import shutil
import requests
import fnmatch

#client = chromadb.PersistentClient(path=".chroma")
client = chromadb.EphemeralClient()
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

def is_image(filepath):
    image_patterns = ['*.jpg', '*.jpeg', '*.png']
    for pattern in image_patterns:
        if fnmatch.fnmatch(filepath, pattern):
            return True
    return False

def load_document(filepath):
    # extract file contents
    print(f"Reading {filepath}")
    # if is_image(filepath):
    #     return image_to_text(filepath)
# else:
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            return content
    except Exception as e:
        print(f"Error opening {filepath}, will not store: {e}")
        return None
    
def chunk_document(filepath, chunk_size=750, chunk_overlap=75):

    text = load_document(filepath)

    if text:
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
    
    else:
        return None
    

def get_embedding(chunk):
    # embedding using ollama minilm
    response = ollama.embed(model="all-minilm", input=chunk)
    embedding = response["embeddings"]
    return embedding[0]

def store_document(filepath):
    chunks = chunk_document(filepath)

    if chunks:
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
    metadata = results['metadatas'][0]
    return data, metadata

def answer_query_with_rag(query, n=5):
    data, metadata = retrieve_chunks(query, n)

    sources = []
    lines = []
    for i in range(len(data)):
        filename = os.path.basename(metadata[i]['file'])
        text = data[i]
        line = f"{filename}: {text}"
        lines.append(line)
        sources.append({"file": filename, "text": text})

    context = '\n'.join(lines)

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
        model="llama3.1:8b-instruct-fp16",
        prompt=prompt.format(context=context, query=query)
    )
    print(prompt.format(context=context, query=query))
    return output['response'], sources

def answer_query_no_rag():
    prompt = """
    "You are a helpful AI assistant. To answer questions about a GitHub repository, I need you to first provide a repository URL in the 'Settings' section of the sidebar and click 'Ingest'. Once the repository is processed, I'll be able to answer your questions."
    """

    output = ollama.generate(
        model="llama3.1:8b-instruct-fp16",
        prompt=prompt
    )
    return output['response']

def image_to_text(filepath):
    name = os.path.basename(filepath)
    prompt = f"Given the image name, {name}, and content, describe this image. The description is most likely going to be used to improve other llm's understanding of the image, so give as much details as possible. Do not hallucinate."
    response = ollama.chat(
        model='llama3.2-vision',
        messages=[{
            'role': 'user',
            'content': prompt,
            'images': [filepath]
        }]
    )
    
    return response['message']['content']

def single_document_rag_test():
    store_document("pokemon.txt")
    query = "Which Pokemon resemble penguins?"
    answer = answer_query_with_rag(query)
    print(answer)


def main():
    store_document('rag-architecture.png')

if __name__ == "__main__":
    main()
