ifeq ($(OS),Windows_NT)
PYTHON ?= .venv/Scripts/python.exe
else
PYTHON ?= .venv/bin/python
endif
DOCKER ?= docker
IMAGE_NAME ?= database-backup
IMAGE_TAG ?= latest

.PHONY: build-local build-docker test

build-local:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt nuitka
	$(PYTHON) -m nuitka \
		--onefile \
		--standalone \
		--output-filename=database-backup \
		--include-data-files=config.yaml.example=config.yaml.example \
		--include-data-files=env.example=env.example \
		--assume-yes-for-downloads \
		main.py

build-docker:
	$(DOCKER) build -t $(IMAGE_NAME):$(IMAGE_TAG) .

test:
	$(PYTHON) -m pytest tests/ -v \
		--cov=main \
		--cov=config_loader \
		--cov=controllers \
		--cov=models \
		--cov=services \
		--cov=views \
		--cov-fail-under=90
