# Miles Aggregator Makefile

.PHONY: help install test demo run examples clean lint format

help:  ## Show this help message
	@echo "Miles Aggregator - Available Commands:"
	@echo "======================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

test:  ## Run tests
	@echo "🧪 Running tests..."
	python3 -m pytest tests/ -v

test-cov:  ## Run tests with coverage
	@echo "🧪 Running tests with coverage..."
	python3 -m pytest tests/ --cov=clients --cov-report=term-missing

demo:  ## Run demo with mock data
	@echo "🎬 Running demo..."
	python3 demo.py

run:  ## Run main application (requires .env setup)
	@echo "🚀 Running main application..."
	python3 main.py

examples:  ## Run usage examples
	@echo "📚 Running usage examples..."
	python3 example_usage.py

setup:  ## Create .env template
	@echo "⚙️  Setting up configuration..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ Created .env file from template"; \
		echo "📝 Please edit .env with your Peloton credentials"; \
	else \
		echo "ℹ️  .env file already exists"; \
	fi

lint:  ## Run code linting
	@echo "🔍 Running linter..."
	flake8 clients/ tests/ *.py

format:  ## Format code
	@echo "🎨 Formatting code..."
	black clients/ tests/ *.py

type-check:  ## Run type checking
	@echo "🔍 Running type checker..."
	mypy clients/

clean:  ## Clean up generated files
	@echo "🧹 Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/

dev-setup: install setup  ## Complete development setup
	@echo "🛠️  Development setup complete!"
	@echo "📋 Next steps:"
	@echo "   1. Edit .env with your Peloton credentials"
	@echo "   2. Run 'make demo' to test with mock data"
	@echo "   3. Run 'make run' to use with real data"

check: lint type-check test  ## Run all code quality checks
	@echo "✅ All checks passed!"