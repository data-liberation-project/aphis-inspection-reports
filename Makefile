.PHONY: venv README.md

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
	black scripts
	isort scripts

lint:
	black --check scripts
	isort --check scripts
	flake8 scripts
