# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Invoice Guard is an expense invoice and receipt processing system for employees and finance reviewers. It extracts structured invoice data, automates deterministic policy checks, and uses retrieval-assisted semantic evaluation for ambiguous policy cases that cannot be resolved reliably with rules alone.

### Technology Stack

- **Backend:** Python, FastAPI, SQLAlchemy, PostgreSQL
- **Storage:** S3-compatible object storage
- **Infrastructure:** Redis where appropriate for rate limiting and ephemeral state
- **Frontend:** React, TypeScript, Vite
- **Frontend architecture:** Feature-Sliced Design
- **API contract:** OpenAPI with generated TypeScript types

### Testing

Behavior changes follow the BDD double-loop in `.claude/rules/common/development-workflow.md` (via the `bdd-guide` agent), not a standalone TDD cycle.

Testing principles:

- Do not optimize for an arbitrary coverage percentage
- Do not add trivial tests solely to increase coverage

## Git Workflow

- Keep changes narrowly scoped to one behavior, refactor, or concern
- Update tests with behavior changes
- Review the diff before considering work complete
- Commit message format and PR process: `.claude/rules/common/git-workflow.md`
