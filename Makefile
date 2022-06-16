SHELL := /bin/bash

.PHONY: help format
.DEFAULT: help

help:
	@echo "Usage: make <target>"
	@echo
	@echo "Available targets:"
	@echo "  format: Run type checking and code styling inplace"

format:
	isort .
	black .
	flake8 .
	mypy .
