#!/usr/bin/env python3
"""
Coverage analysis tool for GRIMOIRE Runner.

This script analyzes the current test coverage and identifies areas
that need additional testing.
"""

import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple


def run_coverage() -> None:
    """Run coverage and generate XML report."""
    print("🧪 Running tests with coverage...")
    result = subprocess.run([
        sys.executable, "-m", "pytest", "tests/",
        "--cov=grimoire_runner",
        "--cov-report=xml",
        "--quiet"
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Tests failed: {result.stderr}")
        sys.exit(1)


def parse_coverage_xml() -> List[Tuple[str, int, int, float]]:
    """Parse coverage.xml and return coverage data."""
    coverage_file = Path("coverage.xml")
    if not coverage_file.exists():
        print("❌ coverage.xml not found. Run tests with coverage first.")
        sys.exit(1)
    
    tree = ET.parse(coverage_file)
    root = tree.getroot()
    
    coverage_data = []
    
    for class_elem in root.findall(".//class"):
        filename = class_elem.get("filename", "")
        if not filename.startswith("src/grimoire_runner"):
            continue
            
        lines = class_elem.find("lines")
        if lines is None:
            continue
            
        total_lines = 0
        covered_lines = 0
        
        for line in lines.findall("line"):
            hits = int(line.get("hits", "0"))
            total_lines += 1
            if hits > 0:
                covered_lines += 1
        
        if total_lines > 0:
            coverage_pct = (covered_lines / total_lines) * 100
            coverage_data.append((filename, total_lines, covered_lines, coverage_pct))
    
    return coverage_data


def analyze_coverage(coverage_data: List[Tuple[str, int, int, float]]) -> None:
    """Analyze coverage data and provide recommendations."""
    print("\n📊 Coverage Analysis\n")
    
    # Sort by coverage percentage (lowest first)
    coverage_data.sort(key=lambda x: x[3])
    
    print("Modules with lowest coverage (highest priority for testing):")
    print("=" * 70)
    
    low_coverage = []
    medium_coverage = []
    high_coverage = []
    
    for filename, total, covered, pct in coverage_data:
        # Clean up filename for display
        display_name = filename.replace("src/grimoire_runner/", "").replace(".py", "")
        
        status = ""
        if pct == 0:
            status = "🔴 NO COVERAGE"
            low_coverage.append((display_name, total, covered, pct))
        elif pct < 30:
            status = "🟠 LOW"
            low_coverage.append((display_name, total, covered, pct))
        elif pct < 70:
            status = "🟡 MEDIUM"
            medium_coverage.append((display_name, total, covered, pct))
        else:
            status = "🟢 GOOD"
            high_coverage.append((display_name, total, covered, pct))
        
        print(f"{display_name:40} {covered:3}/{total:3} lines {pct:5.1f}% {status}")
    
    print(f"\n📈 Summary:")
    print(f"   🔴 No/Low Coverage: {len(low_coverage)} modules")
    print(f"   🟡 Medium Coverage: {len(medium_coverage)} modules") 
    print(f"   🟢 Good Coverage:   {len(high_coverage)} modules")
    
    if low_coverage:
        print(f"\n🎯 Priority Areas for Testing:")
        print("=" * 50)
        for name, total, covered, pct in low_coverage[:5]:  # Top 5 priorities
            uncovered = total - covered
            print(f"• {name}: {uncovered} uncovered lines ({pct:.1f}% coverage)")
        
        print(f"\n💡 Recommended next steps:")
        print("1. Focus on modules with 0% coverage first (highest impact)")
        print("2. Add integration tests for UI components")
        print("3. Test error handling and edge cases")
        print("4. Add tests for utility functions and helpers")


def generate_test_suggestions() -> None:
    """Generate suggestions for new tests based on low coverage areas."""
    suggestions = {
        "ui/browser": [
            "Test compendium browsing functionality",
            "Test item selection and filtering",
            "Test browser navigation and search"
        ],
        "ui/cli": [
            "Test CLI argument parsing",
            "Test interactive mode",
            "Test command execution and error handling"
        ],
        "ui/interactive": [
            "Test REPL functionality",
            "Test command history and completion",
            "Test interactive flow execution"
        ],
        "integrations/rng_integration": [
            "Test random number generation",
            "Test seed handling",
            "Test distribution functions"
        ],
        "integrations/llm_integration": [
            "Test LLM prompt generation",
            "Test response parsing",
            "Test error handling for API failures"
        ],
        "utils/serialization": [
            "Test YAML loading and saving",
            "Test data validation",
            "Test error handling for malformed files"
        ],
        "utils/logging": [
            "Test log configuration",
            "Test different log levels",
            "Test log formatting"
        ]
    }
    
    print(f"\n🧪 Test Implementation Suggestions:")
    print("=" * 50)
    
    for module, tests in suggestions.items():
        print(f"\n{module}:")
        for test in tests:
            print(f"  • {test}")


def main():
    """Main entry point."""
    print("🔍 GRIMOIRE Runner Coverage Analysis")
    print("=" * 40)
    
    # Change to grimoire-runner directory
    script_dir = Path(__file__).parent
    grimoire_dir = script_dir / "grimoire-runner"
    
    if grimoire_dir.exists():
        import os
        os.chdir(grimoire_dir)
        print(f"📁 Working directory: {grimoire_dir}")
    else:
        print(f"📁 Working directory: {Path.cwd()}")
    
    # Run coverage
    run_coverage()
    
    # Parse and analyze results
    coverage_data = parse_coverage_xml()
    
    if not coverage_data:
        print("❌ No coverage data found.")
        sys.exit(1)
    
    # Analyze coverage
    analyze_coverage(coverage_data)
    
    # Generate test suggestions
    generate_test_suggestions()
    
    print(f"\n✅ Analysis complete! Use './coverage.sh' to run tests with HTML output.")


if __name__ == "__main__":
    main()
