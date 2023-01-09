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

inspections-parse:
	python scripts/03-parse-inspection-pdfs.py

inspections-parse:
	python scripts/05-combine-inspection-data.py

inspections: inspections-init inspections-refresh inspections-download inspections-parse inspections-combine

# Intentionally a separate step, not in `make inspections`
upload:
	python scripts/04-upload-inspection-pdfs.py


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
