#!/usr/bin/env python3
"""Static analysis of PR #104 fix without requiring API keys."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))


def analyze_fix():
    """Analyze the PR #104 fix implementation."""
    print("PR #104 Static Code Analysis")
    print("=" * 60)

    # Check if the fix is present by reading the file
    agent_file = Path(__file__).parent / 'src' / 'landuse' / 'agents' / 'landuse_agent.py'

    if not agent_file.exists():
        print("❌ Agent file not found")
        return False

    content = agent_file.read_text()

    # Check for key elements of the fix
    checks = {
        "Union import": "from typing import Union" in content,
        "AppConfig import": "from landuse.core.app_config import AppConfig" in content,
        "Union type hint": "Union[LanduseConfig, AppConfig]" in content,
        "isinstance check": "isinstance(config, AppConfig)" in content,
        "Conversion method": "_convert_to_legacy_config" in content,
        "Debug attribute": "self.debug =" in content,
        "self.config.debug replaced": content.count("if self.debug:") > 5,
    }

    print("\nCode Analysis Results:")
    print("-" * 60)

    all_passed = True
    for check_name, check_result in checks.items():
        status = "✅" if check_result else "❌"
        print(f"{status} {check_name}: {check_result}")
        if not check_result:
            all_passed = False

    # Count the actual replacements
    old_pattern_count = content.count("self.config.debug")
    new_pattern_count = content.count("self.debug")
    print(f"\nPattern Analysis:")
    print(f"  - Old pattern (self.config.debug): {old_pattern_count} occurrences")
    print(f"  - New pattern (self.debug): {new_pattern_count} occurrences")

    # Check the conversion method implementation
    if "_convert_to_legacy_config" in content:
        print("\n✅ Conversion method found. Key mappings:")
        conversion_mappings = [
            "legacy_config.db_path = app_config.database.path",
            "legacy_config.model_name = app_config.llm.model_name",
            "legacy_config.max_iterations = app_config.agent.max_iterations",
            "legacy_config.debug = app_config.logging.level == 'DEBUG'",
        ]

        for mapping in conversion_mappings:
            if mapping in content:
                print(f"  ✅ {mapping.split(' = ')[0].strip()}")
            else:
                print(f"  ❌ Missing: {mapping}")
                all_passed = False

    # Look for potential issues
    print("\n" + "=" * 60)
    print("Potential Issues Analysis:")
    print("-" * 60)

    issues = []

    # Check for bypassing validation in conversion
    if "object.__new__(LanduseConfig)" in content:
        issues.append("⚠️  Bypasses LanduseConfig validation in conversion method")

    # Check for incomplete conversion
    if "_convert_to_legacy_config" in content:
        # Count fields in LanduseConfig vs fields being mapped
        legacy_fields = [
            'db_path', 'model_name', 'temperature', 'max_tokens',
            'max_iterations', 'max_execution_time', 'max_query_rows',
            'default_display_limit', 'debug', 'enable_memory'
        ]

        mapped_fields = []
        for field in legacy_fields:
            if f"legacy_config.{field} =" in content:
                mapped_fields.append(field)

        missing_fields = set(legacy_fields) - set(mapped_fields)
        if missing_fields:
            issues.append(f"⚠️  Not all fields mapped in conversion: {', '.join(missing_fields)}")

    # Check for memory management
    if "self.app_config = config" in content and "self.config = self._convert_to_legacy_config" in content:
        issues.append("⚠️  Stores both config objects, potential memory overhead")

    # Check for thread safety
    if "self.debug" in content and "__init__" in content:
        # Check if debug is properly initialized in all paths
        init_method = content[content.find("def __init__"):content.find("def ", content.find("def __init__") + 10)]
        if init_method.count("self.debug =") < 2:
            issues.append("⚠️  Debug attribute might not be set in all initialization paths")

    if issues:
        for issue in issues:
            print(issue)
    else:
        print("✅ No obvious issues found")

    print("\n" + "=" * 60)
    print("Architecture Assessment:")
    print("-" * 60)

    # Architecture assessment
    arch_issues = []

    if "_convert_to_legacy_config" in content:
        arch_issues.append("🏗️  Band-aid solution: Adds conversion layer instead of refactoring to use single config")
        arch_issues.append("🏗️  Technical debt: Maintains two config systems increases complexity")
        arch_issues.append("🏗️  Violation of DRY: Config mapping logic duplicates configuration structure")

    if "object.__new__" in content:
        arch_issues.append("🔒 Security concern: Bypasses Pydantic validation could introduce invalid configs")

    if arch_issues:
        for issue in arch_issues:
            print(issue)

    # Performance assessment
    print("\n" + "=" * 60)
    print("Performance Considerations:")
    print("-" * 60)

    perf_issues = []

    if "self.app_config = config" in content and "self.config = self._convert_to_legacy_config" in content:
        perf_issues.append("⚠️  Memory: Stores duplicate config objects")
        perf_issues.append("⚠️  CPU: Conversion happens on every agent initialization")

    if perf_issues:
        for issue in perf_issues:
            print(issue)
    else:
        print("✅ No significant performance concerns")

    return all_passed


def check_test_coverage():
    """Check if tests exist for the fix."""
    print("\n" + "=" * 60)
    print("Test Coverage Analysis:")
    print("-" * 60)

    test_patterns = [
        "tests/test_landuse_agent.py",
        "tests/unit/test_landuse_agent.py",
        "tests/integration/test_landuse_agent.py",
    ]

    tests_found = False
    for pattern in test_patterns:
        test_file = Path(__file__).parent / pattern
        if test_file.exists():
            print(f"✅ Found test file: {pattern}")
            content = test_file.read_text()

            # Check for config compatibility tests
            if "AppConfig" in content and "LanduseConfig" in content:
                print(f"  ✅ Tests both config types")
            else:
                print(f"  ⚠️  May not test both config types")

            tests_found = True
            break

    if not tests_found:
        print("⚠️  No unit tests found for LanduseAgent")

    return tests_found


def main():
    """Run analysis."""
    fix_present = analyze_fix()
    tests_exist = check_test_coverage()

    print("\n" + "=" * 60)
    print("FINAL ASSESSMENT:")
    print("-" * 60)

    if fix_present:
        print("✅ Fix appears to be implemented correctly")
        print("⚠️  However, this is a band-aid solution that increases technical debt")
        print("📝 Issue #103 correctly tracks the need to remove legacy config")
    else:
        print("❌ Fix implementation has issues")

    print("\nRecommendations:")
    print("1. ✅ Merge PR #104 to unblock CI/CD pipeline")
    print("2. ⚠️  Prioritize Issue #103 to remove legacy LanduseConfig")
    print("3. 📊 Add performance monitoring for config conversion overhead")
    print("4. 🔒 Consider security implications of bypassing validation")
    print("5. 📝 Add comprehensive tests for both config types")


if __name__ == "__main__":
    main()