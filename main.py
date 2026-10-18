
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent

# Load .env without overriding OS environment variables
load_dotenv(BASE_DIR / ".env", override=False)

app = FastAPI()

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
    path = BASE_DIR / "config.development.yaml"

    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def effective_config(query_params):
    # Layer 1: defaults
    config = DEFAULTS.copy()

    # Layer 2: YAML
    config.update(read_yaml())

    # Layer 3: environment variables
    for key in CONFIG_KEYS:
        env_key = f"APP_{key.upper()}"
        if env_key in os.environ:
            config[key] = os.environ[env_key]

    # NUM_WORKERS alias
    if "NUM_WORKERS" in os.environ:
        config["workers"] = os.environ["NUM_WORKERS"]

    # Layer 4: query parameters (highest precedence)
    for param, value in query_params.multi_items():
        if param == "set":
            # Supports repeated parameters: ?set=workers=16&set=port=8195
            if "=" in value:
                key, override_value = value.split("=", 1)
                if key in CONFIG_KEYS:
                    config[key] = override_value

        elif param.startswith("set-"):
            # Supports ?set-workers=16
            key = param[4:]
            if key in CONFIG_KEYS:
                config[key] = value

        elif param in CONFIG_KEYS:
            # Supports ?workers=16
            config[param] = value

    # Convert types after merging all layers
    for key in CONFIG_KEYS:
        config[key] = coerce(key, config[key])

    # Mask secret
    config["api_key"] = "***"

    return config


@app.get("/effective-config")
async def get_effective_config(request: Request):
    return effective_config(request.query_params)
