#!/bin/bash
# Check code coverage for MLX Whisper Server

set -e

echo "📊 Checking Code Coverage for MLX Whisper Server"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found.${NC}"
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Check if pytest-cov is installed
if ! python -c "import pytest_cov" 2>/dev/null; then
    echo -e "${BLUE}📦 Installing pytest-cov...${NC}"
    pip install pytest-cov
fi

echo -e "${BLUE}▶️  Running tests with coverage...${NC}"
echo ""

# Run tests with coverage
pytest tests/ \
    --cov=src \
    --cov-report=term-missing \
    --cov-report=html:htmlcov \
    --cov-report=xml \
    --cov-fail-under=80 \
    -v

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Code coverage check passed!${NC}"
    echo ""
    echo -e "${BLUE}Coverage Reports:${NC}"
    echo "  • Terminal: Displayed above"
    echo "  • HTML: htmlcov/index.html"
    echo "  • XML: coverage.xml"
    echo ""
    echo -e "${BLUE}To view HTML report:${NC}"
    echo "  open htmlcov/index.html  # macOS"
    echo "  xdg-open htmlcov/index.html  # Linux"
    echo ""
else
    echo ""
    echo -e "${RED}❌ Code coverage check failed!${NC}"
    echo ""
    echo -e "${YELLOW}Coverage report generated at:${NC}"
    echo "  • HTML: htmlcov/index.html"
    echo "  • XML: coverage.xml"
    echo ""
    exit 1
fi
