# Contributing to Expense Tracker API

Thank you for your interest in contributing. This project demonstrates production-grade backend engineering patterns; contributions should preserve that quality bar.

## Getting started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USER/Expense-Tracker-API.git`
3. Copy environment: `cp .env.example .env`
4. Start stack: `make run && make migrate`
5. Run tests: `make test`

## Development workflow

1. Create a feature branch from `main`
2. Make focused changes with tests
3. Run lint: `make lint`
4. Run integration tests: `make test`
5. Open a pull request with a clear description

## Code standards

- **Python 3.12+**, type hints where practical
- **black** + **isort** + **flake8** (line length 88)
- Layered architecture: endpoints → services → repositories
- No business logic in route handlers
- Integration tests for API behavior changes

## Commit messages

Use conventional prefixes: `feat:`, `fix:`, `docs:`, `test:`, `chore:`, `refactor:`

## Security

Do not commit secrets, `.env` files, or credentials. Report vulnerabilities privately before opening public issues.

## Questions

Open a GitHub Discussion or Issue for architecture questions before large refactors.
