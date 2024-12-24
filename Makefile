install:
	python -m pip install -r ./requirements/common.txt

install-dev:
	python -m pip install -r ./requirements/dev.txt

format:
	python -m ruff format ./src 
	python -m ruff check ./src --fix 

lint:
	python -m mypy ./src