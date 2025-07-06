#!/bin/bash
# scripts/setup_jetson.sh

echo "🤖 Setting up Disaster Response AI on Jetson Nano"

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker (if not present)
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
fi

# Install Ollama for Jetson
curl -fsSL https://ollama.ai/install.sh | sh

# Pull models (start with smaller one for Jetson Nano)
ollama pull gemma3n:2b

# Install Python dependencies
pip3 install -r requirements.txt

# Set up environment variables
export OLLAMA_HOST=0.0.0.0:11434
export OLLAMA_MODELS=/home/$USER/.ollama

echo "🎯 Jetson setup complete! Run tests with: bash scripts/run_tests.sh"