# chainlit-a2a-xmpp-mcp-testing

## Pre-requisites

Note: most of the commands in this section should be run from the either the `/backend` or `/frontend` directories, depending on which part of the project a section is referring to.

### Backend (/backend)

- uv (https://docs.astral.sh/uv/)

`uv` will handle the dependencies and virtual environment for the backend. To install the dependencies, run the following command:

```bash
uv sync
```

Make sure to use the proper uv commands instead of the normal pip commands when managing dependencies (`uv add` instead of `pip install`). See their documentation for more details.

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

## Formatting & Linting

### Backend (/backend)

Ruff has been defined as a dev dependency. It can be used as both a linter and a formatter. To run it, use the following command:

```bash
uv run ruff check .
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