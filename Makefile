.PHONY: install run stop test lint migrate down build logs shell prod-build prod-up release-prepare deploy-staging docs-pdf

docs-pdf:
	python scripts/generate_documentation_pdf.py --lang en

install:
	pip install -r requirements.txt -r requirements-dev.txt

run:
	docker compose up -d

build:
	docker compose build

prod-build:
	docker build -f docker/Dockerfile -t expensetracker-api:$$(cat VERSION) .
	docker build -f docker/Dockerfile.celery.prod -t expensetracker-celery:$$(cat VERSION) .

prod-up:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file $${ENV_FILE:-.env.staging} up -d

deploy-staging:
	bash scripts/deploy-staging.sh $${ENV_FILE:-.env.staging}

release-prepare:
	bash scripts/release-prepare.sh

stop:
	docker compose stop

down:
	docker compose down -v

logs:
	docker compose logs -f

test:
	docker compose exec -T api pytest tests/integration

lint:
	black --check app tests
	isort --check-only app tests
	flake8 app tests

migrate:
	docker compose exec -T api alembic upgrade head

shell:
	docker compose exec -it api bash
