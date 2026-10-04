## Commands

- run: `byox` (CLI entry point, `byox_ladder._cli:main`; install via `./install.sh`)
- test: `python3 -m pytest -q`
- test-changed: `scripts/test_changed.sh`
- lint: `pre-commit run ruff --all-files`
- coverage: `python -m pytest byox_ladder/tests/ --cov=byox_ladder --cov-branch --cov-fail-under=100 --cov-report=xml -q`
- coverage-gaps: `coverage-gaps coverage.xml`
