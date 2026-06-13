#!/usr/bin/env python3
"""
Token Management DI Integration Verification Script

This script verifies that token management services have been properly
integrated into the DI container without requiring the full runtime environment.
"""

import sys
import ast
from pathlib import Path


def check_file_exists(file_path):
    """Check if a file exists."""
    return Path(file_path).exists()


def parse_python_file(file_path):
    """Parse a Python file and return the AST."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return ast.parse(f.read(), filename=file_path)
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return None


def check_imports(tree, required_imports):
    """Check if required imports are present in the AST."""
    found_imports = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in required_imports:
                    found_imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for alias in node.names:
                    full_import = f"{node.module}.{alias.name}"
                    if full_import in required_imports or alias.name in required_imports:
                        found_imports.add(alias.name)

    return found_imports


def check_class_attributes(tree, class_name, required_attributes):
    """Check if a class has required attributes."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            found_attributes = set()
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            found_attributes.add(target.id)
            return found_attributes
    return set()


def check_function_definitions(tree, required_functions):
    """Check if required functions are defined."""
    found_functions = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.name in required_functions:
                found_functions.add(node.name)

    return found_functions


def verify_container_integration():
    """Verify token management integration in container.py."""
    print("=" * 80)
    print("TOKEN MANAGEMENT DI CONTAINER INTEGRATION VERIFICATION")
    print("=" * 80)

    base_path = Path("platform/backend/app")
    container_path = base_path / "core" / "container.py"
    factory_path = base_path / "repositories" / "repository_factory.py"

    # Check files exist
    print("\n1. Checking files exist...")
    files_to_check = [
        container_path,
        factory_path,
        base_path / "services" / "token_budget_service.py",
        base_path / "services" / "token_quota_service.py",
        base_path / "services" / "token_alert_service.py",
        base_path / "services" / "token_reporting_service.py",
        base_path / "repositories" / "token_budget_repository.py",
        base_path / "repositories" / "token_quota_repository.py",
        base_path / "repositories" / "token_alert_repository.py",
    ]

    for file_path in files_to_check:
        exists = check_file_exists(file_path)
        status = "✓" if exists else "✗"
        print(f"  {status} {file_path}")

    # Check container imports
    print("\n2. Checking container imports...")
    required_service_imports = {
        "TokenBudgetService",
        "TokenQuotaService",
        "TokenAlertService",
        "TokenReportingService"
    }

    required_repo_imports = {
        "SQLAlchemyTokenBudgetRepository",
        "SQLAlchemyTokenQuotaRepository",
        "SQLAlchemyTokenAlertRepository"
    }

    required_interface_imports = {
        "ITokenBudgetRepository",
        "ITokenQuotaRepository",
        "ITokenAlertRepository"
    }

    container_tree = parse_python_file(container_path)
    if container_tree:
        service_imports = check_imports(container_tree, required_service_imports)
        repo_imports = check_imports(container_tree, required_repo_imports)
        interface_imports = check_imports(container_tree, required_interface_imports)

        print(f"  Services: {len(service_imports)}/{len(required_service_imports)} imported")
        for imp in required_service_imports:
            status = "✓" if imp in service_imports else "✗"
            print(f"    {status} {imp}")

        print(f"  Repositories: {len(repo_imports)}/{len(required_repo_imports)} imported")
        for imp in required_repo_imports:
            status = "✓" if imp in repo_imports else "✗"
            print(f"    {status} {imp}")

        print(f"  Interfaces: {len(interface_imports)}/{len(required_interface_imports)} imported")
        for imp in required_interface_imports:
            status = "✓" if imp in interface_imports else "✗"
            print(f"    {status} {imp}")

    # Check container class attributes
    print("\n3. Checking Container class attributes...")
    required_providers = {
        "token_budget_repository",
        "token_quota_repository",
        "token_alert_repository",
        "token_budget_service",
        "token_quota_service",
        "token_alert_service",
        "token_reporting_service"
    }

    if container_tree:
        providers = check_class_attributes(container_tree, "Container", required_providers)
        print(f"  Providers: {len(providers)}/{len(required_providers)} registered")
        for provider in required_providers:
            status = "✓" if provider in providers else "✗"
            print(f"    {status} {provider}")

    # Check provider functions
    print("\n4. Checking provider functions...")
    required_providers = {
        "provide_token_budget_service",
        "provide_token_quota_service",
        "provide_token_alert_service",
        "provide_token_reporting_service"
    }

    if container_tree:
        provider_funcs = check_function_definitions(container_tree, required_providers)
        print(f"  Provider functions: {len(provider_funcs)}/{len(required_providers)} defined")
        for func in required_providers:
            status = "✓" if func in provider_funcs else "✗"
            print(f"    {status} {func}()")

    # Check provider aliases
    print("\n5. Checking provider aliases...")
    required_aliases = {
        "DependsTokenBudgetService",
        "DependsTokenQuotaService",
        "DependsTokenAlertService",
        "DependsTokenReportingService"
    }

    if container_tree:
        aliases = check_class_attributes(container_tree, None, required_aliases)
        print(f"  Aliases: {len(aliases)}/{len(required_aliases)} defined")
        for alias in required_aliases:
            status = "✓" if alias in aliases else "✗"
            print(f"    {status} {alias}")

    # Check repository factory
    print("\n6. Checking RepositoryFactory methods...")
    required_factory_methods = {
        "get_token_budget_repository",
        "get_token_quota_repository",
        "get_token_alert_repository",
        "set_token_budget_repository",
        "set_token_quota_repository",
        "set_token_alert_repository"
    }

    factory_tree = parse_python_file(factory_path)
    if factory_tree:
        factory_methods = check_function_definitions(factory_tree, required_factory_methods)
        print(f"  Methods: {len(factory_methods)}/{len(required_factory_methods)} defined")
        for method in required_factory_methods:
            status = "✓" if method in factory_methods else "✗"
            print(f"    {status} {method}()")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    all_checks_passed = True

    # Count total checks
    total_checks = (
        len(files_to_check) +
        len(required_service_imports) +
        len(required_repo_imports) +
        len(required_interface_imports) +
        len(required_providers) +
        len(required_providers) +
        len(required_aliases) +
        len(required_factory_methods)
    )

    # Estimate passed checks (simplified)
    passed_checks = 0

    if all(check_file_exists(f) for f in files_to_check):
        passed_checks += len(files_to_check)

    if container_tree:
        passed_checks += len(service_imports)
        passed_checks += len(repo_imports)
        passed_checks += len(interface_imports)
        passed_checks += len(providers)
        passed_checks += len(provider_funcs)
        passed_checks += len(aliases)

    if factory_tree:
        passed_checks += len(factory_methods)

    percentage = (passed_checks / total_checks * 100) if total_checks > 0 else 0

    print(f"\nIntegration Status: {passed_checks}/{total_checks} checks passed ({percentage:.1f}%)")

    if percentage >= 95:
        print("✓ Token management services successfully integrated into DI container!")
        return 0
    else:
        print("✗ Some integration checks failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(verify_container_integration())
