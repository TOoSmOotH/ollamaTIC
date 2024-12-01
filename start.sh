#!/bin/bash

# Exit on error
set -e

# Configuration
VENV_NAME="venv"
PYTHON_CMD="python3"
REQUIREMENTS_FILE="requirements.txt"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Ollama Proxy setup...${NC}"

# Check if Python 3 is installed
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo -e "${RED}Python 3 is not installed. Please install Python 3 and try again.${NC}"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_NAME" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    $PYTHON_CMD -m venv $VENV_NAME
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source "$VENV_NAME/bin/activate"

# Upgrade pip to latest version
echo -e "${YELLOW}Upgrading pip to latest version...${NC}"
python -m pip install --upgrade pip

# Install requirements with verbose output
echo -e "${YELLOW}Installing requirements...${NC}"
pip install -v -r $REQUIREMENTS_FILE

# Verify all required packages are installed
echo -e "${YELLOW}Verifying installations...${NC}"
python -c "
import importlib
required = ['fastapi', 'uvicorn', 'httpx', 'dotenv', 'pydantic', 'pydantic_settings', 'prometheus_client']
missing = []
for package in required:
    try:
        importlib.import_module(package)
    except ImportError as e:
        missing.append(package)
if missing:
    print('Missing packages:', ', '.join(missing))
    exit(1)
print('All required packages are installed')
"

# Increase file descriptor limit for the current session
# Check if running on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    # Get current limit
    current_limit=$(ulimit -n)
    desired_limit=4096
    
    if [ "$current_limit" -lt "$desired_limit" ]; then
        echo -e "${YELLOW}Attempting to increase file descriptor limit...${NC}"
        ulimit -n $desired_limit || echo -e "${RED}Warning: Could not increase file descriptor limit. You may need to run: sudo launchctl limit maxfiles 4096 unlimited${NC}"
    fi
else
    ulimit -n 4096 || echo -e "${RED}Warning: Could not increase file descriptor limit${NC}"
fi

# Kill any existing uvicorn processes
echo -e "${YELLOW}Checking for existing uvicorn processes...${NC}"
pkill -f uvicorn || true

# Start the Ollama proxy server
echo -e "${GREEN}Starting Ollama proxy server...${NC}"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
