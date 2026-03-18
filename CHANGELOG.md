# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.1.0.0] - 2026-03-18

### Added

- Architecture design doc with constitutional AI monitoring layer
- Model-agnostic Python SDK with adapter pattern (Anthropic + OpenAI)
- Governance service scaffold (FastAPI)
- Default constitution (5 rules, LLM-interpreted)
- Interpreter prompt v1 (Claude 3.5 Sonnet)
- Golden set consistency checker (8 test cases)
- Audit log schema + evaluation state machine
- Smart output truncation strategy (paragraph-boundary chunking)
- Project governance docs (CLAUDE.md, TODOS.md)

### Fixed

- Lambda closure bug in evaluation loop (chunk not properly captured)
- Prompt corruption in multi-chunk evaluation
- User prompt always empty in wrap()
- Async task silent death on unhandled exceptions
- Adapter lifecycle management in fire-and-forget mode
- Auth/rate-limit/timeout errors distinguished in error handling
