"""Fail early when local SQL Server settings are incomplete or inconsistent."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def validate_environment(values: dict[str, str]) -> None:
    missing = [name for name in ("SA_PASSWORD", "SQLSERVER_PASSWORD") if not values.get(name)]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    if values.get("SQLSERVER_USER", "sa").lower() == "sa" and values["SA_PASSWORD"] != values["SQLSERVER_PASSWORD"]:
        raise ValueError("For the local Compose sa account, SA_PASSWORD and SQLSERVER_PASSWORD must match")
    try:
        port = int(values.get("SQLSERVER_PORT", "1433"))
    except ValueError as exc:
        raise ValueError("SQLSERVER_PORT must be an integer from 1 to 65535") from exc
    if not 1 <= port <= 65535:
        raise ValueError("SQLSERVER_PORT must be an integer from 1 to 65535")


def main() -> None:
    load_dotenv(ROOT / ".env")
    validate_environment(dict(os.environ))
    print("Environment configuration is valid")


if __name__ == "__main__":
    main()
