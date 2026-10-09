.PHONY: docs-check test up seed smoke

docs-check:
	uv run --locked python scripts/validate_blueprint.py

test:
	uv run --locked --extra test ruff check takshyra tests migrations
	uv run --locked --extra test python -m pytest -q

up:
	docker compose up --build

seed:
	docker compose exec api python -m takshyra.seed

smoke:
	docker compose exec -T api python scripts/smoke.py
