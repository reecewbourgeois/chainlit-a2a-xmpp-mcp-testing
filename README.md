# chainlit-a2a-xmpp-mcp-testing

## Pre-requisites
- uv (https://docs.astral.sh/uv/)

`uv` will handle the dependencies and virtual environment for this project. To install the dependencies, run the following command:

```bash
# You may need to set up a virtual environment first using `uv venv` if you haven't already, not sure if sync does this for you
uv sync
```

## Formatting & Linting

Ruff has been defined as a dev dependency. It can be used as both a linter and a formatter. To run it, use the following command:

```bash
uv run ruff check .
```