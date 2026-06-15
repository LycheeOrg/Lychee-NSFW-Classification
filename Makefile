IMAGE  ?= lychee-ai-vision
PORT   ?= 8000

.PHONY: lint test run docker-build docker-run

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run ty check .

format:
	uv run ruff format .
	uv run ruff check --unsafe-fixes --fix

test:
	uv run pytest

run:
	uv run uvicorn app.main:app --host 0.0.0.0 --port $(PORT) --reload

docker-build:
	docker build -t $(IMAGE) .

docker-run:
	docker run --rm -p $(PORT):8000 \
		--env-file .env \
		$(IMAGE)
