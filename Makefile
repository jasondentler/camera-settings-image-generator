PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip
SAMPLES := $(shell find samples -type f -name '*.jpg' ! -name '*_blurred.jpg' ! -name '*_settings.jpg' ! -name '*_post.jpg' ! -name '*_split_*.jpg' | sort)

.PHONY: help install check test samples

help:
	@echo "Targets:"
	@echo "  install  Install Python dependencies into the active environment"
	@echo "  check    Compile-check source files and run unit tests"
	@echo "  test     Run unit tests"
	@echo "  samples  Regenerate blurred sample images and companion text files"

install:
	$(PIP) install -r requirements.txt

check:
	$(PYTHON) -m py_compile src/*.py
	$(PYTHON) -m unittest discover

test:
	$(PYTHON) -m unittest discover

samples:
	@for image in $(SAMPLES); do \
		$(PYTHON) src/main.py "$$image"; \
	done
