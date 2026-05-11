# Aegis Backend

FastAPI service that monitors EVM wallets for risky ERC-20 approvals.
Week 1 scope: Ethereum mainnet, Etherscan + Alchemy.

## Setup

```bash
cd backend
uv sync --all-extras
cp .env.example .env
```

## Run

```bash
uv run uvicorn aegis.main:app --reload --port 8000
```

## Test

```bash
uv run pytest -q
uv run ruff check .
```
