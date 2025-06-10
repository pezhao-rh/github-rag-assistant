FROM python:3.12.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y git --no-install-recommends && rm -rf /var/lib/apt/lists/*

RUN pip install uv

COPY pyproject.toml ./

RUN uv sync

COPY src/ .

EXPOSE 8501

CMD ["uv", "run", "streamlit", "run", "app.py"]