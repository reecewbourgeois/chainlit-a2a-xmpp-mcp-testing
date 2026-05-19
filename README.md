# chainlit-a2a-xmpp-mcp-testing

## Pre-requisites

> Note 1: most of the commands in this section should be run from the either the `/backend` or `/frontend` directories, depending on which part of the project a section is referring to.

> Note 2: I am primarily using VS Code and there are some configuration issues with monorepos and the various standard extensions with the tools used in this project (uv, oxc, etc.). I have included the general .vscode settings I have in place, but you may need to adjust them for your own setup.

### Backend (/backend)

- uv (https://docs.astral.sh/uv/)
- Ollama and a model of your choice (https://ollama.com/)

`uv` will handle the dependencies and virtual environment for the backend. To install the dependencies, run the following command:

```bash
uv sync
```

Make sure to use the proper uv commands instead of the normal pip commands when managing dependencies (`uv add` instead of `pip install`). See their documentation for more details.

If you chose a different model than is present in the code, make sure to update the `MODEL` variable in `main.py` to match the name of your model in Ollama.

### Frontend (/frontend)

- nvs (Node Version Switcher, https://github.com/jasongin/nvs) or Node.js directly installed

Use this to manage your Node.js versions. Install the latest LTS version:

```bash
nvs add lts
nvs link lts
```

After that, enable pnpm and install the dependencies:

```bash
npm install -g pnpm
pnpm install
```

A note on pnpm: you may run into issues with some post-install build scripts for one or more packages (I think the Sass package does this). If you do, follow the steps in the error message to fix it. It should be something like this:

```bash
# Remember: use the command indicated in the error message, it may be different from this one.
pnpm approve-builds
```

## Running the project

### Backend (/backend)

To run the backend, use the following command:

```bash
uv run app/main.py
```

This will start the FastAPI uvicorn server on port 5000. You can access the API at `http://localhost:5000`. There are swagger docs available at `http://localhost:5000/docs`.

> Note: If you see `"0.0.0.0"` in the code and terminal output, that is normal. It just means "use the host machine's IP address" which for us means `localhost`, or `127.0.0.1` if you're fancy.

### Frontend (/frontend)

To run the frontend, use the following command:

```bash
pnpm dev
```

This will start the Vite development server on port 3000. You can access the frontend at `http://localhost:3000`.


## Formatting & Linting

> Note: If you are using VS Code and have the appropriate extensions installed, you should be able to format on save. The commands below are for manual use or if you want to run them in a CI/CD pipeline. Linting errors should show in your editor as you work.

### Backend (/backend)

Ruff has been defined as a dev dependency. It can be used as both a linter and a formatter. To run it, use the following commands:

```bash
uv run ruff check .
uv run ruff format .
```

### Frontend (/frontend)

The frontend uses oxlint (https://oxc.rs/docs/guide/usage/linter.html) as a linter and oxfmt (https://oxc.rs/docs/guide/usage/formatter.html) as a formatter. To run them, use the following commands:

```bash
# These commands are defined in the package.json file as "lint" and 
# "format" scripts, these are not native commands.

# Default behavior is to check for linting without fixing
pnpm lint
pnpm lint:fix

# Default behavior is to format files, this will modify files in place
pnpm format
pnpm format:check
```