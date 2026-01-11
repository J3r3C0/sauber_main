"""
Configuration for Sheratan Core v2
"""
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Data directory for JSONL storage
DATA_DIR = BASE_DIR / "data"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)
