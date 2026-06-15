# Команди для Docker
.PHONY: up down build logs restart clean

up:
	docker-compose up -d

down:
	docker-compose down

build:
	docker-compose up -d --build

logs:
	docker-compose logs -f

restart: down up

clean:
	docker-compose down -v
	docker system prune -f

local-run:
	python3 bot_service/bot_app.py