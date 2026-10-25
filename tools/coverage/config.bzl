"""Shared minimum coverage for every language's coverage test targets.

Every language enforces aggregate line coverage. Python's coverage.py report
also includes branches in its existing 100% gate (python/.coveragerc).
Ruby measures lines only. TypeScript collects V8 branches without gating them.
Go converts native block profiles to lines; Rust gates LLVM line coverage.
Neither native wrapper enforces a separate branch threshold.
"""

MINIMUM_LINE_COVERAGE = 100
