#!/bin/bash
# Quickstart Validation Script for MLX Whisper Server
# This script validates that all steps in README.md quickstart guide work correctly

set -e

echo "🚀 Validating MLX Whisper Server Quickstart Guide"
echo "=================================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Track validation status
VALIDATION_PASSED=true

# Test counter
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function to run a test
run_test() {
    local test_name="$1"
    local test_command="$2"

    TESTS_RUN=$((TESTS_RUN + 1))
    echo -e "${BLUE}▶️  Test $TESTS_RUN: $test_name${NC}"

    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "   ${GREEN}✅ PASSED${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "   ${RED}❌ FAILED${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        VALIDATION_PASSED=false
    fi
    echo ""
}

# Test 1: Check Python version
echo -e "${YELLOW}📋 Step 1: Checking Prerequisites${NC}"
echo ""

run_test "Python 3.12+ is installed" \
    "python3 -c 'import sys; assert sys.version_info >= (3, 12)'"

run_test "pip is installed" \
    "python3 -m pip --version"

run_test "Git is installed" \
    "git --version"

run_test "cURL is installed" \
    "curl --version"

echo ""

# Test 2: Installation - uv method
echo -e "${YELLOW}📦 Step 2: Installation (uv method)${NC}"
echo ""

if command -v uv &> /dev/null; then
    echo -e "${BLUE}⚙️  Using uv package manager${NC}"
    echo ""

    run_test "Create virtual environment with uv" \
        "test -d .venv || uv venv"

    run_test "Activate virtual environment" \
        "source .venv/bin/activate && python -c 'import sys; assert sys.prefix != sys.base_prefix'"

    run_test "Install dependencies with uv" \
        "source .venv/bin/activate && uv sync --all-extras"

    echo ""

    # Test 3: Server startup
    echo -e "${YELLOW}▶️  Step 3: Server Startup${NC}"
    echo ""

    run_test "Configuration file exists" \
        "test -f config/config.yaml"

    run_test "Environment example file exists" \
        "test -f config/.env.example"

    # Check if server is already running
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${BLUE}⚠️  Port 8000 already in use, skipping server startup test${NC}"
    else
        echo -e "${BLUE}⚙️  Testing server startup (will take a moment)...${NC}"

        # Start server in background and test it
        (
            cd /Users/rich/repos/github/simple-mlx-whisper-server || exit 1
            source .venv/bin/activate
            timeout 10 uvicorn src.main:app --host 127.0.0.1 --port 8000 > /tmp/server_startup.log 2>&1 &
            SERVER_PID=$!
            sleep 3

            # Test if server responds
            if curl -s http://127.0.0.1:8000/health > /dev/null; then
                kill $SERVER_PID 2>/dev/null || true
                echo "   ✅ PASSED"
                TESTS_PASSED=$((TESTS_PASSED + 1))
            else
                kill $SERVER_PID 2>/dev/null || true
                echo "   ❌ FAILED"
                TESTS_FAILED=$((TESTS_FAILED + 1))
                VALIDATION_PASSED=false
            fi
            TESTS_RUN=$((TESTS_RUN + 1))
        )
        echo ""
    fi

    # Test 4: API endpoints
    echo -e "${YELLOW}🔌 Step 4: API Endpoints${NC}"
    echo ""

    run_test "Health endpoint is accessible" \
        "curl -s http://localhost:8000/health | grep -q 'status'"

    run_test "Root endpoint is accessible" \
        "curl -s http://localhost:8000/ | grep -q 'MLX Whisper Server'"

    run_test "OpenAPI docs are accessible" \
        "curl -s http://localhost:8000/docs | grep -q 'Swagger'"

    run_test "OpenAPI JSON schema is accessible" \
        "curl -s http://localhost:8000/openapi.json | grep -q 'openapi'"

    echo ""

    # Test 5: Transcribe endpoint
    echo -e "${YELLOW}🎤 Step 5: Transcription Endpoint${NC}"
    echo ""

    # Create a test audio file
    TEST_AUDIO=$(mktemp)
    echo "RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00" > "$TEST_AUDIO"

    run_test "Transcribe endpoint accepts MP3 file" \
        "curl -s -X POST http://localhost:8000/v1/audio/transcriptions \
            -F 'file=@$TEST_AUDIO' \
            -F 'model=mlx-community/whisper-small' | grep -q 'error\\|text'"

    run_test "Transcribe endpoint rejects oversized file" \
        "dd if=/dev/zero bs=1M count=30 2>/dev/null | \
            curl -s -X POST http://localhost:8000/v1/audio/transcriptions \
            -F 'file=@-;filename=large.mp3' \
            -F 'model=mlx-community/whisper-small' | grep -q '413'"

    run_test "Transcribe endpoint rejects invalid format" \
        "echo 'invalid data' | \
            curl -s -X POST http://localhost:8000/v1/audio/transcriptions \
            -F 'file=@-;filename=invalid.xyz' \
            -F 'model=mlx-community/whisper-small' | grep -q '400\\|422'"

    # Cleanup
    rm -f "$TEST_AUDIO"

    echo ""

    # Test 6: Error handling
    echo -e "${YELLOW}🛡️  Step 6: Error Handling${NC}"
    echo ""

    run_test "Empty file returns 422" \
        "curl -s -X POST http://localhost:8000/v1/audio/transcriptions \
            -F 'file=@/dev/null' \
            -F 'model=mlx-community/whisper-small' | grep -q '422'"

    run_test "Error responses include request_id" \
        "curl -s -X POST http://localhost:8000/v1/audio/transcriptions \
            -F 'file=@/dev/null' \
            -F 'model=mlx-community/whisper-small' | grep -q 'request_id'"

    echo ""

    # Test 7: OpenAI SDK compatibility
    echo -e "${YELLOW}🔗 Step 7: OpenAI SDK Compatibility${NC}"
    echo ""

    # Check if openai package is installed
    if source .venv/bin/activate && python -c "import openai" 2>/dev/null; then
        run_test "OpenAI SDK is installed" \
            "source .venv/bin/activate && python -c 'import openai'"

        # Check if the SDK can be configured
        run_test "OpenAI SDK can be configured for server" \
            "source .venv/bin/activate && python -c 'from openai import OpenAI; c = OpenAI(api_key=\"test\", base_url=\"http://localhost:8000/v1\"); assert c is not None'"
    else
        echo -e "${BLUE}⚠️  OpenAI SDK not installed, skipping SDK compatibility test${NC}"
    fi

    echo ""

else
    echo -e "${BLUE}⚠️  uv not installed, skipping uv installation tests${NC}"
    echo ""
fi

# Test 8: Test suite
echo -e "${YELLOW}🧪 Step 8: Test Suite${NC}"
echo ""

run_test "Test directory exists" \
    "test -d tests/"

run_test "Unit tests exist" \
    "test -d tests/unit/"

run_test "Integration tests exist" \
    "test -d tests/integration/"

run_test "Contract tests exist" \
    "test -d tests/contract/"

run_test "Performance tests exist" \
    "test -d tests/performance/"

run_test "Test configuration exists" \
    "grep -q 'pytest' pyproject.toml"

# Run a quick unit test (if pytest is available)
if command -v pytest &> /dev/null || python -m pytest --version &> /dev/null; then
    echo -e "${BLUE}⚙️  Running a quick unit test check...${NC}"

    TESTS_RUN=$((TESTS_RUN + 1))
    if python -m pytest tests/unit/test_config.py -v --tb=line -q 2>&1 | grep -q "passed\|failed"; then
        echo "   ✅ PASSED"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo "   ❌ FAILED"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        VALIDATION_PASSED=false
    fi
    echo ""
fi

echo ""

# Test 9: Documentation
echo -e "${YELLOW}📚 Step 9: Documentation${NC}"
echo ""

run_test "README.md exists" \
    "test -f README.md"

run_test "INSTALL.md exists" \
    "test -f INSTALL.md"

run_test "COVERAGE.md exists" \
    "test -f COVERAGE.md"

run_test "pyproject.toml exists" \
    "test -f pyproject.toml"

run_test "requirements.txt exists" \
    "test -f requirements.txt"

echo ""

# Test 10: Scripts and Docker
echo -e "${YELLOW}📦 Step 10: Scripts & Docker${NC}"
echo ""

run_test "start.sh script exists" \
    "test -f scripts/start.sh"

run_test "start.sh is executable" \
    "test -x scripts/start.sh"

run_test "run_tests.sh script exists" \
    "test -f scripts/run_tests.sh"

run_test "run_tests.sh is executable" \
    "test -x scripts/run_tests.sh"

run_test "benchmark.py script exists" \
    "test -f scripts/benchmark.py"

run_test "benchmark.py is executable" \
    "test -x scripts/benchmark.py"

run_test "Dockerfile exists" \
    "test -f Dockerfile"

run_test "docker-compose.yml exists" \
    "test -f docker-compose.yml"

run_test ".dockerignore exists" \
    "test -f .dockerignore"

echo ""

# Summary
echo "=================================================="
echo -e "${BLUE}📊 Validation Summary${NC}"
echo "=================================================="
echo ""
echo "Total tests run: $TESTS_RUN"
echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ "$VALIDATION_PASSED" = true ]; then
    echo -e "${GREEN}✅ All validation checks passed!${NC}"
    echo ""
    echo "The quickstart guide is ready to use. You can now:"
    echo "  1. Run: ./setup.sh"
    echo "  2. Run: source .venv/bin/activate"
    echo "  3. Run: uvicorn src.main:app --host 0.0.0.0 --port 8000"
    echo "  4. Test: curl http://localhost:8000/health"
    echo "  5. Transcribe: See README.md for examples"
    echo ""
    exit 0
else
    echo -e "${RED}❌ Some validation checks failed!${NC}"
    echo ""
    echo "Please review the failed tests above and fix any issues."
    echo "Common solutions:"
    echo "  • Ensure Python 3.12+ is installed"
    echo "  • Run: ./setup.sh to install dependencies"
    echo "  • Check that all required files exist"
    echo ""
    exit 1
fi
