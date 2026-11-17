import os
import sys
from pathlib import Path

os.environ.setdefault("OFFLINE_MODE", "true")
os.environ.setdefault("API_KEY", "test-key")
os.environ.setdefault("DB_PATH", "data/test_results.db")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
