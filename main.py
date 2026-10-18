
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent

# Load .env without overriding existing OS environment variables
load_dotenv(BASE_DIR / ".env", override=False)

app = FastAPI()

# Allow requests from the assignment page
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

CONFIG_KEYS = ("port", "workers", "debug", "log_level", "api_key")


def coerce(key, value):
    """Convert each configuration value to its required type."""
    if key in ("port", "workers"):
        return int(value)

    if key == "debug":
        if isinstance(value, bool):
            return value

        value = str(value).strip().lower()

        if value in ("true", "1", "yes", "on"):
            return True
        if value in ("false", "0", "no", "off"):
            return False

        raise ValueError(f"Invalid boolean value: {value}")

    return str(value)


def read_yaml():
    """Read environment-specific YAML configuration."""
    path = BASE_DIR / "config.development.yaml"

    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def effective_config(query_params):
    # Layer 1: hardcoded defaults
    config = DEFAULTS.copy()

    # Layer 2: environment-specific YAML
    yaml_config = read_yaml()
    config.update(yaml_config)

    # Layer 3: .env / environment variables
    # load_dotenv() has already loaded .env values.
    for key in CONFIG_KEYS:
        env_key = f"APP_{key.upper()}"

        if env_key in os.environ:
            config[key] = os.environ[env_key]

    # Special alias for workers
    if "NUM_WORKERS" in os.environ:
        config["workers"] = os.environ["NUM_WORKERS"]

    # Layer 4: query parameters (highest precedence)
    for key in CONFIG_KEYS:
        direct_key = key
        prefixed_key = f"set-{key}"

        # Apply the direct query parameter first
        if direct_key in query_params:
            config[key] = query_params[direct_key]

        # The set- form also works and takes precedence if both exist
        if prefixed_key in query_params:
            config[key] = query_params[prefixed_key]

    # Convert types only after all layers are merged
    for key in CONFIG_KEYS:
        config[key] = coerce(key, config[key])

    # Never expose the actual API key
    config["api_key"] = "***"

    return config


@app.get("/effective-config")
async def get_effective_config(request: Request):
    return effective_config(request.query_params)
