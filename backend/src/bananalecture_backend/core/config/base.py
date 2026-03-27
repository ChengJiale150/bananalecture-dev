from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]
DEFAULT_CONFIG_FILE = ROOT_DIR / "config.yaml"
DEFAULT_ENV_FILE = ROOT_DIR / ".env"
