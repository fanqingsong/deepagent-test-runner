"""
SOLID Architecture Verification Test Runner

Run this script to execute all SOLID verification tests:
- Verifies all 5 SOLID principles
- Tests complete end-to-end workflows
- Validates repository, service, strategy, DI, health, metrics layers
"""

import subprocess
import sys


def run_verification():
    """Run all SOLID verification test suites."""
    test_files = [
        "test_solid_part1_repositories.py",
        "test_solid_part2_services.py",
        "test_solid_part3_strategies.py",
        "test_solid_part4_di_container.py",
        "test_solid_part5_health_metrics.py",
        "test_solid_part6_workflows.py",
        "test_solid_part7_result_types.py",
        "test_solid_part8_principles.py"
    ]

    print("=" * 80)
    print("SOLID Architecture Verification Test Suite")
    print("=" * 80)
    print()

    all_passed = True

    for test_file in test_files:
        print(f"\n{'=' * 80}")
        print(f"Running: {test_file}")
        print(f"{'=' * 80}")

        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_file, "-v"],
            capture_output=False
        )

        if result.returncode != 0:
            all_passed = False
            print(f"❌ {test_file} FAILED")
        else:
            print(f"✅ {test_file} PASSED")

    print("\n" + "=" * 80)
    if all_passed:
        print("✅ ALL SOLID VERIFICATION TESTS PASSED")
        print("=" * 80)
        print("\nSOLID Principles Verified:")
        print("✅ Single Responsibility Principle (SRP)")
        print("✅ Open/Closed Principle (OCP)")
        print("✅ Liskov Substitution Principle (LSP)")
        print("✅ Interface Segregation Principle (ISP)")
        print("✅ Dependency Inversion Principle (DIP)")
        print("\nLayers Verified:")
        print("✅ Repository Layer")
        print("✅ Service Layer")
        print("✅ Strategy Pattern")
        print("✅ DI Container")
        print("✅ Health Check System")
        print("✅ Metrics Collection")
        print("✅ Result Types")
        print("✅ Complete Workflows")
    else:
        print("❌ SOME SOLID VERIFICATION TESTS FAILED")
        print("=" * 80)

    return all_passed


if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    success = run_verification()
    sys.exit(0 if success else 1)
