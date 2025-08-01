#!/usr/bin/env python3
"""
Generate GitHub-friendly coverage reports from coverage.xml
"""

import xml.etree.ElementTree as ET
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional


def parse_coverage_xml(xml_file: Path) -> Dict:
    """Parse coverage.xml and return structured data."""
    if not xml_file.exists():
        return {}
    
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    # Get overall coverage from root element
    line_rate = float(root.get('line-rate', '0'))
    branch_rate = float(root.get('branch-rate', '0'))
    overall_coverage = line_rate * 100
    branch_coverage = branch_rate * 100
    
    # Parse packages and classes
    modules = []
    packages = root.findall('.//package')
    
    for package in packages:
        package_name = package.get('name', '')
        classes = package.findall('classes/class')
        
        for class_elem in classes:
            filename = class_elem.get('filename', '')
            if not filename.startswith('src/grimoire_runner'):
                continue
            
            # Clean up filename for display
            module_name = filename.replace('src/grimoire_runner/', '').replace('.py', '')
            
            # Get line coverage from class attributes
            class_line_rate = float(class_elem.get('line-rate', '0'))
            class_branch_rate = float(class_elem.get('branch-rate', '0'))
            
            lines = class_elem.find('lines')
            if lines is not None:
                total_lines = 0
                covered_lines = 0
                
                for line in lines.findall('line'):
                    hits = int(line.get('hits', '0'))
                    total_lines += 1
                    if hits > 0:
                        covered_lines += 1
                
                line_coverage = (covered_lines / total_lines * 100) if total_lines > 0 else 0
                
                modules.append({
                    'name': module_name,
                    'filename': filename,
                    'total_lines': total_lines,
                    'covered_lines': covered_lines,
                    'line_coverage': line_coverage,
                    'total_branches': 0,  # Will calculate if needed
                    'covered_branches': 0,
                    'branch_coverage': class_branch_rate * 100
                })
    
    return {
        'overall_coverage': overall_coverage,
        'branch_coverage': branch_coverage,
        'modules': modules
    }


def generate_github_summary(coverage_data: Dict, python_version: str) -> str:
    """Generate GitHub Actions summary markdown."""
    if not coverage_data:
        return "❌ No coverage data available"
    
    overall = coverage_data['overall_coverage']
    branch = coverage_data['branch_coverage']
    modules = coverage_data['modules']
    
    # Sort modules by coverage (lowest first)
    modules.sort(key=lambda x: x['line_coverage'])
    
    # Determine badge color
    if overall >= 80:
        color = 'brightgreen'
    elif overall >= 60:
        color = 'green'
    elif overall >= 40:
        color = 'yellow'
    elif overall >= 20:
        color = 'orange'
    else:
        color = 'red'
    
    summary = f"""## 📊 Coverage Report - Python {python_version}

![Coverage](https://img.shields.io/badge/coverage-{overall:.1f}%25-{color})

### 📈 Overall Statistics
- **Line Coverage:** {overall:.1f}%
- **Branch Coverage:** {branch:.1f}%
- **Total Modules:** {len(modules)}

### 🎯 Priority Areas (Lowest Coverage)
| Module | Lines | Coverage | Status |
|--------|-------|----------|--------|"""
    
    # Add top 10 lowest coverage modules
    for module in modules[:10]:
        status_icon = "🔴" if module['line_coverage'] == 0 else "🟠" if module['line_coverage'] < 30 else "🟡" if module['line_coverage'] < 70 else "🟢"
        summary += f"\n| `{module['name']}` | {module['covered_lines']}/{module['total_lines']} | {module['line_coverage']:.1f}% | {status_icon} |"
    
    summary += f"""

### 📊 Coverage Distribution
- 🔴 **No Coverage (0%):** {len([m for m in modules if m['line_coverage'] == 0])} modules
- 🟠 **Low Coverage (<30%):** {len([m for m in modules if 0 < m['line_coverage'] < 30])} modules  
- 🟡 **Medium Coverage (30-70%):** {len([m for m in modules if 30 <= m['line_coverage'] < 70])} modules
- 🟢 **Good Coverage (≥70%):** {len([m for m in modules if m['line_coverage'] >= 70])} modules

### 🏆 Best Covered Modules"""
    
    # Add top 5 best covered modules
    best_modules = [m for m in modules if m['line_coverage'] > 70][-5:]
    best_modules.reverse()  # Highest first
    
    for module in best_modules:
        summary += f"\n- `{module['name']}`: {module['line_coverage']:.1f}% ({module['covered_lines']}/{module['total_lines']} lines)"
    
    summary += "\n\n📁 **Download HTML Report:** Available in workflow artifacts for detailed line-by-line analysis"
    
    return summary


def generate_pr_comment(coverage_data: Dict, python_version: str) -> str:
    """Generate PR comment markdown."""
    if not coverage_data:
        return "❌ Coverage data not available"
    
    overall = coverage_data['overall_coverage']
    modules = coverage_data['modules']
    
    # Determine badge color
    if overall >= 80:
        color = 'brightgreen'
    elif overall >= 60:
        color = 'green'  
    elif overall >= 40:
        color = 'yellow'
    elif overall >= 20:
        color = 'orange'
    else:
        color = 'red'
    
    # Count modules by coverage level
    no_coverage = len([m for m in modules if m['line_coverage'] == 0])
    low_coverage = len([m for m in modules if 0 < m['line_coverage'] < 30])
    
    comment = f"""## 📊 Coverage Report - Python {python_version}

![Coverage](https://img.shields.io/badge/coverage-{overall:.1f}%25-{color})

**Overall Coverage:** {overall:.1f}%

### 🎯 Priority Areas for Testing
"""
    
    if no_coverage > 0:
        comment += f"- **{no_coverage} modules** with 0% coverage (highest priority)\n"
    if low_coverage > 0:
        comment += f"- **{low_coverage} modules** with <30% coverage\n"
    
    comment += f"""
### 📁 Reports Available
- **HTML Coverage Report**: Download from workflow artifacts
- **Detailed Analysis**: Check the "Coverage analysis" step in workflow logs

### 🔍 Quick Stats
- Total modules analyzed: {len(modules)}
- Modules needing attention: {no_coverage + low_coverage}
- Well-covered modules: {len([m for m in modules if m['line_coverage'] >= 70])}
"""
    
    return comment


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python github_coverage_report.py <action> [python_version]")
        print("Actions: summary, pr-comment")
        sys.exit(1)
    
    action = sys.argv[1]
    python_version = sys.argv[2] if len(sys.argv) > 2 else "3.11"
    
    # Look for coverage.xml in current directory
    coverage_xml = Path("coverage.xml")
    
    if not coverage_xml.exists():
        print("❌ coverage.xml not found in current directory")
        sys.exit(1)
    
    # Parse coverage data
    coverage_data = parse_coverage_xml(coverage_xml)
    
    if action == "summary":
        print(generate_github_summary(coverage_data, python_version))
    elif action == "pr-comment":
        print(generate_pr_comment(coverage_data, python_version))
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)


if __name__ == "__main__":
    main()
