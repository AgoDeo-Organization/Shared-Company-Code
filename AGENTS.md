# AI Agent Operating Rules for This Repository

*Version 0.1.1*

## 1. Purpose

This document defines how AI agents (e.g. Codex, Claude Code, internal automation agents)
are allowed to interact with this repository.

Agents must follow these rules strictly.

## 2. Important Rules

- Keep the code **simple**. The people interacting with this repository are not necessairly advanced programmers
- Make the code human readable (e.g. use `orders_last_day` instead of `o`)
- Use comments frequently, especially for higher level logic.
- When you are modifying code, do not fix formatting of current code to avoid too many diff lines (e.g. ignore long lines)
- Only do exactly what you are told to do. Do NOT proactively fix mypy errors, lint errors, formatting errors, docstrings, docs, implement tests. You must always ask or suggest.
- Always make minimal changes to keep diff simple. First change the code, and then ask if you can also fix mypy errors, lint errors, formatting errors, ...
- Any text (docs, docstrings, comments) must be explained in simple language, assuming reader is **12 years old**. Only keep technical terms (e.g. API, method, ...)

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

## 3. Coding standards
- Always import modules using this format: `from myproj.core import run`
- Use PEP8 + Black formatting
- Use clear and explicit exceptions.

## 4. Testing Rules

Imporant testing rules:
- All tests are with `pytest`
- Agents must **always** run **all** tests after making modifications
- Tests should be fast, independed and repeatable
- Do NOT call real APIs, use real databases, depend on the internet
- Always run test before merging. If tests fail, merging fails
- Every new behaviour requires a new test

Use this folder structure:

```
project/
│
├── src/
│   └── your_code.py
│
└── tests/
    └── test_your_code.py
```

Structure rules:
- Test files must start with: test_
- Test functions must start with: test_
- Keep tests inside a folder called tests

Other testing rules:
- Test at least one edge case
- Always test error behavior, not just happy paths.
- Write clear names for tests. The name should explain what is being tested.
- Each test should check one behavior only. Do not put many unrelated checks in one test.
- Never reduce coverage, and never delete tests unless replacing with stronger tests

## 5. Security Rules

How to manage credentials:
- Locally: save in `.env` file in project root
- AWS Lambda: configuration → environment variables
- Create file `src/config.py` and load secrets with `load_dotenv()` and `API_KEY = os.environ['API_KEY']`
- Use `from src.config import API_KEY` to use secrets through project

Important rules:
- **NEVER** commit credentials or `.env` files to git. Always gitignore!
- **NEVER** hardcode credentials in code
- Validate all external inputs
- Sanitize file paths

## 6. Documentation Rules

For new modules:

- Update `/docs`
- Add usage example
- Explain architectural placement

If behavior changes:
- Update README
- Update docstrings

Docstings & type hint rules:
- All functions must have type hints.
- All functions (public and private) must have Google-style docstrings (with args, returns, raises, ...).

Writing style:
- Must be written for a **12 year old** to understand.
- Exception: when technical terms are used (e.g. API, method, function, ...)

## 7. Commit Message Format

```
[agent] <type>: <short description>
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

## 8. Large Change Policy

If change affects more than 5 files:

Agent must:

1. Provide plan first
2. List impacted modules
3. Describe risks
4. Wait for approval

## 9. AI Agent Self-Check Before Finalizing

Before finalizing any change, agents **MUST**:
- Verify code runs
- Run all tests using `pytest`
- No linter errors using `ruff check .`
- No type errors using `mypy src`

## 10. Final Principle

- Clarity > Cleverness
- Explicit > Implicit
- Simple > Complex
- Safe > Fast

Agents are collaborators, not decision-makers.
Architectural integrity always wins over speed.
