import ast
from pathlib import Path

from pytest_archon import archrule


def test_api_layer_dependencies():
    """Ensure API layer stays independent from the app entrypoint."""
    (
        archrule("API layer dependencies")
        .match("bananalecture_backend.api.*")
        .should_not_import("bananalecture_backend.main")
        .check("bananalecture_backend")
    )


def test_service_layer_dependencies():
    """Ensure service resources do not depend on API or application use cases."""
    (
        archrule("Service layer dependencies")
        .match("bananalecture_backend.services.resources.*")
        .should_not_import("bananalecture_backend.api.*")
        .should_not_import("bananalecture_backend.application.use_cases.*")
        .check("bananalecture_backend")
    )


def test_application_layer_dependencies():
    """Ensure use cases stay independent from the API layer."""
    (
        archrule("Application layer dependencies")
        .match("bananalecture_backend.application.use_cases.*")
        .should_not_import("bananalecture_backend.api.*")
        .check("bananalecture_backend")
    )


def test_api_layer_uses_services_not_clients_or_infrastructure() -> None:
    """Ensure endpoint modules do not directly import clients or infrastructure."""
    endpoints_dir = Path(__file__).resolve().parents[2] / "src" / "bananalecture_backend" / "api" / "v1" / "endpoints"

    for endpoint_file in endpoints_dir.glob("*.py"):
        tree = ast.parse(endpoint_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                assert not node.module.startswith("bananalecture_backend.clients")
                assert not node.module.startswith("bananalecture_backend.infrastructure")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("bananalecture_backend.clients")
                    assert not alias.name.startswith("bananalecture_backend.infrastructure")


def test_clients_layer_dependencies():
    """Ensure clients stay isolated from business and persistence layers."""
    (
        archrule("Clients layer dependencies")
        .match("bananalecture_backend.clients.*")
        .should_not_import("bananalecture_backend.api.*")
        .should_not_import("bananalecture_backend.db.*")
        .should_not_import("bananalecture_backend.models.*")
        .should_not_import("bananalecture_backend.infrastructure.*")
        .check("bananalecture_backend")
    )


def test_infrastructure_layer_dependencies():
    """Ensure infrastructure stays isolated from business and persistence layers."""
    (
        archrule("Infrastructure layer dependencies")
        .match("bananalecture_backend.infrastructure.*")
        .should_not_import("bananalecture_backend.api.*")
        .should_not_import("bananalecture_backend.db.*")
        .should_not_import("bananalecture_backend.models.*")
        .should_not_import("bananalecture_backend.services.*")
        .check("bananalecture_backend")
    )


def test_db_layer_dependencies():
    """Ensure DB layer only depends on models and core."""
    (
        archrule("DB layer dependencies")
        .match("bananalecture_backend.db*")
        .should_not_import("bananalecture_backend.api.*")
        .should_not_import("bananalecture_backend.services.*")
        .should_not_import("bananalecture_backend.application.*")
        .check("bananalecture_backend")
    )


def test_models_layer_dependencies():
    """Ensure Models layer is independent of services and api."""
    (
        archrule("Models layer dependencies")
        .match("bananalecture_backend.models*")
        .should_not_import("bananalecture_backend.api.*")
        .should_not_import("bananalecture_backend.services.*")
        .should_not_import("bananalecture_backend.application.*")
        .check("bananalecture_backend")
    )


def test_core_layer_dependencies():
    """Ensure Core layer is independent of all other project layers."""
    (
        archrule("Core layer dependencies")
        .match("bananalecture_backend.core*")
        .should_not_import("bananalecture_backend.api.*")
        .should_not_import("bananalecture_backend.services.*")
        .should_not_import("bananalecture_backend.application.*")
        .should_not_import("bananalecture_backend.db.*")
        .should_not_import("bananalecture_backend.models.*")
        .check("bananalecture_backend")
    )


def test_no_test_imports_in_production():
    """Ensure production code does not import from tests."""
    (
        archrule("No test imports in production")
        .match("bananalecture_backend.*")
        .should_not_import("tests.*")
        .check("bananalecture_backend")
    )


def test_services_directory_only_contains_core_services() -> None:
    """Ensure mixed workflow/media implementations moved out of services stay out."""
    services_dir = Path(__file__).resolve().parents[2] / "src" / "bananalecture_backend" / "services"
    forbidden_files = {
        "image.py",
        "audio.py",
        "video.py",
        "workflows.py",
        "dialogues.py",
        "slides.py",
        "projects.py",
        "tasks.py",
    }
    existing_forbidden = {path.name for path in services_dir.iterdir() if path.name in forbidden_files}
    assert existing_forbidden == set()


def test_application_layers_do_not_call_module_builders() -> None:
    """Ensure use cases and resource services do not build upstream dependencies directly."""
    target_dirs = [
        Path(__file__).resolve().parents[2] / "src" / "bananalecture_backend" / "application",
        Path(__file__).resolve().parents[2] / "src" / "bananalecture_backend" / "services" / "resources",
    ]

    for directory in target_dirs:
        for source_file in directory.rglob("*.py"):
            tree = ast.parse(source_file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module is not None:
                    for alias in node.names:
                        assert not alias.name.startswith("build_")
