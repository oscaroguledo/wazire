# Contributing to Wazire

Thank you for contributing. This document covers commit conventions, branch strategy, and pull request requirements.

---

## Conventional Commits

All commits must follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification:

```
<type>(<scope>): <short summary>

[optional body]

[optional footer(s)]
```

### Types

| Type | When to use |
|------|-------------|
| `feat` | A new feature or capability |
| `fix` | A bug fix |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test` | Adding or updating tests |
| `docs` | Documentation only changes |
| `ci` | Changes to CI/CD configuration or scripts |
| `chore` | Maintenance tasks (dependency bumps, tooling, etc.) |
| `perf` | Performance improvements |
| `style` | Formatting, whitespace — no logic change |
| `revert` | Reverts a previous commit |

### Scopes

Use a scope to narrow the area of change:

| Scope | Area |
|-------|------|
| `backend` | FastAPI application |
| `frontend` | React/TypeScript SPA |
| `worker` | Kafka consumer worker |
| `scheduler` | APScheduler process |
| `docker` | Docker / Docker Compose |
| `nginx` | Nginx configuration |
| `db` | Database models or migrations |
| `kafka` | Kafka producer/consumer utilities |
| `auth` | Authentication and authorisation |
| `billing` | Billing domain |
| `academic` | Academic domain (exams, questions, submissions) |
| `analytics` | Analytics / dashboard domain |
| `ci` | CI/CD pipeline |
| `deps` | Dependency updates |

### Examples

```
feat(academic): add PRELOAD_QUESTIONS scheduler job and Redis cache

fix(backend): add yield to lifespan context manager

refactor(worker): convert to class-based Worker with lifecycle methods

test(billing): add property-based tests for Invoice.to_dict

ci: add backend and frontend jobs to GitHub Actions workflow

docs: add CONTRIBUTING.md with commit and branch conventions

chore(deps): pin gunicorn to 23.0.0 in requirements.txt
```

### Rules

- Summary line: imperative mood, no period at the end, ≤ 72 characters.
- Body: wrap at 100 characters; explain *why*, not *what*.
- Breaking changes: add `BREAKING CHANGE:` footer or append `!` after the type/scope.

---

## Branch Strategy

```
main          ← production-ready; protected; requires passing CI + PR review
  └── develop ← integration branch; all feature/fix branches merge here first
        ├── fix/<short-description>     e.g. fix/lifespan-yield
        ├── feat/<short-description>    e.g. feat/force-submit-exam
        ├── refactor/<short-description>
        ├── chore/<short-description>
        └── ci/<short-description>
```

### Rules

- **Never push directly to `main` or `develop`** — always open a PR.
- Branch names use kebab-case: `fix/app-wide-refactor`, `feat/groq-key-rotator`.
- Keep branches short-lived; rebase on `develop` before opening a PR.
- Delete the branch after it is merged.

---

## Pull Request Requirements

1. **CI must pass** — all three jobs (`backend`, `frontend`, `playwright`) must be green before merge.
2. **Title ≤ 70 characters** — follow the same `<type>(<scope>): <summary>` format as commits.
3. **Description** must include:
   - A summary of what changed and why.
   - What was tested (unit, integration, e2e, manual).
   - Any blocked or deferred items.
4. **Coverage** — overall coverage must remain ≥ 90% (enforced by Codecov status check).
5. **At least one reviewer** must approve before merge.
6. **No force-push** to a PR branch after review has started.

### PR Description Template

```markdown
## Summary
<!-- What does this PR do and why? -->

## Changes
<!-- Bullet list of notable changes -->

## Testing
<!-- What tests were added or updated? What was tested manually? -->

## Blocked / Deferred
<!-- Anything intentionally left out of this PR? -->
```

---

## Local Development Checks

Run these before pushing to catch issues early:

```bash
# Backend
cd backend
ruff check .
mypy . --ignore-missing-imports
pytest --cov --cov-fail-under=90

# Frontend
cd frontend
npm run lint
npx tsc --noEmit
npm run test:coverage
```
