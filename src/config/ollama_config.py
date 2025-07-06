# // config/ollama_config.json
OLLAMA_CONFIG = {
    "default": {
        "base_url": "http://localhost:11434",
        "model": "gemma3n:2b",
        "timeout": 60
    },
    "macos": {
        "base_url": "http://localhost:11434",
        "model": "gemma3n:4b",
        "timeout": 30,
        "performance_mode": "high"
    },
    "linux": {
        "base_url": "http://localhost:11434",
        "model": "gemma3n:2b",
        "timeout": 120,
        "performance_mode": "efficient"
    }
}