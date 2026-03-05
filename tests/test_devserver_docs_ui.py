import pytest


pytest.importorskip("fastapi")

from ai_orchestrator.devserver.app import (
    DocsConcatRequest,
    api_docs,
    app,
    docs_catalog,
    docs_concat,
    docs_page,
    home,
    internal_swagger,
)
from fastapi import HTTPException


def _html(response) -> str:
    return response.body.decode("utf-8")


def _route_map() -> dict[str, set[str]]:
    mapping: dict[str, set[str]] = {}
    for route in app.routes:
        methods = getattr(route, "methods", None)
        if methods is not None:
            mapping[route.path] = methods
    return mapping


def test_nav_links_present_on_home_docs_and_api_docs():
    for view in [home, docs_page, api_docs]:
        response = view()
        assert response.status_code == 200
        html = _html(response)
        assert 'href="/"' in html
        assert 'href="/docs"' in html
        assert 'href="/api-docs"' in html


def test_docs_catalog_shape_and_sorted_order():
    payload = docs_catalog()
    assert set(payload.keys()) == {"folders", "root_files"}

    folder_labels = [folder["label"] for folder in payload["folders"]]
    assert folder_labels == sorted(folder_labels)

    for folder in payload["folders"]:
        assert folder["id"].startswith("folder:")
        assert folder["kind"] == "folder"
        assert isinstance(folder["children"], list)

        child_labels = [child["label"] for child in folder["children"]]
        assert child_labels == sorted(child_labels)

        for child in folder["children"]:
            assert child["kind"] == "file"
            assert child["id"].startswith("doc:")

    root_labels = [root_file["label"] for root_file in payload["root_files"]]
    assert root_labels == sorted(root_labels)
    for root_file in payload["root_files"]:
        assert root_file["kind"] == "file"
        assert root_file["id"].startswith("doc:")


def test_docs_page_contains_controls_and_checkbox_templates():
    response = docs_page()
    assert response.status_code == 200

    html = _html(response)
    assert "Expand all" in html
    assert "Collapse all" in html
    assert "Clear selection" in html
    assert "Copy to Clipboard" in html
    assert 'id="docs-tree"' in html
    assert 'id="markdown-output"' in html
    assert 'class="folder-checkbox"' in html
    assert 'class="file-checkbox"' in html


def test_docs_page_contains_responsive_layout_markers():
    html = _html(docs_page())
    assert "grid-template-columns:minmax(260px, 32%) minmax(0, 1fr)" in html
    assert "@media (max-width: 900px)" in html


def test_docs_concat_empty_selection_returns_empty_markdown():
    response = docs_concat(DocsConcatRequest(selected_file_ids=[]))
    assert response == {"markdown": ""}


def test_docs_concat_preserves_order_separator_and_path_headers():
    catalog = docs_catalog()
    all_ids = []
    for folder in catalog["folders"]:
        all_ids.extend(child["id"] for child in folder["children"])
    all_ids.extend(root_file["id"] for root_file in catalog["root_files"])
    assert len(all_ids) >= 2

    selected = [all_ids[1], all_ids[0]]
    response = docs_concat(DocsConcatRequest(selected_file_ids=selected))
    markdown = response["markdown"]

    first_marker = f"Path: docs/{selected[0].removeprefix('doc:')}"
    second_marker = f"Path: docs/{selected[1].removeprefix('doc:')}"

    assert first_marker in markdown
    assert second_marker in markdown
    assert markdown.index(first_marker) < markdown.index(second_marker)
    assert markdown.count("\n\n---\n\n") == 1


def test_docs_concat_unknown_id_returns_400():
    with pytest.raises(HTTPException) as exc_info:
        docs_concat(DocsConcatRequest(selected_file_ids=["doc:00_overview/system_vision.md", "doc:missing.md"]))

    assert exc_info.value.status_code == 400
    assert "Unknown document IDs" in exc_info.value.detail
    assert "doc:missing.md" in exc_info.value.detail


def test_api_docs_route_compatibility_and_endpoints_retirement():
    routes = _route_map()

    assert "/api-docs" in routes
    assert "GET" in routes["/api-docs"]

    assert "/_swagger" in routes
    assert "GET" in routes["/_swagger"]

    assert "/endpoints" not in routes

    swagger_response = internal_swagger()
    assert swagger_response.status_code == 200
