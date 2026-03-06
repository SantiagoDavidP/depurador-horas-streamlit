.PHONY: help dev build test lint docker-up docker-down migrate seed clean

# Default target
help:
	@echo "Comandos disponibles:"
	@echo "  make dev          — Inicia el entorno de desarrollo completo"
	@echo "  make build        — Build de produccion (frontend + backend check)"
	@echo "  make test         — Ejecuta todos los tests"
	@echo "  make test-fe      — Tests de frontend (Vitest)"
	@echo "  make test-be      — Tests de backend (pytest)"
	@echo "  make lint         — Ejecuta linters"
	@echo "  make docker-up    — Levanta el stack completo con Docker"
	@echo "  make docker-down  — Para Docker Compose"
	@echo "  make migrate      — Ejecuta migraciones de base de datos"
	@echo "  make seed         — Carga datos de prueba"
	@echo "  make clean        — Limpia archivos temporales"

# Desarrollo
dev:
	@echo "Iniciando entorno de desarrollo..."
	@cp -n .env.development .env 2>/dev/null || true
	@echo "Iniciando PostgreSQL..."
	docker-compose up -d db
	@echo "Esperando PostgreSQL..."
	@sleep 3
	@echo "Ejecutando migraciones..."
	alembic upgrade head
	@echo "Iniciando backend en background (puerto 8000)..."
	uvicorn api.main:app --reload --port 8000 &
	@echo "Iniciando frontend (puerto 5173)..."
	npm run dev

# Build
build:
	npm run build
	python -m py_compile api/main.py
	@echo "Build completado"

# Tests
test: test-fe test-be
	@echo "Todos los tests completados"

test-fe:
	npx vitest run --reporter=verbose

test-be:
	python -m pytest tests/backend/ -v

test-coverage:
	npx vitest run --coverage
	python -m pytest tests/backend/ --cov=api --cov-report=term-missing

# Lint
lint:
	npm run lint
	black api/ --check --line-length 88
	isort api/ --check-only

lint-fix:
	npm run lint:fix
	black api/ --line-length 88
	isort api/

# Docker
docker-up:
	@cp -n .env.development .env 2>/dev/null || true
	docker-compose up --build

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

# Base de datos
migrate:
	alembic upgrade head

migrate-create:
	@read -p "Nombre de la migracion: " name; \
	alembic revision --autogenerate -m "$$name"

seed:
	python scripts/seed.py

# Limpieza
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf dist/ coverage/ htmlcov/ .coverage 2>/dev/null || true
	@echo "Limpieza completada"
