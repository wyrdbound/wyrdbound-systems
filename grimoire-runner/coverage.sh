#!/bin/bash
# Coverage reporting script for GRIMOIRE Runner

set -e

echo "🧪 Running GRIMOIRE Runner test suite with coverage..."

# Change to the grimoire-runner directory
cd "$(dirname "$0")"

# Run tests with coverage
echo "Running pytest with coverage..."
python -m pytest tests/ \
    --cov=grimoire_runner \
    --cov-report=term-missing \
    --cov-report=html \
    --cov-report=xml \
    --cov-branch \
    --tb=short

echo ""
echo "📊 Coverage reports generated:"
echo "  - Terminal: (displayed above)"
echo "  - HTML: htmlcov/index.html"
echo "  - XML: coverage.xml"
echo ""

# Check if we're in a CI environment
if [ -z "$CI" ]; then
    echo "💡 To view the HTML coverage report:"
    echo "  open htmlcov/index.html"
    echo ""
    
    # Optionally open the coverage report
    if command -v open >/dev/null 2>&1; then
        read -p "Open HTML coverage report now? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            open htmlcov/index.html
        fi
    fi
fi

echo "✅ Coverage analysis complete!"
