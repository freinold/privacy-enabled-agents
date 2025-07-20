# Privacy-enabled Agents

This repository contains the code for my master thesis "Privacy-enabled Agents".
It is currently a work in progress and will be updated regularly.
If you have any questions or suggestions, feel free to open an issue or a pull request.

## Installation

### Prerequisites

- uv is installed: https://docs.astral.sh/uv/getting-started/installation/
- A container runtime is installed:
  - Docker: https://docs.docker.com/get-docker/
  - Podman: https://podman.io/getting-started/installation

### Setup

Create a venv and install the dependencies:

```bash
uv sync
```

## Usage

1. Start the docker-compose environment:

```bash
docker-compose up -d
```

2. Run the application:

```bash
uv run main.py
```

To stop the docker-compose environment, run:

```bash
docker-compose stop
```

## Development

### Dependencies

uv is used to manage dependencies in this project. The following commands are available:

- Add dependencies

```bash
uv add <package>
```

- Remove dependencies

```bash
uv remove <package>
```

- Update dependencies

```bash
uv lock -U
uv sync
```

- Add development dependencies

```bash
uv add --dev <package>
```

- Compile requirements

```bash
rm requirements.txt
uv pip compile --universal pyproject.toml -o requirements.txt
```

### Linting / Formatting

ruff is used for linting and formatting. The following commands are available:

- Lint the code

```bash
uv run ruff check --fix
```

- Format the code

```bash
uv run ruff format
```

### Pre-commit hooks

pre-commit is used to manage pre-commit hooks. The following commands are available:

- Install pre-commit hooks

```bash
uv run pre-commit install
```

- Run pre-commit hooks manually

```bash
uv run pre-commit run --all-files
```

- Update pre-commit hooks

```bash
uv run pre-commit autoupdate
```

### GitHub Actions

This project uses GitHub Actions to automate linting and formatting using Ruff. The workflow runs on push to the main branch and on pull requests. It performs the following actions:

- Runs Ruff linter with `--fix` option
- Runs Ruff formatter

You can see the workflow details in the `.github/workflows/ruff.yml` file.
