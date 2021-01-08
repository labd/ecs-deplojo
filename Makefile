all: clean install lint test

clean:
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -delete
	find . -name '*.egg-info' -delete

coverage:
	py.test --cov=ecs_deplojo --cov-report=term-missing --cov-report=xml

install:
	pip install -e .[test]

docker-build:
	docker build -t labdigital/ecs-deplojo:0.9.2 .

docker-push:
	docker push labdigital/ecs-deplojo:0.9.2

lint:
	flake8 src/ tests/
	isort --check --diff src tests
	black --check-only src/ tests/

test:
	py.test -vvv tests/

format:
	isort src tests
	black src/ tests/

release:
	pip install twine wheel
	rm -rf dist/*
	python setup.py sdist bdist_wheel
	twine upload -s dist/*
