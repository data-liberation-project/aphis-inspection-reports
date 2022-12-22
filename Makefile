.PHONY: README.md tests venv

requirements.txt: requirements.in
	pip-compile requirements.in

venv:
	python -m venv venv
	venv/bin/pip install -r requirements.txt

inspections-init:
	python scripts/00-fetch-inspection-list.py

inspections-refresh:
	python scripts/01-refresh-inspection-list.py

inspections-download:
	python scripts/02-download-inspection-pdfs.py

inspections: inspections-init inspections-refresh inspections-download


format:
	black scripts tests
	isort scripts tests

lint:
	black --check scripts tests
	isort --check scripts tests
	flake8 scripts tests

mypy:
	mypy scripts tests --ignore-missing-imports

tests:
	pytest tests -sv --cov
