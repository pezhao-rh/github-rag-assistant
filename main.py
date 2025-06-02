import os
from langchain.text_splitter import Language, RecursiveCharacterTextSplitter
import ollama
import chromadb
import uuid

client = chromadb.PersistentClient(path=".chroma")
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
    
def chunk_document(filepath, chunk_size=500, chunk_overlap=50):

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
    response = ollama.embed(model="all-minilm", input=chunk)
    embedding = response["embeddings"]
    return embedding[0]

def store_document(filepath):
    chunks = chunk_document(filepath)
    doc_uuid = str(uuid.uuid4())

    for i, d in enumerate(chunks):
        embedding = get_embedding(d.page_content)
        chunk_id = f"{doc_uuid}-{i}"
        collection.add(
            ids=[chunk_id],
            embeddings=[embedding],
            documents=[d.page_content]
        )

def retrieve_chunks(query, n):
    embedding = get_embedding(query)
    results = collection.query(
        query_embeddings = [embedding],
        n_results=n
    )
    data = results['documents'][0]
    return data

def main():
    store_document("pokemon.txt")
    query = "What kind of Pokemon is Piplup? Describe this Pokemon."
    data = retrieve_chunks(query, 2)
    context = '\n'.join(data)

    prompt = """
    Context information is below.
    -------------
    {context}
    -------------
    Given the context information, respond to this prompt: {query}
    """

    output = ollama.generate(
        model="llama3.2:3b",
        prompt=prompt.format(context=context, query=query)
    )
    print(output['response'])

if __name__ == "__main__":
    main()
