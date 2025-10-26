Local test execution

Prerequisites:
- Python >= 3.11 (CPython or PyPy 3.11)
- pip
- Dependencies from requirements_test.txt (or minimal set from requirements_test_min.txt)

Setup:
```bash
pip install -e .
pip install -r requirements_test.txt
```

Run tests:
```bash
pytest --durations=10 --benchmark-disable tests/
```

Coverage (optional):
```bash
pytest --cov --cov-report=html tests/
```

Troubleshooting:
- Ensure astroid version matches the pin in requirements_test_min.txt.
- Primer tests interact with external repositories; skip primer locally unless explicitly needed.
- If you see path-related expectations in tests (e.g., config file location), ensure the package is installed in editable mode (`pip install -e .`).

