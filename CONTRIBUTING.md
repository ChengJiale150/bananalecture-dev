# Contributing to bananalecture_backend

First off, thank you for considering contributing to bananalecture_backend! It's people like you that make bananalecture_backend such a great tool.

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## How Can I Contribute?

### Reporting Bugs

- **Check for existing issues**: Before opening a new issue, search to see if someone else has already reported the problem.
- **Provide detail**: Include steps to reproduce, what you expected to happen, and what actually happened.

### Suggesting Enhancements

- **Explain the use case**: Why is this feature needed? How would it benefit other users?

### Pull Requests

1.  **Fork the repo** and create your branch from `main`.
2.  **Initialize the environment**: Run `just init` and `just install`.
3.  **just your changes**: Ensure your code follows the [Style Guidelines](#style-guidelines).
4.  **Run checks**: Ensure all checks pass by running `just check`.
5.  **Submit the PR**: Link it to any related issues and provide a clear description of the changes.

## Style Guidelines

### Python Style

- We follow **PEP 8**.
- We use **Ruff** for formatting and linting.
- We use **Mypy** for static type checking (strict mode).
- Docstrings should follow the **Google Style**.

### Commit Messages

We use **Conventional Commits**:
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Changes that do not affect the meaning of the code
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `test`: Adding missing tests or correcting existing tests
- `chore`: Changes to the build process or auxiliary tools

Example: `feat: add user authentication module`

## Development Environment

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) for dependency management.
