#!/bin/bash
# Test runner script for MLX Whisper Server

set -e

echo "🧪 Running MLX Whisper Server Test Suite"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found.${NC}"
    echo "Please run setup.sh first or create a virtual environment."
    exit 1
fi

# Activate virtual environment
echo -e "${BLUE}📦 Activating virtual environment...${NC}"
source .venv/bin/activate

# Determine which test runner to use
if command -v pytest &> /dev/null; then
    TEST_RUNNER="pytest"
elif python -m pytest --version &> /dev/null; then
    TEST_RUNNER="python -m pytest"
else
    echo -e "${RED}❌ pytest not found. Please install test dependencies.${NC}"
    exit 1
fi

# Parse command line arguments
COVERAGE=""
PERFORMANCE=""
VERBOSE=""
TEST_PATH="tests/"

while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage)
            COVERAGE="--cov=src --cov-report=html --cov-report=term-missing"
            shift
            ;;
        --performance)
            PERFORMANCE="-m performance"
            shift
            ;;
        --benchmark)
            PERFORMANCE="-m benchmark"
            shift
            ;;
        --verbose|-v)
            VERBOSE="-v"
            shift
            ;;
        --unit)
            TEST_PATH="tests/unit/"
            shift
            ;;
        --integration)
            TEST_PATH="tests/integration/"
            shift
            ;;
        --contract)
            TEST_PATH="tests/contract/"
            shift
            ;;
        --performance-tests)
            TEST_PATH="tests/performance/"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --coverage       Run tests with coverage report"
            echo "  --performance    Run performance tests only"
            echo "  --benchmark      Run benchmark tests only"
            echo "  --verbose        Verbose output"
            echo "  --unit           Run unit tests only"
            echo "  --integration    Run integration tests only"
            echo "  --contract       Run contract tests only"
            echo "  --performance-tests    Run performance test suite only"
            echo "  --help           Show this help message"
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Print test configuration
echo -e "${BLUE}Test Configuration:${NC}"
echo "  Test runner: $TEST_RUNNER"
echo "  Test path: $TEST_PATH"
echo "  Coverage: ${COVERAGE:-disabled}"
echo "  Performance: ${PERFORMANCE:-disabled}"
echo ""

# Check if pytest plugins are available
if [ -n "$COVERAGE" ]; then
    echo -e "${BLUE}📊 Coverage report enabled${NC}"
    if ! python -c "import pytest_cov" 2>/dev/null; then
        echo -e "${YELLOW}⚠️  pytest-cov not installed. Installing...${NC}"
        pip install pytest-cov
    fi
fi

# Run tests based on configuration
echo -e "${GREEN}▶️  Running tests...${NC}"
echo ""

if [ -n "$PERFORMANCE" ]; then
    echo -e "${YELLOW}⚡ Running performance tests${NC}"
    $TEST_RUNNER $TEST_PATH -m performance $VERBOSE --tb=short
elif [ -n "$COVERAGE" ]; then
    echo -e "${YELLOW}📊 Running tests with coverage${NC}"
    $TEST_RUNNER $TEST_PATH $COVERAGE $VERBOSE --tb=short
else
    echo -e "${BLUE}🧪 Running all tests${NC}"
    $TEST_RUNNER $TEST_PATH $VERBOSE --tb=short
fi

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ All tests passed!${NC}"
    echo ""

    # Show coverage report if enabled
    if [ -n "$COVERAGE" ]; then
        echo -e "${BLUE}📊 Coverage report generated in htmlcov/index.html${NC}"
    fi

    # Show test results summary
    echo -e "${BLUE}Test Summary:${NC}"
    echo "  • Unit tests: tests/unit/"
    echo "  • Integration tests: tests/integration/"
    echo "  • Contract tests: tests/contract/"
    echo "  • Performance tests: tests/performance/"
    echo ""
    echo "For more options, run: $0 --help"
else
    echo ""
    echo -e "${RED}❌ Some tests failed${NC}"
    echo ""
    echo "Common solutions:"
    echo "  • Check error messages above"
    echo "  • Ensure all dependencies are installed"
    echo "  • Verify test fixtures are present"
    echo "  • Check configuration in config/config.yaml"
    exit 1
fi
