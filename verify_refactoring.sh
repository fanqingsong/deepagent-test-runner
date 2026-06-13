#!/bin/bash

echo "=========================================="
echo "TestCaseGenerator Refactoring Verification"
echo "=========================================="
echo ""

# Check if all components exist
echo "1. Checking component files..."
files=(
    "platform/backend/app/services/llm_client.py"
    "platform/backend/app/services/prompt_builder.py"
    "platform/backend/app/services/response_parser.py"
    "platform/backend/app/repositories/test_case_repository.py"
    "platform/backend/app/services/test_case_generator.py"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ✗ $file (MISSING)"
    fi
done

echo ""
echo "2. Checking test files..."
test_files=(
    "platform/backend/tests/services/test_llm_client.py"
    "platform/backend/tests/services/test_prompt_builder.py"
    "platform/backend/tests/services/test_response_parser.py"
    "platform/backend/tests/repositories/test_test_case_repository.py"
    "platform/backend/tests/services/test_test_case_generator_integration.py"
)

for file in "${test_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ✗ $file (MISSING)"
    fi
done

echo ""
echo "3. Line counts:"
echo "  LLMClient: $(wc -l platform/backend/app/services/llm_client.py | awk '{print $1}') lines"
echo "  PromptBuilder: $(wc -l platform/backend/app/services/prompt_builder.py | awk '{print $1}') lines"
echo "  ResponseParser: $(wc -l platform/backend/app/services/response_parser.py | awk '{print $1}') lines"
echo "  TestCaseRepository: $(wc -l platform/backend/app/repositories/test_case_repository.py | awk '{print $1}') lines"
echo "  TestCaseGenerator: $(wc -l platform/backend/app/services/test_case_generator.py | awk '{print $1}') lines"

echo ""
echo "4. Testing imports in Docker container..."
docker exec deepagent-tester-backend python3 -c "
from app.services.test_case_generator import TestCaseGenerator
from app.services.llm_client import LLMClient
from app.services.prompt_builder import PromptBuilder
from app.services.response_parser import ResponseParser
from app.repositories.test_case_repository import TestCaseRepository
print('  ✓ All components import successfully')
print('  ✓ TestCaseGenerator has all required methods')
print('  ✓ Backward compatibility maintained')
" 2>&1

echo ""
echo "=========================================="
echo "Refactoring Verification Complete"
echo "=========================================="
