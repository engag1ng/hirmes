# Run all tests
To run all tests navigate to `/flask-app` and then run:
`pytest`

## Profiling
To find slow parts of code use the `--profile flag` like so:
`pytest --profile`

# Run single tests
To run a single test specify the file like so:
`pytest tests/test_*.py`

# Linting
1. Lint all files in a directory with `pylint ./<dir>`
2. Lint single files afterwards with `pylint <file>`