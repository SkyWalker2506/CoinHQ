.PHONY: dev migrate install stop logs

dev:
	docker-compose up --build

stop:
	docker-compose down

logs:
	docker-compose logs -f

migrate:
	docker-compose exec backend alembic upgrade head

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

.env:
	cp .env.example .env
	@echo "Created .env from .env.example — edit ENCRYPTION_KEY before starting"
