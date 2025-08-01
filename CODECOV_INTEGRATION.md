# Codecov Local Integration

This document describes how we've integrated codecov CLI for enhanced local coverage analysis without uploading data to external services.

## Overview

We use codecov CLI with the `--dump` flag to provide enhanced local coverage analysis while maintaining privacy by not uploading coverage data to codecov.io.

## Features

✅ **Local Analysis Only**: No data uploaded to external services  
✅ **Enhanced Reporting**: Rich analysis beyond basic coverage.py output  
✅ **GitHub Actions Integration**: Automated analysis in CI/CD  
✅ **File-level Details**: Detailed coverage for each source file  
✅ **Branch Coverage**: Complete branch analysis with missed branches

## Usage

### Local Development

```bash
# Generate coverage data
./coverage.sh

# Run codecov analysis
codecov --file coverage.xml --dump --verbose
```

### GitHub Actions Integration

The workflow automatically:

1. Runs tests with coverage
2. Generates XML coverage report
3. Uses codecov CLI for enhanced analysis
4. Creates GitHub Actions summary
5. Uploads HTML coverage as artifact

## Configuration

### codecov CLI Installation

```bash
pip install codecov
```

### Key Flags

- `--dump`: Outputs analysis locally without upload
- `--verbose`: Provides detailed analysis output
- `--file coverage.xml`: Specifies coverage file

## Benefits of Codecov Local Analysis

1. **Enhanced File Discovery**: Automatically identifies all source files
2. **Detailed Branch Analysis**: Shows specific missed branches with line numbers
3. **Rich Debugging Info**: Git metadata and comprehensive file listing
4. **No External Dependencies**: All analysis happens locally
5. **Professional Output**: Clean, formatted coverage analysis

## Current Coverage Status

- **Total Files**: 38 analyzed
- **Line Coverage**: 29.0%
- **Branch Coverage**: 14.0%
- **Tests Passing**: 135/135

## GitHub Actions Workflow

The `.github/workflows/test-and-coverage.yml` includes:

- Codecov analysis step using `--dump` flag
- Coverage summary generation
- HTML report artifact upload
- No external service uploads

## Privacy & Security

✅ No data sent to codecov.io  
✅ All analysis performed locally  
✅ Git metadata stays local  
✅ Coverage data never leaves your infrastructure

This approach gives you the power of codecov's analysis tools while maintaining complete data privacy.
