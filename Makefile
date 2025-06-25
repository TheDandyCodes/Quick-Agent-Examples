.ONESHELL:
.PHONY: install compile

# Project parameters
PROJECT_NAME := RAG
PYTHON_VERSION := 3.11
ENV_NAME := $(PROJECT_NAME)

# Command to use Conda
SHELL := /bin/bash
RUN := conda run -n $(ENV_NAME) --live-stream

install:
	@echo "🔧 Creating virtual environment with Conda..."
	@if ! conda env list | grep -q "^$(ENV_NAME) "; then \
		conda create -n $(ENV_NAME) python=$(PYTHON_VERSION) pip -y; \
	else \
		echo "✅ The environment $(ENV_NAME) already exists."; \
	fi
	@echo "📦 Installing dependencies..."
	@$(RUN) pip install pip-tools
	@$(MAKE) compile
	@$(RUN) pip install -r requirements.txt
	@echo "✅ Installation complete. Use 'conda activate $(ENV_NAME)' to activate the environment."

compile:
	@echo "🔄 Compiling dependencies..."
	@$(RUN) pip-compile requirements.in