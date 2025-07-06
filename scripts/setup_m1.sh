#!/bin/bash
echo "🚀 Setting up Disaster Response AI on MacBook M1"

# Install Ollama (correct method for M1 Macs)
if ! command -v ollama &> /dev/null; then
    echo "Installing Ollama..."
    cd /tmp
    curl -L https://ollama.com/download/Ollama-darwin.zip -o Ollama-darwin.zip
    unzip Ollama-darwin.zip
    sudo mv Ollama.app /Applications/
    sudo ln -sf /Applications/Ollama.app/Contents/Resources/ollama /usr/local/bin/ollama
    cd -
    echo "Ollama installed. Starting service..."
fi

# Start Ollama service
/Applications/Ollama.app/Contents/MacOS/Ollama &
sleep 5

# Pull Gemma models (using correct model names)
echo "Pulling Gemma models..."
ollama pull gemma:2b
ollama pull gemma:7b

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

# Create necessary directories
mkdir -p data/rescuenet data/sample_images temp results

echo "Setup complete! Run 'python src/api/app.py' to start development server"