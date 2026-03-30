# Commit Guidelines

## Workflow

Before committing, follow these steps to ensure quality:

1. **Check Changes**: Review your changes to ensure only intended modifications are included:
   ```bash
   git status
   git diff
   ```

2. **Verify Quality**: Run the quality check command for your project:

   | Project | Command | Description |
   |---------|---------|-------------|
   | Backend | `just pre-commit` | Runs linting, type checks, and architecture tests |
   | Frontend | `bun run check` | Runs linting, type checks, and tests |

   Only proceed with the commit if all checks pass.

## Format

- **Language**: All commit messages must be in **English**.
- **Structure**: Follow [Conventional Commits](https://www.conventionalcommits.org/).

  ```
  <type>(<scope>): <subject>

  <body>
  ```

- **Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.

## Examples

**Backend:**
```
feat(projects): add slide reordering functionality

Implement drag-and-drop slide reordering in the project editor.
- Add use case for position updates
- Update repository with reorder method
- Add architecture tests for layer compliance
```

**Frontend:**
```
feat(projects): add slide reordering functionality

Implement drag-and-drop slide reordering in the project editor.
- Add useReorder hook for slide position management
- Update project API client with reorder endpoint
- Add unit tests for reordering logic
```
