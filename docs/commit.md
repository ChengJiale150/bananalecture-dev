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
   | Backend | `just check` | Runs linting, type checks, and architecture tests |
   | Frontend | `bun run check` | Runs linting, type checks, and tests |

   Only proceed with the commit if all checks pass.

3. **Update Changelog**: If the change affects behaviour, append an entry to
   [CHANGELOG.md](../CHANGELOG.md) **in the same commit**. See [Changelog](#changelog) below.

## Format

- **Language**: All commit messages must be in **English**.
- **Structure**: Follow [Conventional Commits](https://www.conventionalcommits.org/).

  ```
  <type>(<scope>): <subject>

  <body>
  ```

- **Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.

## Changelog

Behaviour-changing commits must be recorded in [CHANGELOG.md](../CHANGELOG.md). This is the
only copy of the release history, so it has to stay trustworthy.

- **Scope**: required for `feat`, `fix`, `refactor` and `perf`. Not required for `docs`,
  `style`, `test`, `chore`, `ci`, `build` or `revert`.
- **Same commit**: the entry ships together with the code it describes. Never add it in a
  follow-up commit, and never edit an entry after its commit has been pushed.
- **Language**: Chinese, consistent with the rest of the file.
- **Placement**: append under `## [未发布]`, in the category matching the commit type:
  `新增` (feat), `修复` (fix), `优化` (perf), `重构` (refactor). Create the category if absent.
- **Format**:

  ```markdown
  - **<type>(<scope>): <一句话中文说明>**
    - 具体影响，或可核对的数据（可选，但推荐）
  ```

  Optionally append ` —— [<短哈希>](https://github.com/ChengJiale150/bananalecture-dev/commit/<短哈希>)`
  after the bolded summary. A commit cannot know its own hash, so entries written in the
  same commit normally omit it; add hashes for past commits, or fill them all in as part of
  a release pass.

- **Releases**: when cutting a release, rename `## [未发布]` to
  `## [<版本号>] - <YYYY-MM-DD>` and add a fresh empty `## [未发布]` above it.

## Examples

**Backend:**
```
feat(projects): add slide reordering functionality

Implement drag-and-drop slide reordering in the project editor.
- Add use case for position updates
- Update repository with reorder method
- Add architecture tests for layer compliance
```

This is a `feat`, so the same commit also appends to `CHANGELOG.md`:

```markdown
### 新增

- **feat(projects): 支持拖拽调整幻灯片顺序**
  - 项目编辑器支持拖拽排序，顺序变更即时持久化。
```

**Frontend:**
```
feat(projects): add slide reordering functionality

Implement drag-and-drop slide reordering in the project editor.
- Add useReorder hook for slide position management
- Update project API client with reorder endpoint
- Add unit tests for reordering logic
```
