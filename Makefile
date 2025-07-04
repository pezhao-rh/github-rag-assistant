VERSION ?= 0.2.0
REGISTRY ?= quay.io/ecosystem-appeng

llamastack:
	source .venv/bin/activate && \
	INFERENCE_MODEL=llama3.2:3b-instruct-fp16 llama stack build --template ollama --image-type venv --run

ui:
	uv run streamlit run src/app.py

build_ui:
	podman build --platform linux/amd64 -t github-rag-ui:$(VERSION) .

build_and_push_ui: build_ui
	podman tag github-rag-ui:$(VERSION) $(REGISTRY)/github-rag-ui:$(VERSION)
	podman push $(REGISTRY)/github-rag-ui:$(VERSION)