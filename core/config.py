from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Data directory for storage
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "sheratan.db"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

def _f(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))

def _i(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))

class MeshConfig:
    WEIGHT_COST = _f("MESH_WEIGHT_COST", 0.45)
    WEIGHT_REL  = _f("MESH_WEIGHT_REL", 0.40)
    WEIGHT_LAT  = _f("MESH_WEIGHT_LAT", 0.15)

    REL_MIN   = _f("MESH_REL_MIN", 0.60)
    WARMUP_N  = _i("MESH_WARMUP_N", 5)
    STALE_TTL = _i("MESH_STALE_TTL", 120)
    LAT_CAP_MS = _i("MESH_LAT_CAP_MS", 1500)

    PROBER_INTERVAL_S = _i("MESH_PROBER_INTERVAL", 30)
    PROBER_TIMEOUT_S  = _f("MESH_PROBER_TIMEOUT", 2.5)
    PROBER_FAIL_THRESHOLD = _i("MESH_PROBER_FAIL_THRESHOLD", 3)

    @classmethod
    def normalized_weights(cls):
        s = cls.WEIGHT_COST + cls.WEIGHT_REL + cls.WEIGHT_LAT
        if s <= 0:
            return (0.45, 0.40, 0.15)
        return (cls.WEIGHT_COST/s, cls.WEIGHT_REL/s, cls.WEIGHT_LAT/s)
