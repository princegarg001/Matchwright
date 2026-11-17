.PHONY: setup data data-small smoke test pairs run ui ui-test eval bias docker-up newman lint

setup:
	pip install -r requirements.txt
	cp -n .env.example .env || true

data:
	python -m app.data.pipeline --download --jd-limit 5000

data-small:
	python -m app.data.pipeline --jd-limit 500

smoke:
	python scripts/smoke_test.py

test:
	OFFLINE_MODE=true pytest -q

pairs:
	python -m app.cli batch samples/pairs.yaml --out reports/pairs.md

run:
	uvicorn app.api.main:app --reload --port 8000

ui:
	cd frontend && npm run dev

ui-test:
	cd frontend && npm test && npm run build

eval:
	python eval/run_eval.py

bias:
	python eval/bias_check.py

docker-up:
	docker compose up --build

newman:
	npx newman run postman/collection.json -e postman/local.env.json -r cli,htmlextra --reporter-htmlextra-export reports/newman.html

lint:
	ruff check app tests
