.PHONY: install dev dev-backend dev-frontend telegram docker-up docker-down test clean help

help:
	@echo "SwaraSetu Development Commands:"
	@echo "  make dev           - Run backend and frontend concurrently"
	@echo "  make dev-backend   - Run FastAPI backend server (port 8000)"
	@echo "  make dev-frontend  - Run Vite frontend dev server (port 5173)"
	@echo "  make telegram      - Start backend, localtunnel & register Telegram bot"
	@echo "  make docker-up     - Start all services via Docker Compose"
	@echo "  make docker-down   - Stop Docker Compose services"
	@echo "  make test          - Run pytest backend test suite"
	@echo "  make install       - Install Python and Node dependencies"

install:
	pip install -r backend/requirements.txt
	npm install

dev-backend:
	uvicorn app.main:app --app-dir backend --reload --port 8000

dev-frontend:
	npm run dev

telegram:
	./scripts/start_telegram.sh

dev:
	npx -y concurrently -k -n "backend,frontend" -c "blue,green" \
		"uvicorn app.main:app --app-dir backend --reload --port 8000" \
		"npm run dev"

docker-up:
	docker compose up -d

docker-down:
	docker compose down

test:
	pytest backend/tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf dist .pytest_cache
