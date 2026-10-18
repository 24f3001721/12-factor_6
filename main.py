import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent

# Load .env values without overriding existing OS environment variables.
load_dotenv(BASE_DIR / ".env", override=False)

app = FastAPI()

# The assignment requires browser requests from the assignment page to work.
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


def as_bool(value):
    if isinstance(value, bool):
        return value
    if str(value).strip().lower() in ("true", "1", "yes", "on"):
        return True
    if str(value).strip().lower() in ("false", "0", "no", "off"):
        return False
    raise ValueError(f"Invalid boolean value: {value}")


def coerce(key, value):
    if key in ("port", "workers"):
        return int(value)
    if key == "debug":
        return as_bool(value)
    return str(value)


def read_yaml():
    path = BASE_DIR / "config.development.yaml"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def effective_config(query_params):
    # Lowest to highest precedence.
    config = DEFAULTS.copy()
    config.update(read_yaml())

    # .env values are loaded into os.environ by load_dotenv.
    for key in ("port", "workers", "debug", "log_level", "api_key"):
        env_key = f"APP_{key.upper()}"
        if env_key in os.environ:
            config[key] = os.environ[env_key]

    # Special alias required by the assignment.
    if "NUM_WORKERS" in os.environ:
        config["workers"] = os.environ["NUM_WORKERS"]

    # CLI/query parameters have the highest precedence.
    for key in ("port", "workers", "debug", "log_level", "api_key"):
        if key in query_params:
            config[key] = query_params[key]

    # Convert values to their required types.
    for key in ("port", "workers", "debug", "log_level", "api_key"):
        config[key] = coerce(key, config[key])

    # Never expose the actual secret.
    config["api_key"] = "***"
    return config


@app.get("/effective-config")
async def get_effective_config(request: Request):
    return effective_config(request.query_params)
