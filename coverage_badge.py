#!/usr/bin/env python3
"""
Generate a simple coverage badge or summary for README.
"""

import xml.etree.ElementTree as ET
from pathlib import Path


def get_coverage_percentage():
    """Extract coverage percentage from coverage.xml."""
    coverage_file = Path("coverage.xml")
    if not coverage_file.exists():
        return None
    
    try:
        tree = ET.parse(coverage_file)
        root = tree.getroot()
        
        # Find the overall coverage element
        coverage_elem = root.find(".//coverage")
        if coverage_elem is not None:
            line_rate = float(coverage_elem.get("line-rate", "0"))
            return line_rate * 100
        
        # Alternative: calculate from all classes
        total_lines = 0
        covered_lines = 0
        
        for class_elem in root.findall(".//class"):
            lines = class_elem.find("lines")
            if lines is not None:
                for line in lines.findall("line"):
                    hits = int(line.get("hits", "0"))
                    total_lines += 1
                    if hits > 0:
                        covered_lines += 1
        
        if total_lines > 0:
            return (covered_lines / total_lines) * 100
        
    except Exception as e:
        print(f"Error parsing coverage.xml: {e}")
        return None
    
    return None


def main():
    # Change to grimoire-runner directory if it exists
    grimoire_dir = Path("grimoire-runner")
    if grimoire_dir.exists():
        import os
        os.chdir(grimoire_dir)
    
    coverage = get_coverage_percentage()
    
    if coverage is None:
        print("Coverage data not available")
        return
    
    # Generate badge color based on coverage
    if coverage >= 80:
        color = "brightgreen"
    elif coverage >= 60:
        color = "green"
    elif coverage >= 40:
        color = "yellow"
    elif coverage >= 20:
        color = "orange"
    else:
        color = "red"
    
    badge_url = f"https://img.shields.io/badge/coverage-{coverage:.1f}%25-{color}"
    
    print(f"Coverage: {coverage:.1f}%")
    print(f"Badge URL: {badge_url}")
    
    # Also output for GitHub Actions
    print(f"::set-output name=coverage::{coverage:.1f}")
    print(f"::set-output name=badge_url::{badge_url}")


if __name__ == "__main__":
    main()
