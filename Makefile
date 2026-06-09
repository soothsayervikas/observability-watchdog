.PHONY: install dev test lint seed samples demo webhook run-api docker docker-up typecheck

install:
	python -m pip install -e ".[dev]"
	cd dashboard && npm install

samples:
	python scripts/generate_samples.py

run-api:
	uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

webhook:
	python scripts/mock_webhook.py

seed:
	python scripts/seed_sample_logs.py --dataset error_spike

analyze:
	curl -X POST http://127.0.0.1:8000/api/v1/analyze/run

demo: samples seed analyze
	python scripts/run_demo.py

test:
	pytest -q --cov=app --cov-report=term-missing

typecheck:
	mypy app

lint:
	ruff check app tests scripts
	ruff format --check app tests scripts

secrets:
	python scripts/check_secrets.py

test-dashboard:
	cd dashboard && npm test

dashboard:
	cd dashboard && npm run dev

dashboard-build:
	cd dashboard && npm run build

docker:
	docker build -t observability-watchdog .

docker-up:
	docker compose up --build
