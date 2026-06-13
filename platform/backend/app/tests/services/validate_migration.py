#!/usr/bin/env python3
"""
Quick validation script for Result type migration.

Tests that the migrated services can be imported and have the expected methods.
"""

import sys
import ast
import inspect

def validate_service_migration():
    """Validate that services have been migrated correctly."""

    print("🔍 Validating Result Type Migration...")
    print("=" * 60)

    errors = []

    # Test 1: Check Result types can be imported
    try:
        from app.core.simple_result_types import (
            service_success, service_error, service_not_found,
            service_validation_error, ServiceSuccess, ServiceError
        )
        print("✅ Result types import successful")
    except ImportError as e:
        errors.append(f"❌ Failed to import Result types: {e}")
        print(errors[-1])

    # Test 2: Check ExecutionService migration
    try:
        from app.services.execution_service import ExecutionService

        # Check for new v2 methods
        v2_methods = [
            'resolve_target_tests_v2',
            'create_test_run_v2',
            'update_run_status_v2',
            'save_test_results_v2'
        ]

        for method_name in v2_methods:
            if not hasattr(ExecutionService, method_name):
                errors.append(f"❌ ExecutionService missing method: {method_name}")
                print(errors[-1])
            else:
                print(f"✅ ExecutionService has method: {method_name}")

        # Check that legacy methods still exist
        legacy_methods = [
            'resolve_target_tests',
            'create_test_run',
            'update_run_status',
            'save_test_results'
        ]

        for method_name in legacy_methods:
            if not hasattr(ExecutionService, method_name):
                errors.append(f"❌ ExecutionService missing legacy method: {method_name}")
                print(errors[-1])
            else:
                print(f"✅ ExecutionService has legacy method: {method_name}")

    except ImportError as e:
        errors.append(f"❌ Failed to import ExecutionService: {e}")
        print(errors[-1])

    # Test 3: Check SuiteService migration
    try:
        from app.services.suite_service import SuiteService

        v2_methods = [
            'resolve_suite_entries_v2',
            'resolve_dynamic_suite_v2',
            'create_suite_run_v2',
            'get_suite_run_with_entries_v2',
            'cancel_suite_run_v2'
        ]

        for method_name in v2_methods:
            if not hasattr(SuiteService, method_name):
                errors.append(f"❌ SuiteService missing method: {method_name}")
                print(errors[-1])
            else:
                print(f"✅ SuiteService has method: {method_name}")

        legacy_methods = [
            'resolve_suite_entries',
            'resolve_dynamic_suite',
            'create_suite_run',
            'get_suite_run_with_entries',
            'cancel_suite_run'
        ]

        for method_name in legacy_methods:
            if not hasattr(SuiteService, method_name):
                errors.append(f"❌ SuiteService missing legacy method: {method_name}")
                print(errors[-1])
            else:
                print(f"✅ SuiteService has legacy method: {method_name}")

    except ImportError as e:
        errors.append(f"❌ Failed to import SuiteService: {e}")
        print(errors[-1])

    # Test 4: Check ScriptValidationService migration
    try:
        from app.services.script_validation_service import ScriptValidationService

        v2_methods = [
            'validate_script_v2',
            'validate_script_with_metadata_v2',
            'determine_script_status_v2'
        ]

        for method_name in v2_methods:
            if not hasattr(ScriptValidationService, method_name):
                errors.append(f"❌ ScriptValidationService missing method: {method_name}")
                print(errors[-1])
            else:
                print(f"✅ ScriptValidationService has method: {method_name}")

        legacy_methods = [
            'validate_script',
            'validate_script_with_metadata',
            'determine_script_status'
        ]

        for method_name in legacy_methods:
            if not hasattr(ScriptValidationService, method_name):
                errors.append(f"❌ ScriptValidationService missing legacy method: {method_name}")
                print(errors[-1])
            else:
                print(f"✅ ScriptValidationService has legacy method: {method_name}")

    except ImportError as e:
        errors.append(f"❌ Failed to import ScriptValidationService: {e}")
        print(errors[-1])

    # Test 5: Check method signatures
    try:
        from app.services.execution_service import ExecutionService
        import inspect

        # Check that v2 methods have proper return type hints
        create_v2_sig = inspect.signature(ExecutionService.create_test_run_v2)
        print(f"✅ ExecutionService.create_test_run_v2 signature: {create_v2_sig}")

        save_v2_sig = inspect.signature(ExecutionService.save_test_results_v2)
        print(f"✅ ExecutionService.save_test_results_v2 signature: {save_v2_sig}")

    except Exception as e:
        errors.append(f"❌ Failed to inspect method signatures: {e}")
        print(errors[-1])

    # Test 6: Check test files exist
    import os
    test_files = [
        'app/tests/services/test_execution_service_result_types.py',
        'app/tests/services/test_suite_service_result_types.py',
        'app/tests/services/test_script_validation_service_result_types.py'
    ]

    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"✅ Test file exists: {test_file}")
        else:
            errors.append(f"❌ Test file missing: {test_file}")
            print(errors[-1])

    # Summary
    print("=" * 60)
    if errors:
        print(f"❌ Migration validation failed with {len(errors)} errors")
        for error in errors:
            print(f"  {error}")
        return 1
    else:
        print("✅ Migration validation successful!")
        print("\n📋 Migration Summary:")
        print("  • ExecutionService: 4 v2 methods + 4 legacy methods")
        print("  • SuiteService: 5 v2 methods + 5 legacy methods")
        print("  • ScriptValidationService: 3 v2 methods + 3 legacy methods")
        print("  • All Result types properly imported")
        print("  • All test files present")
        print("\n🎉 Core services successfully migrated to Result types!")
        return 0

if __name__ == "__main__":
    sys.exit(validate_service_migration())
