.PHONY: help up up-d down down-v logs db

# Default target when simply running 'make'
.DEFAULT_GOAL := help

help:
	@echo "Available commands:"
	@echo "  make up                - Build and start the development stack"
	@echo "  make up-d              - Build and start the development stack in the background"
	@echo "  make db                - Start only PostgreSQL in the background"
	@echo "  make down              - Stop and remove containers and networks"
	@echo "  make down-v            - Stop the stack and delete PostgreSQL data"
	@echo "  make logs              - Follow logs for all services"

up:
	docker compose up --build

up-d:
	docker compose up --build -d

db:
	docker compose up -d postgres

down:
	docker compose down

down-v:
	docker compose down -v

logs:
	docker compose logs -f
