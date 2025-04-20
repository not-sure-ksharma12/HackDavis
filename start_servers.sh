#!/bin/bash

# Activate virtual environment
source venv_new/bin/activate

# Function to check if port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        return 0
    else
        return 1
    fi
}

# Function to kill process on port
kill_port() {
    local port=$1
    if check_port $port; then
        echo "Killing process on port $port"
        kill -9 $(lsof -t -i:$port) 2>/dev/null || true
        sleep 2
    fi
}

# Clean up function
cleanup() {
    echo "Cleaning up processes..."
    kill_port 8000
    exit 0
}

# Set up trap for cleanup
trap cleanup SIGINT SIGTERM

# Kill any existing process on our port
echo "Cleaning up existing process..."
kill_port 8000

# Wait for port to clear
sleep 3

# Start the server
echo "Starting server on port 8000..."
PORT=8000 python run.py

# Keep script running
while true; do
    sleep 1
done
