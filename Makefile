all: clean install lint test

clean:
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -delete
	find . -name '*.egg-info' -delete

coverage:
	uv run --group test pytest --cov=ecs_deplojo --cov-report=term-missing --cov-report=xml

install:
	uv sync --group test

docker-build:
	docker build -t labdigital/ecs-deplojo:0.9.2 .

docker-push:
	docker push labdigital/ecs-deplojo:0.9.2

lint:
	uv run --group test ruff format --check
	uv run --group test ruff check

test:
	uv run --group test pytest -vvv tests/

format:
	uv run --group test ruff format
