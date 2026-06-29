.PHONY: help setup hooks format lint test check clean

help:
	@echo "Available commands:"
	@echo "  setup   - Install dependencies, git hooks, and create .env file"
	@echo "  hooks   - Install pre-commit and pre-push git hooks"
	@echo "  format  - Format Python source code using ruff"
	@echo "  lint    - Run ruff linter and fix fixable errors"
	@echo "  test    - Run the test suite"
	@echo "  check   - Run CI checks (lint + format, no auto-fix)"
	@echo "  clean   - Remove temporary cache and directory files"

setup:
	pip install -e ".[dev]"
	pre-commit install --hook-type pre-commit --hook-type pre-push
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env from .env.example. Please configure GEMINI_API_KEY in .env."; \
	else \
		echo ".env already exists."; \
	fi

hooks:
	pre-commit install --hook-type pre-commit --hook-type pre-push

format:
	ruff format src/ tests/

lint:
	ruff check src/ tests/ --fix

test:
	pytest tests/

check:
	ruff check src/ tests/
	ruff format --check src/ tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
