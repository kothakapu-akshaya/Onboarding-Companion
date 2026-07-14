# Contributing to Corpus Collections API

Thank you for your interest in contributing to the Corpus Collections API! This backend project is built using FastAPI, and we welcome contributions from everyone, especially those skilled in FastAPI. Please take a moment to review this document to understand our guidelines and best practices.

## How to Contribute

1.  **Fork the Repository**: Start by forking the `corpus/corpus-server-app` repository to your code.swecha.org.
2.  **Clone Your Fork**:
    ```bash
    git clone https://code.swecha.org/corpus/corpus-server-app.git
    cd corpus-server-app
    ```
3.  **Create a New Branch**: Create a new branch for your feature or bug fix.
    ```bash
    git checkout -b feature/your-feature-name
    # Or for a bug fix:
    git checkout -b fix/issue-description
    ```
4.  **Make Your Changes**: Implement your changes, following the code style guidelines below.
5.  **Add Tests**: If you're adding new features or fixing bugs, include appropriate tests to cover your changes.
6.  **Commit Your Changes**: Write clear, concise, and semantic commit messages following the convention: `<type>(<scope>): <description>`.
    -   **type**: `feat` (new feature), `fix` (bug fix), `docs` (documentation only changes), `style` (formatting, missing semicolons, etc.; no code change), `refactor` (code refactoring), `test` (adding missing tests, refactoring tests), `chore` (maintenance, build process, etc.)
    -   **scope** (optional): The part of the codebase affected (e.g., `auth`, `api-v1`, `database`, `records`, `docs`)
    -   **description**: A concise description of the change in imperative mood (e.g., `add new user endpoint` not `added new user endpoint`).

    Example: `feat(api-v1): add new user registration endpoint`
7.  **Submit a Pull Request**: Push your branch to your fork and open a pull request to the `main` branch of the original repository. Ensure your merge request title also follows the semantic commit message convention.

## Setting Up Your Development Environment

Refer to the [README.md](README.md) for detailed instructions on setting up your local development environment, including:

-   Creating a virtual environment (`uv venv`)
-   Installing dependencies (`uv sync` for all deps, or `uv sync --no-dev` for production only)
-   Starting services with Docker Compose
-   Configuring environment variables (`.env` file)
-   Setting up the PostgreSQL database (using `setup_postgresql.py` script or manual steps)

## Code Style and Formatting

We use `ruff` for code formatting and linting. Please ensure your code adheres to these standards before submitting a pull request.

-   **Install development dependencies**:
    ```bash
    uv sync
    ```
-   **Format and lint code with Ruff**:
    ```bash
    uv run ruff format .
    uv run ruff check .
    ```
-   **Typing**: Use type hints extensively for function arguments, return values, and variables.
-   **Naming Conventions**:
    -   Variables and functions: `snake_case`
    -   Classes: `PascalCase`
    -   Constants: `UPPER_SNAKE_CASE`
-   **Error Handling**: Use explicit `try...except` blocks. Avoid bare `except` clauses. Log errors appropriately.
-   **Docstrings**: Use Google-style docstrings for modules, classes, and functions.

## Running Tests

We use `pytest` for running tests. Always run the tests before submitting your changes.

-   **Run all tests**:
    ```bash
    uv run pytest
    ```
-   **Run a single test file**:
    ```bash
    uv run pytest tests/test_your_module.py
    ```
-   **Run a specific test within a file**:
    ```bash
    uv run pytest tests/test_your_module.py::test_function_name
    ```

## Database Migrations

This project uses Alembic for database migrations.

-   **Create a new migration**:
    ```bash
    uv run alembic revision --autogenerate -m "description_of_migration"
    ```
-   **Apply migrations**:
    ```bash
    uv run alembic upgrade head
    ```
-   **Check migration status**:
    ```bash
    uv run alembic current
    ```

## Semantic Versioning and Naming Conventions

To maintain a clear and organized project history, we enforce semantic naming conventions for issue titles, commit messages, and merge request titles.

### Semantic Issue Titles
Issue titles should follow the semantic convention: `<type>(<scope>): <description>`

-   **type**:
    -   `feat`: A new feature
    -   `fix`: A bug fix
    -   `docs`: Documentation only changes
    -   `style`: Changes that do not affect the meaning of the code (white-space, formatting, missing semicolons, etc.)
    -   `refactor`: A code change that neither fixes a bug nor adds a feature
    -   `perf`: A code change that improves performance
    -   `test`: Adding missing tests or correcting existing tests
    -   `chore`: Other changes that don't modify src or test files (e.g., build process, tooling, dependencies)
-   **scope** (optional): The part of the codebase affected (e.g., `auth`, `api-v1`, `database`, `records`, `docs`).
-   **description**: A concise description of the issue in imperative mood (e.g., `add new user endpoint` not `added new user endpoint`).

Examples:
- `feat(users): Implement user profile update endpoint`
- `fix(auth): Correct OTP verification logic`
- `docs(setup): Update PostgreSQL setup instructions`

### Semantic Merge Request Titles
Merge request titles should follow the same semantic convention as commit messages and issue titles: `<type>(<scope>): <description>`. This helps in automatically generating changelogs and understanding the purpose of the merge request at a glance.

Examples:
- `feat(records): Add support for video file uploads`
- `fix(deps): Upgrade FastAPI to latest version`
- `refactor(auth): Consolidate JWT token generation`

## Submitting Changes (Pull Request Guidelines)

When submitting a pull request, please ensure it includes:

-   **Clear Description**: A detailed explanation of the changes, why they were made, and any relevant context.
-   **Checklist**: A checklist of completed tasks, such as:
    -   [ ] Code follows project API guidelines (if applicable).
    -   [ ] Tests are included and passing.
    -   [ ] Documentation is updated (if applicable).
    -   [ ] Code adheres to project coding standards.
-   **Related Issue(s)**: Link to any relevant issues using `Closes #IssueNumber`.

We appreciate your contributions and look forward to your pull requests!
