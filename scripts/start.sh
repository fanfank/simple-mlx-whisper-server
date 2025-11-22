#!/bin/bash
# Startup script for MLX Whisper Server

set -e

echo "🚀 Starting MLX Whisper Server..."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
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

# Check Python version
PYTHON_VERSION=$(python -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
REQUIRED_VERSION="3.12"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
    echo -e "${GREEN}✅ Python $PYTHON_VERSION detected${NC}"
else
    echo -e "${YELLOW}⚠️  Python $PYTHON_VERSION detected, but $REQUIRED_VERSION+ required${NC}"
fi

# Check if running with uv or venv
if command -v uv &> /dev/null && [ -f "uv.lock" ]; then
    echo -e "${BLUE}🔧 Using uv...${NC}"
    RUN_CMD="uv run uvicorn src.main:app --host 0.0.0.0 --port 8000"
elif command -v python &> /dev/null; then
    echo -e "${BLUE}🐍 Using standard Python...${NC}"
    RUN_CMD="uvicorn src.main:app --host 0.0.0.0 --port 8000"
else
    echo -e "${RED}❌ No suitable Python installation found${NC}"
    exit 1
fi

# Load configuration
CONFIG_FILE="config/config.yaml"
if [ -f "$CONFIG_FILE" ]; then
    echo -e "${BLUE}📋 Using configuration: $CONFIG_FILE${NC}"
fi

# Get host and port from config if available
if [ -f "$CONFIG_FILE" ] && command -v yq &> /dev/null; then
    HOST=$(yq e '.server.host // "0.0.0.0"' "$CONFIG_FILE" 2>/dev/null || echo "0.0.0.0")
    PORT=$(yq e '.server.port // "8000"' "$CONFIG_FILE" 2>/dev/null || echo "8000")
    WORKERS=$(yq e '.server.workers // "2"' "$CONFIG_FILE" 2>/dev/null || echo "2")

    RUN_CMD="uvicorn src.main:app --host $HOST --port $PORT --workers $WORKERS"
    echo -e "${BLUE}⚙️  Configuration: host=$HOST, port=$PORT, workers=$WORKERS${NC}"
fi

# Check if port is already in use
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Port 8000 is already in use.${NC}"
    echo "Please stop the existing service or change the port."
    echo ""
    echo "To kill the process using port 8000, run:"
    echo "  lsof -ti:8000 | xargs kill -9"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Starting server...${NC}"
echo ""
echo "Server will be available at:"
echo "  • http://localhost:8000"
echo "  • http://localhost:8000/health"
echo "  • http://localhost:8000/docs (API documentation)"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
exec $RUN_CMD
