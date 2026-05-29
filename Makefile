.PHONY: install install-dev test smoke compare notebook lint clean

PDF ?= data/input/Metals_Option_Products.pdf
OUT ?= data/output

install:
	pip install -e .

install-dev:
	pip install -e ".[dev,notebook]"

test:
	pytest

smoke:
	python -m large_pdf_extractor.cli.main extract \
	  --pdf $(PDF) --output-dir $(OUT) --strategy pymupdf --llm-provider fake --max-chunks 12

compare:
	python -m large_pdf_extractor.cli.main extract \
	  --pdf $(PDF) --output-dir $(OUT) --strategy compare --llm-provider fake --max-chunks 12

notebook:
	jupyter nbconvert --to notebook --execute \
	  notebooks/01_phase1_cme_reference_demo.ipynb \
	  --output 01_phase1_cme_reference_demo.executed.ipynb

lint:
	ruff check src tests

clean:
	rm -rf data/output/* .pytest_cache .ruff_cache .mypy_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
