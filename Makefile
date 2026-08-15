PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip
SAMPLES := $(filter-out %_blurred.jpg,$(wildcard samples/*.jpg))

.PHONY: help install check samples

help:
	@echo "Targets:"
	@echo "  install  Install Python dependencies into the active environment"
	@echo "  check    Compile-check source files"
	@echo "  samples  Regenerate blurred sample images and companion text files"

install:
	$(PIP) install -r requirements.txt

check:
	$(PYTHON) -m py_compile src/*.py

samples:
	@for image in $(SAMPLES); do \
		$(PYTHON) src/main.py "$$image"; \
	done
