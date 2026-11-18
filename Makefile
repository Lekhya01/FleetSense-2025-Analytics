.PHONY: install download build validate dashboard test all
install:
	python -m pip install -r requirements.txt
download:
	python -m pipeline.ingest
build:
	python -m pipeline.build
validate:
	python -m pipeline.validate
dashboard:
	streamlit run dashboard/app.py
test:
	pytest -q
all: download build validate test
