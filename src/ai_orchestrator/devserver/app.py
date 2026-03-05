from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import uvicorn


DOCS_ROOT_DIR = "docs"
FOLDER_STATE_STORAGE_KEY = "app.docs.folderState.v1"


class StartCommandRequest(BaseModel):
    """Input contract for `ai-orchestrator start`."""

    config: str = Field(description="Path to the YAML config passed via --config.")
    models: list[str] = Field(description="Model plugin names passed via --models.")


class StartCommandOutput(BaseModel):
    """Output contract for `ai-orchestrator start`."""

    instance_id: str
    gpu_type: str | None = Field(default=None, description="GPU model selected by provider.")
    cost_per_hour: float | None = Field(default=None, description="Hourly instance cost.")
    idle_timeout: int
    snapshot_version: str
    deepseek_url: str
    whisper_url: str


class DocsConcatRequest(BaseModel):
    selected_file_ids: list[str] = Field(default_factory=list)


app = FastAPI(
    title="ai-orchestrator Dev Docs",
    description=(
        "Development-only API docs for the ai-orchestrator CLI contract. "
        "This server does not execute orchestration runtime logic."
    ),
    docs_url=None,
    redoc_url=None,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _docs_root() -> Path:
    return _repo_root() / DOCS_ROOT_DIR


def _doc_id(relative_path: Path) -> str:
    return f"doc:{relative_path.as_posix()}"


def _docs_catalog() -> dict[str, list[dict[str, object]]]:
    docs_root = _docs_root()
    folders: list[dict[str, object]] = []
    root_files: list[dict[str, str]] = []

    if not docs_root.exists() or not docs_root.is_dir():
        return {"folders": folders, "root_files": root_files}

    folder_paths = sorted((path for path in docs_root.iterdir() if path.is_dir()), key=lambda path: path.name)
    for folder_path in folder_paths:
        children: list[dict[str, str]] = []
        for file_path in sorted(folder_path.glob("*.md"), key=lambda path: path.name):
            relative_path = file_path.relative_to(docs_root)
            children.append(
                {
                    "id": _doc_id(relative_path),
                    "label": file_path.name,
                    "kind": "file",
                }
            )
        folders.append(
            {
                "id": f"folder:{folder_path.name}",
                "label": folder_path.name,
                "kind": "folder",
                "children": children,
            }
        )

    for file_path in sorted(docs_root.glob("*.md"), key=lambda path: path.name):
        relative_path = file_path.relative_to(docs_root)
        root_files.append(
            {
                "id": _doc_id(relative_path),
                "label": file_path.name,
                "kind": "file",
            }
        )

    return {"folders": folders, "root_files": root_files}


def _docs_index() -> dict[str, Path]:
    docs_root = _docs_root()
    index: dict[str, Path] = {}
    catalog = _docs_catalog()

    for folder in catalog["folders"]:
        for child in folder["children"]:
            relative_path = Path(child["id"].removeprefix("doc:"))
            index[child["id"]] = docs_root / relative_path

    for root_file in catalog["root_files"]:
        relative_path = Path(root_file["id"].removeprefix("doc:"))
        index[root_file["id"]] = docs_root / relative_path

    return index


def _render_nav(active: str) -> str:
    links = [
        ("/", "Home", "home"),
        ("/docs", "Documentation", "docs"),
        ("/api-docs", "API Reference", "api-docs"),
    ]
    anchors: list[str] = []
    for href, label, key in links:
        active_class = "nav-link active" if active == key else "nav-link"
        anchors.append(f'<a class="{active_class}" href="{href}">{label}</a>')
    return "".join(anchors)


def _render_page(title: str, active_nav: str, body: str) -> HTMLResponse:
    nav = _render_nav(active_nav)
    html = f"""<!DOCTYPE html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>{title}</title>
    <style>
      :root {{
        --bg: #f6f9fc;
        --ink: #1f2937;
        --muted: #6b7280;
        --panel: #ffffff;
        --line: #d1d5db;
        --accent: #0f766e;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        background: var(--bg);
        color: var(--ink);
        font-family: "Source Sans 3", "Segoe UI", sans-serif;
      }}
      .top-nav {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.75rem 1rem;
        background: linear-gradient(120deg, #0f172a, #1f2937);
        border-bottom: 1px solid #111827;
      }}
      .brand {{
        color: #f9fafb;
        font-weight: 700;
        letter-spacing: 0.02em;
      }}
      .nav-links {{
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
      }}
      .nav-link {{
        color: #d1d5db;
        text-decoration: none;
        padding: 0.4rem 0.6rem;
        border-radius: 0.45rem;
        border: 1px solid transparent;
      }}
      .nav-link:hover {{
        color: #ffffff;
        border-color: #4b5563;
      }}
      .nav-link.active {{
        color: #ffffff;
        border-color: #0ea5a5;
        background: rgba(15, 118, 110, 0.2);
      }}
      main {{
        max-width: 1200px;
        margin: 0 auto;
        padding: 1rem;
      }}
      .panel {{
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 0.75rem;
        padding: 1rem;
      }}
      .button-link,
      button {{
        border: 1px solid #0f766e;
        background: #0f766e;
        color: #ffffff;
        border-radius: 0.45rem;
        padding: 0.45rem 0.7rem;
        cursor: pointer;
        text-decoration: none;
        font-size: 0.95rem;
      }}
      .button-link.secondary,
      button.secondary {{
        background: #ffffff;
        color: #0f766e;
      }}
      button:disabled {{
        opacity: 0.65;
        cursor: not-allowed;
      }}
      .status {{
        color: var(--muted);
        min-height: 1.2rem;
      }}
      .sr-only {{
        border: 0;
        clip: rect(0 0 0 0);
        height: 1px;
        margin: -1px;
        overflow: hidden;
        padding: 0;
        position: absolute;
        width: 1px;
      }}
    </style>
  </head>
  <body>
    <header class=\"top-nav\">
      <div class=\"brand\">ai-orchestrator Dev Docs</div>
      <nav class=\"nav-links\">{nav}</nav>
    </header>
    <main>{body}</main>
  </body>
</html>
"""
    return HTMLResponse(html)


@app.get("/", response_class=HTMLResponse, tags=["ui"], summary="Home")
def home() -> HTMLResponse:
    body = """
<section class="panel">
  <h1>ai-orchestrator Dev Documentation</h1>
  <p>Local documentation workspace for browsing docs files and API contracts.</p>
  <div style="display:flex; gap:0.75rem; flex-wrap:wrap; margin-top:0.5rem;">
    <a class="button-link" href="/docs">Documentation</a>
    <a class="button-link secondary" href="/api-docs">API Reference</a>
  </div>
</section>
"""
    return _render_page("ai-orchestrator Dev Docs", "home", body)


@app.get("/api-docs", response_class=HTMLResponse, tags=["ui"], summary="API Reference")
def api_docs() -> HTMLResponse:
    body = """
<section class="panel">
  <h1>API Reference</h1>
  <p>OpenAPI/Swagger reference for the dev documentation server.</p>
  <iframe
    title="ai-orchestrator api reference"
    src="/_swagger"
    style="width:100%; min-height:78vh; border:1px solid #d1d5db; border-radius:0.5rem;"
  ></iframe>
</section>
"""
    return _render_page("API Reference", "api-docs", body)


@app.get("/_swagger", include_in_schema=False)
def internal_swagger() -> HTMLResponse:
    openapi_url = app.openapi_url or "/openapi.json"
    return get_swagger_ui_html(openapi_url=openapi_url, title="ai-orchestrator Swagger UI")


@app.get("/docs", response_class=HTMLResponse, tags=["ui"], summary="Documentation")
def docs_page() -> HTMLResponse:
    body = f"""
<section class="panel">
  <h1>Documentation Builder</h1>
  <p>Select markdown files from the repository docs tree and generate concatenated markdown.</p>
</section>

<section class="docs-layout" style="margin-top:1rem; display:grid; grid-template-columns:minmax(260px, 32%) minmax(0, 1fr); gap:1rem;">
  <article class="panel" id="docs-left-pane">
    <div class="docs-toolbar" style="display:flex; gap:0.5rem; flex-wrap:wrap; margin-bottom:0.75rem;">
      <button id="expand-all" type="button" class="secondary">Expand all</button>
      <button id="collapse-all" type="button" class="secondary">Collapse all</button>
      <button id="clear-selection" type="button" class="secondary">Clear selection</button>
    </div>
    <div id="docs-tree" aria-live="polite">Loading documentation catalog...</div>

    <template id="folder-row-template">
      <div class="folder-row" style="border:1px solid #d1d5db; border-radius:0.5rem; margin-bottom:0.65rem;">
        <div style="display:flex; align-items:center; gap:0.45rem; padding:0.45rem 0.6rem; background:#f9fafb; border-bottom:1px solid #e5e7eb;">
          <button type="button" class="folder-toggle secondary" style="padding:0.2rem 0.5rem; min-width:2rem;">-</button>
          <label style="display:flex; align-items:center; gap:0.4rem; margin:0;">
            <input type="checkbox" class="folder-checkbox" />
            <span class="folder-label"></span>
          </label>
          <span class="folder-count" style="margin-left:auto; color:#6b7280; font-size:0.9rem;"></span>
        </div>
        <div class="folder-children" style="padding:0.5rem 0.6rem;"></div>
      </div>
    </template>

    <template id="file-row-template">
      <label class="file-row" style="display:flex; align-items:center; gap:0.5rem; margin:0.3rem 0;">
        <input type="checkbox" class="file-checkbox" />
        <span class="file-label"></span>
      </label>
    </template>
  </article>

  <article class="panel" id="docs-right-pane">
    <div style="display:flex; align-items:center; justify-content:space-between; gap:0.75rem; flex-wrap:wrap; margin-bottom:0.6rem;">
      <button id="copy-output" type="button">Copy to Clipboard</button>
      <div id="docs-status" class="status" role="status"></div>
    </div>
    <pre id="markdown-output" style="margin:0; min-height:60vh; border:1px solid #d1d5db; background:#0f172a; color:#e5e7eb; border-radius:0.5rem; padding:0.75rem; overflow:auto; white-space:pre-wrap;"></pre>
  </article>
</section>

<style>
  @media (max-width: 900px) {{
    .docs-layout {{
      grid-template-columns: 1fr;
    }}
  }}
</style>

<script>
(() => {{
  const FOLDER_STATE_KEY = {FOLDER_STATE_STORAGE_KEY!r};
  const docsTree = document.getElementById("docs-tree");
  const output = document.getElementById("markdown-output");
  const statusText = document.getElementById("docs-status");
  const expandAllButton = document.getElementById("expand-all");
  const collapseAllButton = document.getElementById("collapse-all");
  const clearSelectionButton = document.getElementById("clear-selection");
  const copyButton = document.getElementById("copy-output");
  const folderTemplate = document.getElementById("folder-row-template");
  const fileTemplate = document.getElementById("file-row-template");

  const state = {{
    catalog: null,
    selected: new Set(),
    folderState: loadFolderState(),
  }};

  function setStatus(message) {{
    statusText.textContent = message;
  }}

  function loadFolderState() {{
    try {{
      const raw = localStorage.getItem(FOLDER_STATE_KEY);
      if (!raw) {{
        return {{}};
      }}
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed === "object" ? parsed : {{}};
    }} catch (_error) {{
      return {{}};
    }}
  }}

  function saveFolderState() {{
    localStorage.setItem(FOLDER_STATE_KEY, JSON.stringify(state.folderState));
  }}

  function expanded(folderId) {{
    if (!(folderId in state.folderState)) {{
      return true;
    }}
    return Boolean(state.folderState[folderId]);
  }}

  function folderSelectedCount(folder) {{
    return folder.children.filter((child) => state.selected.has(child.id)).length;
  }}

  function addFileRow(parentEl, file) {{
    const node = fileTemplate.content.cloneNode(true);
    const checkbox = node.querySelector(".file-checkbox");
    const label = node.querySelector(".file-label");

    checkbox.checked = state.selected.has(file.id);
    checkbox.dataset.fileId = file.id;
    label.textContent = file.label;

    checkbox.addEventListener("change", () => {{
      if (checkbox.checked) {{
        state.selected.add(file.id);
      }} else {{
        state.selected.delete(file.id);
      }}
      renderTree();
      refreshConcat();
    }});

    parentEl.appendChild(node);
  }}

  function renderTree() {{
    docsTree.textContent = "";
    if (!state.catalog) {{
      docsTree.textContent = "No catalog loaded.";
      return;
    }}

    const folderContainer = document.createElement("div");
    for (const folder of state.catalog.folders) {{
      const node = folderTemplate.content.cloneNode(true);
      const row = node.querySelector(".folder-row");
      const toggle = node.querySelector(".folder-toggle");
      const folderCheckbox = node.querySelector(".folder-checkbox");
      const folderLabel = node.querySelector(".folder-label");
      const folderCount = node.querySelector(".folder-count");
      const childrenContainer = node.querySelector(".folder-children");

      folderLabel.textContent = folder.label;

      const selectedCount = folderSelectedCount(folder);
      folderCount.textContent = `${{selectedCount}}/${{folder.children.length}}`;

      const allSelected = folder.children.length > 0 && selectedCount === folder.children.length;
      folderCheckbox.checked = allSelected;
      folderCheckbox.indeterminate = selectedCount > 0 && selectedCount < folder.children.length;

      const isExpanded = expanded(folder.id);
      toggle.textContent = isExpanded ? "-" : "+";
      childrenContainer.style.display = isExpanded ? "block" : "none";

      toggle.addEventListener("click", () => {{
        state.folderState[folder.id] = !expanded(folder.id);
        saveFolderState();
        renderTree();
      }});

      folderCheckbox.addEventListener("change", () => {{
        if (folderCheckbox.checked) {{
          for (const child of folder.children) {{
            state.selected.add(child.id);
          }}
        }} else {{
          for (const child of folder.children) {{
            state.selected.delete(child.id);
          }}
        }}
        renderTree();
        refreshConcat();
      }});

      for (const child of folder.children) {{
        addFileRow(childrenContainer, child);
      }}

      row.dataset.folderId = folder.id;
      folderContainer.appendChild(node);
    }}
    docsTree.appendChild(folderContainer);

    const rootSection = document.createElement("div");
    rootSection.style.marginTop = "1rem";

    const rootTitle = document.createElement("h3");
    rootTitle.textContent = "Root files";
    rootTitle.style.margin = "0 0 0.4rem 0";
    rootSection.appendChild(rootTitle);

    if (state.catalog.root_files.length === 0) {{
      const empty = document.createElement("p");
      empty.className = "status";
      empty.textContent = "No root markdown files found.";
      rootSection.appendChild(empty);
    }} else {{
      for (const rootFile of state.catalog.root_files) {{
        addFileRow(rootSection, rootFile);
      }}
    }}

    docsTree.appendChild(rootSection);
  }}

  async function refreshConcat() {{
    const selectedIds = Array.from(state.selected);
    try {{
      const response = await fetch("/docs/concat", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ selected_file_ids: selectedIds }}),
      }});
      const payload = await response.json();
      if (!response.ok) {{
        throw new Error(payload.detail || "Concat request failed.");
      }}
      output.textContent = payload.markdown;
      setStatus(`Selected ${{selectedIds.length}} file(s).`);
    }} catch (error) {{
      output.textContent = "";
      setStatus(`Concat failed: ${{error.message}}`);
    }}
  }}

  expandAllButton.addEventListener("click", () => {{
    if (!state.catalog) {{
      return;
    }}
    for (const folder of state.catalog.folders) {{
      state.folderState[folder.id] = true;
    }}
    saveFolderState();
    renderTree();
  }});

  collapseAllButton.addEventListener("click", () => {{
    if (!state.catalog) {{
      return;
    }}
    for (const folder of state.catalog.folders) {{
      state.folderState[folder.id] = false;
    }}
    saveFolderState();
    renderTree();
  }});

  clearSelectionButton.addEventListener("click", () => {{
    state.selected.clear();
    renderTree();
    refreshConcat();
  }});

  copyButton.addEventListener("click", async () => {{
    try {{
      await navigator.clipboard.writeText(output.textContent || "");
      setStatus("Copied markdown to clipboard.");
    }} catch (_error) {{
      setStatus("Clipboard copy failed.");
    }}
  }});

  async function init() {{
    setStatus("Loading docs catalog...");
    try {{
      const response = await fetch("/docs/catalog");
      if (!response.ok) {{
        throw new Error(`Catalog request failed: ${{response.status}}`);
      }}
      state.catalog = await response.json();
      renderTree();
      await refreshConcat();
    }} catch (error) {{
      docsTree.textContent = `Unable to load docs catalog: ${{error.message}}`;
      setStatus("Catalog unavailable.");
    }}
  }}

  init();
}})();
</script>
"""
    return _render_page("Documentation", "docs", body)


@app.get("/docs/catalog", tags=["docs"], summary="Docs catalog")
def docs_catalog() -> dict[str, list[dict[str, object]]]:
    return _docs_catalog()


@app.post("/docs/concat", tags=["docs"], summary="Concatenate selected docs")
def docs_concat(payload: DocsConcatRequest) -> dict[str, str]:
    docs_index = _docs_index()
    unknown_ids = [file_id for file_id in payload.selected_file_ids if file_id not in docs_index]
    if unknown_ids:
        details = ", ".join(unknown_ids)
        raise HTTPException(status_code=400, detail=f"Unknown document IDs: {details}")

    blocks: list[str] = []
    for file_id in payload.selected_file_ids:
        file_path = docs_index[file_id]
        relative_path = file_path.relative_to(_docs_root()).as_posix()
        content = file_path.read_text(encoding="utf-8")
        blocks.append(f"Path: docs/{relative_path}\n\n{content}")

    return {"markdown": "\n\n---\n\n".join(blocks)}


@app.get("/health", tags=["system"], summary="Health status")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/cli/start",
    tags=["cli"],
    summary="ai-orchestrator start contract",
    response_model=StartCommandOutput,
)
def cli_start_contract(payload: StartCommandRequest) -> StartCommandOutput:
    """
    Contract endpoint that documents the `ai-orchestrator start` command inputs
    and output schema. This endpoint returns an example response.
    """

    _ = payload
    return StartCommandOutput(
        instance_id="example-instance",
        gpu_type="A100",
        cost_per_hour=1.25,
        idle_timeout=1800,
        snapshot_version="snapshot-v1",
        deepseek_url="http://127.0.0.1:8080",
        whisper_url="http://127.0.0.1:9000",
    )


def run_dev_server() -> None:
    print(
        "Documentation server running:\n\n"
        "http://127.0.0.1:8000/\n"
        "http://127.0.0.1:8000/docs\n"
        "http://127.0.0.1:8000/api-docs"
    )
    uvicorn.run(app, host="127.0.0.1", port=8000)
