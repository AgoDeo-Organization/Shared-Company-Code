# AGENTS.md
# AI Agent Operating Rules for This Repository

## 1. Purpose

This document defines how AI agents (e.g. Codex, Claude Code, internal automation agents)
are allowed to interact with this repository.

Agents must follow these rules strictly.

## 2. General Project Structure

Use this simple template project structure:

```
repo/
├── pyproject.toml
├── README.md
├── LICENSE.txt
├── AGENTS.md
├── src/
│   └── myproject/
│       ├── __init__.py
│       ├── ...
├── tests/
│   └── ...
├── docs/
│   └── ...
├── scripts/
│   └── ...
```

## Coding standards
- Always import modules using this format: `from myproj.core import run`


## 2. Repository Overview

- Language: Python 3.11+
- Style: PEP8 + Black formatting
- Testing: pytest
- Type checking: mypy (strict mode)
- Linting: ruff
- Dependency management: poetry (or specify pip/requirements.txt)



## 5. Code Style Requirements

- Code must be **simple** and **human readable**
- Code must also be **sparse** and **spaced out**
- Make **frequent use of comments** to explain your logic
- Code should be object oriented
- Classes should have a unique purpose/goal
- Use dependency injection
- All functions must have type hints.
- All public functions must have Google-style docstrings (with args, returns, raises, ...).
- No function longer than 80 lines.
- No file longer than 1000 lines.
- No nested logic deeper than 3 levels.
- No wildcard imports.
- Use explicit exceptions.
- Avoid global state, except for logging

---

## 6. Testing Rules

Every new behavior requires:

- Unit tests in `/tests`
- At least one edge case
- At least one failure case

Agents must:

- Never reduce coverage
- Never delete tests unless replacing with stronger tests
- Run tests before finalizing changes

Test naming format:
```
test_<module>_<behavior>.py
```

---

## 7. Safe Refactoring Protocol

When refactoring:

1. Preserve public API
2. Do not change function signatures unless instructed
3. Add tests before modifying behavior
4. Keep commits small and atomic

---

## 8. Dependency Policy

Before adding dependency:

- Justify why stdlib is insufficient
- Confirm license compatibility
- Confirm long-term maintenance
- Keep dependency count minimal

---

## 9. Security Rules

Agents must:

- Never hardcode secrets
- Never log credentials
- Never expose API keys
- Use environment variables
- Validate all external inputs
- Sanitize file paths

Sensitive areas (extra caution required):

- Authentication
- Payments
- Data exports
- File uploads
- Webhooks

---

## 10. Documentation Rules

For new modules:

- Update `/docs`
- Add usage example
- Explain architectural placement

If behavior changes:
- Update README
- Update docstrings

Writing style:
- Must be written for a **12 year old** to understand.
- Exception: when technical terms are used (e.g. API, method, function, ...)
- Valid for Google-style docstrings and comments aswell

---

## 11. Commit Message Format

```
<type>: <short description>
<why this change was made> <risk assessment> <testing performed>
```

Types:

- feat
- fix
- refactor
- test
- docs
- perf
- chore

---

## 12. Large Change Policy

If change affects more than 5 files:

Agent must:

1. Provide plan first
2. List impacted modules
3. Describe risks
4. Wait for approval

---

## 13. AI Agent Self-Check Before Finalizing

Agent must verify:

- [ ] Code runs
- [ ] Tests pass
- [ ] No linter errors
- [ ] No type errors
- [ ] No architectural violations
- [ ] No duplicated logic introduced
- [ ] No circular imports
- [ ] No hidden breaking changes

---

## 14. Prohibited Shortcuts

Agents must NOT:

- Comment out failing code
- Bypass validation logic
- Ignore type errors
- Add `# type: ignore` without justification
- Catch broad `Exception` silently
- Remove error handling

---

## 15. Performance Constraints

- Avoid O(n²) unless justified
- Use generators for large data
- Avoid loading entire files in memory if unnecessary
- Use caching carefully (must be deterministic)

---

## 16. Determinism Requirement

All business logic must be deterministic.

No:
- Hidden randomness
- Time-dependent behavior without injection
- Implicit global state

---

## 17. Agent Escalation Rule

If unsure:

- Do not guess
- Propose alternatives
- Ask for clarification
- Provide tradeoffs

---

## 18. Versioning Policy

Public APIs must follow semantic versioning:

MAJOR.MINOR.PATCH

Breaking change → MAJOR
New feature → MINOR
Fix → PATCH

---

## 19. Migration Rule

If modifying data structures:

- Provide migration script
- Provide rollback instructions
- Ensure backward compatibility if possible

---

## 20. Final Principle

Clarity > Cleverness  
Explicit > Implicit  
Simple > Complex  
Safe > Fast  

Agents are collaborators, not decision-makers.
Architectural integrity always wins over speed.
