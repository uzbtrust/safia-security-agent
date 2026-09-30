.PHONY: setup test bandit
setup:
	uv venv .venv && uv pip install -e ".[dev]"
test:
	.venv/bin/python -m pytest -q
bandit:
	.venv/bin/python scripts/bandit_baseline.py
