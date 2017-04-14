all: clean install lint test

clean:
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -delete
	find . -name '*.egg-info' -delete

coverage:
	py.test --cov=ecs_deplojo --cov-report=term-missing --cov-report=xml

install:
	pip install -e .[test]

lint:
	flake8 src/ tests/
	isort --recursive --check-only --diff src tests

test:
	py.test -vvv


release:
	pip install twine wheel
	rm -rf dist/*
	python setup.py sdist bdist_wheel
	twine upload -s dist/*
