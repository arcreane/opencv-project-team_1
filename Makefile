.PHONY: install run test

install:
	python3 -m pip install -r requirements.txt

run:
	python3 main.py

test:
	python3 -m pytest tests

