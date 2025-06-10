# RAG Assistant for Github Repositories

[Design Document](https://docs.google.com/document/d/1Bo_BkGSxWiDNKUSwEG-GPFBL6swkyRGxIxlsVxe085k/edit?usp=sharing)

This application provides an interactive chatbot interface to analyze and ask questions about a specific GitHub repository. 

It helps teams understand and adapt to large and unfamiliar codebases by offering specialized insight into repositories.

To get this running, jump straight to [installation](#install). 

## Description 
A chat assistant that allows users to ask questions about a GitHub repo (e.g., “How do I deploy this?” or “Explain this function”), using RAG (Retrieval-Augmented Generation) with LLMs.

**What is RAG?** RAG enhances LLMs by retrieving relevant information from an external knowledge base to ground its responses, making them more accurate and up-to-date.

## Features
- Chat assistant with memory and knowledge of provided repository
- Sources tab to view referenced files
- Detailed directory tree visualization

## See it in action 

![demo](./images/source-demo.png)

## Architecture

- **Streamlit App**: Chat interface, repository visualization
- **Llamastack**: API layer for agents, tooling, and vector IO 
- **Ollama**: Runs embedding model (all-minilm), generation model (Llama3)
- **In-memory Faiss Database**: Stores embeddings and performs similarity search for RAG

## Requirements

Ollama installed with the `minilm` and `llama3.1:8b-instruct-fp16` models:
```sh
ollama pull all-minilm
ollama pull llama3.1:8b-instruct-fp16
```

## Install 

1. Make sure that `uv` is installed

```sh
uv --version
```

If not, install using `pip`

```sh
pip install uv
```

2. Install the dependencies

```sh
uv sync
```

3. Make sure Ollama is running

```sh
ollama run llama3.1:8b-instruct-fp16 # Or start the Ollama application
```

4. Start the LlamaStack server

```sh
source .venv/bin/activate
INFERENCE_MODEL=llama3.1:8b-instruct-fp16 llama stack build --template ollama --image-type venv --run
```

4. Run the Streamlit app
```sh
uv run streamlit run app.py
```