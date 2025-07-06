# config/production.py
import os


class ProductionConfig:
    OLLAMA_HOST = "0.0.0.0:11434"
    MODEL = "gemma3n:2b"  # Optimized for Jetson Nano
    MAX_WORKERS = 2       # Conservative for Jetson
    TIMEOUT = 120         # Longer timeout for edge hardware
    LOG_LEVEL = "INFO"

    # Performance optimizations for Jetson
    BATCH_SIZE = 1
    CONCURRENT_REQUESTS = 2
    MEMORY_LIMIT = "6GB"
