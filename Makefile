VERSION ?= 0.1.3
REGISTRY ?= quay.io/rh-ee-pezhao/appeng

llamastack:
	source .venv/bin/activate
	INFERENCE_MODEL=llama3.1:8b-instruct-fp16 llama stack build --template ollama --image-type venv --run

ui:
	uv run streamlit run src/app.py

build_ui:
	podman build --platform linux/amd64 -t github-rag-ui:$(VERSION) .

build_and_push_ui: build_ui
	podman tag github-rag-ui:$(VERSION) $(REGISTRY)/github-rag-ui:$(VERSION)
	podman push $(REGISTRY)/github-rag-ui:$(VERSION)