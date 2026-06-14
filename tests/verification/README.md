# Verification Scripts

This directory contains verification scripts used to test and validate specific implementations of the DeepAgent test runner architecture.

## Scripts

### `verify_strategy_pattern.py`
Verifies the Strategy Pattern implementation for schedule resolution.

**Purpose**: Validates that the schedule resolver uses the Strategy Pattern correctly, with:
- Strategy interface definition
- Concrete strategies (single, suite, tag_filter)
- Factory pattern with registry
- Support for custom/extension strategies
- Backward compatibility

**Usage**:
```bash
./tests/verification/verify_strategy_pattern.py
```

### `verify_strategy_pattern_backend.py`
Backend-specific verification of the Strategy Pattern.

**Purpose**: Similar to the main strategy pattern verification but tests the backend implementation directly.

**Usage**:
```bash
./tests/verification/verify_strategy_pattern_backend.py
```

### `verify_token_integration.py`
Verifies the LLM token usage tracking integration.

**Purpose**: Validates that token usage from GLM LLM calls is properly:
- Captured via LangChain callbacks
- Stored in the llm_usage table
- Available through the analytics API

**Usage**:
```bash
./tests/verification/verify_token_integration.py
```

## Purpose of These Scripts

These verification scripts are different from unit tests in that they:

1. **Validate architectural patterns** - Ensure the codebase follows SOLID principles
2. **Integration verification** - Test that components work together correctly
3. **Development tools** - Help verify refactoring and feature implementations
4. **Documentation** - Serve as executable documentation of architecture decisions

## When to Use These Scripts

- **After refactoring**: Verify the refactored code maintains the same functionality
- **Before merging**: Ensure architectural patterns are correctly implemented
- **Troubleshooting**: Diagnose issues with specific architectural components
- **Onboarding**: Help new developers understand the architecture

## Running All Verification Scripts

```bash
# Make all scripts executable (if not already)
chmod +x tests/verification/*.py

# Run strategy pattern verification
./tests/verification/verify_strategy_pattern.py

# Run backend strategy pattern verification
./tests/verification/verify_strategy_pattern_backend.py

# Run token integration verification
./tests/verification/verify_token_integration.py
```

## Notes

- These scripts are **not** part of the automated test suite (pytest)
- They are standalone verification tools for development and validation
- Results should be manually reviewed for correctness
- Update these scripts when adding new strategies or architectural components
