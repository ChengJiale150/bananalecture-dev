## Commit Guidelines

### Workflow
Before committing, follow these steps to ensure quality:

1.  **Check Changes**: Review your changes to ensure only intended modifications are included:
    ```bash
    git status
    git diff
    ```
2.  **Verify Quality**: Run the following command to ensure code quality:
    ```bash
    npm run check
    ```
    This command runs linting, type checks, and tests. Only proceed with the commit if all checks pass.

### Format
-   **Language**: All commit messages must be in **English**.
-   **Structure**: Follow [Conventional Commits](https://www.conventionalcommits.org/).
    ```
    <type>(<scope>): <subject>

    <body>
    ```
-   **Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.

### Example
```
feat(projects): add slide reordering functionality

Implement drag-and-drop slide reordering in the project editor.
- Add useReorder hook for slide position management
- Update project API client with reorder endpoint
- Add unit tests for reordering logic
```
