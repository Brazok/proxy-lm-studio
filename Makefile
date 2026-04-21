.DEFAULT_GOAL := help
UV := $(HOME)/.local/bin/uv

.PHONY: help install sync run run-dev lint format typecheck test test-cov pre-commit docker-build docker-up docker-down

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Installe toutes les dépendances (dev)
	$(UV) sync

sync: ## Synchronise strictement depuis le lockfile
	$(UV) sync --frozen

run: ## Lance le serveur (nécessite sudo pour le port 443)
	sudo $(UV) run proxy-lm-studio

run-dev: ## Lance sur le port 8443 (pas de sudo)
	PROXY_PORT=8443 $(UV) run proxy-lm-studio

lint: ## Lance ruff (linter)
	$(UV) run ruff check src/ tests/

format: ## Lance ruff (formatter)
	$(UV) run ruff format src/ tests/

typecheck: ## Lance mypy
	$(UV) run mypy src/

test: ## Lance les tests
	$(UV) run pytest

test-cov: ## Lance les tests avec rapport de couverture HTML
	$(UV) run pytest --cov-report=html
	@echo "Rapport disponible dans htmlcov/index.html"

pre-commit: ## Lance tous les hooks pre-commit
	$(UV) run pre-commit run --all-files

docker-build: ## Build l'image Docker
	docker build -t proxy-lm-studio:dev .

docker-up: ## Démarre avec compose
	docker compose up --build

docker-down: ## Arrête compose
	docker compose down
