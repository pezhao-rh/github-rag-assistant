FROM python:3.12.11-slim

RUN groupadd -r appgroup && useradd -r -g appgroup appuser

USER root

RUN apt-get update && apt-get install -y git --no-install-recommends && rm -rf /var/lib/apt/lists/*
RUN pip install uv

RUN mkdir -p /app && chown root:root /app && chmod g+rwX /app
RUN mkdir -p /home/appuser && chown root:root /home/appuser && chmod g+rwX /home/appuser

WORKDIR /app

COPY pyproject.toml ./

RUN uv sync

USER appuser

COPY src/ .

EXPOSE 8501

CMD ["uv", "run", "streamlit", "run", "app.py"]