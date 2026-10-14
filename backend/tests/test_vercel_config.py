import json
from pathlib import Path


def test_vercel_services_route_api_and_spa_without_bindings():
    root = Path(__file__).resolve().parents[2]
    config = json.loads((root / "vercel.json").read_text(encoding="utf-8"))

    assert set(config["services"]) == {"app", "backend"}
    assert config["services"]["app"]["root"] == "."
    assert config["services"]["app"]["framework"] == "vite"
    assert config["services"]["backend"]["root"] == "backend"
    assert config["services"]["backend"]["entrypoint"] == "main:app"
    assert all(not service.get("bindings") for service in config["services"].values())

    rewrites = config["rewrites"]
    assert rewrites[0]["source"] == "/api/(.*)"
    assert rewrites[0]["destination"] == {"service": "backend"}
    assert rewrites[1]["source"] == "/(.*)"
    assert rewrites[1]["destination"] == {"service": "app"}
    assert config["services"]["app"]["rewrites"][0]["destination"] == "/index.html"
