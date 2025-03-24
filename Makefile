.ONESHELL:
.PHONY: install compile

# Project parameters
PROJECT_NAME := RAG
PYTHON_VERSION := 3.11
ENV_NAME := $(PROJECT_NAME)

# Command to use Conda
SHELL = /bin/bash
RUN = conda run -n $(ENV_NAME) --live-stream
CONDA_ACTIVATE = source $(shell conda info --base)/etc/profile.d/conda.sh && conda activate $(ENV_NAME)

# Install the environment with Conda and dependencies
install:
	@echo "🔧 Creating virtual environment with Conda..."
	@if ! conda env list | grep -q "^$(ENV_NAME) "; then \
		conda create -y -n $(ENV_NAME) python=$(PYTHON_VERSION) pip=24.0; \
	else \
		echo "✅ The environment $(ENV_NAME) already exists."; \
	fi
	@echo "📦 Installing dependencies..."
	@$(CONDA_ACTIVATE) && pip install pip-tools uv==0.4.7
	@make compile
	@$(RUN) uv pip install -r requirements.txt
	@echo "✅ Installation complete. Use 'conda activate $(ENV_NAME)' to activate the environment."

# Generate requirements.txt from requirements.in
compile:
	@echo "🔄 Compiling dependencies..."
	@$(RUN) uv pip compile --universal -o requirements.txt requirements.in

deploy:
	@echo "🚀 Deploying the application for testing..."
	$(RUN) streamlit run App/st_RAG.py --server.address 0.0.0.0 --server.port 8505

deploy_test:
	@echo "🚀 Deploying the application for testing..."
	$(RUN) streamlit run App/st_RAG.py --server.address localhost --server.port 8507