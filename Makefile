.PHONY: venv README.md

requirements.txt: requirements.in
	pip-compile requirements.in

venv:
	python -m venv venv
	venv/bin/pip install -r requirements.txt

inspections-init:
	venv/bin/python scripts/00-fetch-inspection-list.py

inspections-refresh:
	venv/bin/python scripts/01-refresh-inspection-list.py

inspections-download:
	venv/bin/python scripts/02-download-inspection-pdfs.py

inspections: inspections-init inspections-refresh inspections-download


format:
	venv/bin/black scripts
	venv/bin/isort scripts

lint:
	venv/bin/black --check scripts
	venv/bin/isort --check scripts
	venv/bin/flake8 scripts
