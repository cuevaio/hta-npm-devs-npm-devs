import json
from pathlib import Path

from app.main import create_app
from scripts.export_openapi import OPENAPI_PATH, render

TOOLS = ["get_fleet_overview", "get_vehicle_status", "get_trip_status", "get_fuel_analysis",
         "get_operational_bottlenecks", "get_alerts", "control_replay"]


def test_openapi_json_is_up_to_date_with_the_app():
    committed = Path(OPENAPI_PATH).read_text(encoding="utf-8")

    assert committed == render(), "El contrato cambió: corre backend/scripts/gen-api.sh y versiona el resultado"


def test_the_seven_tools_are_published_with_their_operation_id():
    spec = create_app().openapi()
    ops = {op["operationId"] for path in spec["paths"].values() for op in path.values()}

    assert set(TOOLS) <= ops


def test_protected_routes_declare_the_api_key_scheme():
    spec = create_app().openapi()

    assert spec["components"]["securitySchemes"]
    assert spec["paths"]["/v1/tools/get_alerts"]["get"]["security"]
    assert not spec["paths"]["/v1/fleet"]["get"].get("security")


def test_every_200_response_has_an_example_for_the_mock():
    spec = json.loads(Path(OPENAPI_PATH).read_text(encoding="utf-8"))
    missing = []
    for path, item in spec["paths"].items():
        for method, op in item.items():
            media = op["responses"]["200"]["content"]["application/json"]
            if "example" not in media and "examples" not in media:
                missing.append(f"{method.upper()} {path}")

    assert not missing
