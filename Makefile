.PHONY: install install-api install-frontend test check test-gemini run-cli run-api run-frontend build-frontend

install:
	python3 -m pip install -r requirements.txt

install-api:
	python3 -m pip install -r requirements-api.txt

install-frontend:
	cd frontend && npm install

test:
	python3 -m unittest discover

check:
	python3 -m py_compile api.py jira-ai.py core/config.py core/models.py core/gemini.py core/jira_client.py core/service.py core/formatter.py tests/test_core.py tests/test_api.py
	python3 -m unittest discover
	cd frontend && npm run build

test-gemini:
	python3 -u jira-ai.py --test-gemini

run-cli:
	python3 -u jira-ai.py

run-api:
	python3 -m uvicorn api:app --reload

run-frontend:
	cd frontend && npm run dev

build-frontend:
	cd frontend && npm run build
