"""
NSAI Notebook Test Suite
========================
Tests notebook execution and validates outputs using nbformat + subprocess.

Strategy:
  1. Syntax validation (notebook JSON structure)
  2. Cell-by-cell execution via nbconvert
  3. Import smoke tests (all cells importable)
  4. Output validation (key cells produce expected types)

Dependencies: pytest, nbformat, nbconvert, jupyter
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
NOTEBOOK_DIR = Path(__file__).parent.parent / "notebooks"
NOTEBOOKS = list(NOTEBOOK_DIR.glob("*.ipynb"))


def notebook_ids():
    """Generate test IDs from notebook filenames."""
    return [nb.stem for nb in NOTEBOOKS]


# ---------------------------------------------------------------------------
# 1. STRUCTURAL VALIDATION
# ---------------------------------------------------------------------------
class TestNotebookStructure:
    """Validate notebook JSON structure and metadata."""

    @pytest.mark.parametrize("notebook", NOTEBOOKS, ids=notebook_ids())
    def test_valid_json(self, notebook):
        """Notebook is valid JSON."""
        data = json.loads(notebook.read_text(encoding="utf-8"))
        assert "cells" in data
        assert "metadata" in data
        assert "nbformat" in data

    @pytest.mark.parametrize("notebook", NOTEBOOKS, ids=notebook_ids())
    def test_has_code_cells(self, notebook):
        """Notebook contains executable code cells."""
        data = json.loads(notebook.read_text(encoding="utf-8"))
        code_cells = [c for c in data["cells"] if c["cell_type"] == "code"]
        assert len(code_cells) > 0, "Notebook has no code cells"

    @pytest.mark.parametrize("notebook", NOTEBOOKS, ids=notebook_ids())
    def test_no_outputs(self, notebook):
        """Notebook is clean (no leftover outputs committed)."""
        data = json.loads(notebook.read_text(encoding="utf-8"))
        code_cells = [c for c in data["cells"] if c["cell_type"] == "code"]
        cells_with_output = [
            i for i, c in enumerate(code_cells)
            if c.get("outputs") and len(c["outputs"]) > 0
        ]
        assert len(cells_with_output) == 0, (
            f"Cells {cells_with_output} have outputs — "
            f"run 'jupyter nbconvert --clear-output' before committing"
        )

    @pytest.mark.parametrize("notebook", NOTEBOOKS, ids=notebook_ids())
    def test_kernel_spec(self, notebook):
        """Notebook specifies a Python kernel."""
        data = json.loads(notebook.read_text(encoding="utf-8"))
        kernel = data.get("metadata", {}).get("kernelspec", {})
        lang = kernel.get("language", "").lower()
        # Allow missing kernelspec (Colab sets it on open) or Python
        assert lang in ("", "python"), f"Unexpected kernel language: {lang}"

    @pytest.mark.parametrize("notebook", NOTEBOOKS, ids=notebook_ids())
    def test_no_empty_code_cells(self, notebook):
        """No completely empty code cells."""
        data = json.loads(notebook.read_text(encoding="utf-8"))
        code_cells = [c for c in data["cells"] if c["cell_type"] == "code"]
        empty = [
            i for i, c in enumerate(code_cells)
            if not "".join(c.get("source", [])).strip()
        ]
        # Allow max 2 empty cells (playground cells)
        assert len(empty) <= 2, (
            f"{len(empty)} empty code cells at indices {empty}"
        )

    @pytest.mark.parametrize("notebook", NOTEBOOKS, ids=notebook_ids())
    def test_cells_have_valid_types(self, notebook):
        """All cells have valid cell_type."""
        data = json.loads(notebook.read_text(encoding="utf-8"))
        valid_types = {"code", "markdown", "raw"}
        for i, cell in enumerate(data["cells"]):
            assert cell["cell_type"] in valid_types, (
                f"Cell {i} has invalid type: {cell['cell_type']}"
            )


# ---------------------------------------------------------------------------
# 2. IMPORT / SYNTAX VALIDATION
# ---------------------------------------------------------------------------
class TestNotebookSyntax:
    """Validate Python syntax in code cells."""

    @pytest.mark.parametrize("notebook", NOTEBOOKS, ids=notebook_ids())
    def test_code_cells_parse(self, notebook):
        """All code cells are valid Python syntax."""
        data = json.loads(notebook.read_text(encoding="utf-8"))
        code_cells = [c for c in data["cells"] if c["cell_type"] == "code"]

        errors = []
        for i, cell in enumerate(code_cells):
            source = "".join(cell.get("source", []))
            # Skip cells with shell commands or magic commands
            if source.strip().startswith(("!", "%", "%%")):
                continue
            # Skip empty cells
            if not source.strip():
                continue
            try:
                compile(source, f"<cell-{i}>", "exec")
            except SyntaxError as e:
                errors.append(f"Cell {i}: {e}")

        assert not errors, f"Syntax errors found:\n" + "\n".join(errors)


# ---------------------------------------------------------------------------
# 3. EXECUTION TEST (requires jupyter/nbconvert)
# ---------------------------------------------------------------------------
class TestNotebookExecution:
    """Execute notebooks end-to-end and check for errors."""

    @pytest.fixture(autouse=True)
    def _check_nbconvert(self):
        """Skip execution tests if nbconvert not available."""
        try:
            import nbformat  # noqa: F401
        except ImportError:
            pytest.skip("nbformat not installed (pip install nbformat)")

        result = subprocess.run(
            [sys.executable, "-m", "jupyter", "--version"],
            capture_output=True
        )
        if result.returncode != 0:
            pytest.skip("jupyter not installed")

    @pytest.mark.parametrize("notebook", NOTEBOOKS, ids=notebook_ids())
    def test_execute_notebook(self, notebook, tmp_path):
        """Execute notebook top-to-bottom without errors."""
        output_path = tmp_path / notebook.name

        result = subprocess.run(
            [
                sys.executable, "-m", "jupyter", "nbconvert",
                "--to", "notebook",
                "--execute",
                "--ExecutePreprocessor.timeout=120",
                "--ExecutePreprocessor.kernel_name=python3",
                "--output", str(output_path),
                str(notebook),
            ],
            capture_output=True,
            text=True,
            env={
                **dict(__import__("os").environ),
                "PYTHONPATH": str(notebook.parent.parent.parent.parent),
            },
        )

        if result.returncode != 0:
            # Parse which cell failed
            stderr = result.stderr
            pytest.fail(
                f"Notebook execution failed:\n"
                f"STDOUT: {result.stdout[:500]}\n"
                f"STDERR: {stderr[:1000]}"
            )

        # Verify output notebook exists and has outputs
        assert output_path.exists(), "Output notebook not created"


# ---------------------------------------------------------------------------
# 4. CONTENT VALIDATION
# ---------------------------------------------------------------------------
class TestNotebookContent:
    """Validate notebook content meets quality standards."""

    @pytest.mark.parametrize("notebook", NOTEBOOKS, ids=notebook_ids())
    def test_has_markdown_documentation(self, notebook):
        """Notebook has documentation (markdown cells)."""
        data = json.loads(notebook.read_text(encoding="utf-8"))
        md_cells = [c for c in data["cells"] if c["cell_type"] == "markdown"]
        assert len(md_cells) >= 3, (
            f"Only {len(md_cells)} markdown cells — "
            f"notebooks should be well-documented"
        )

    @pytest.mark.parametrize("notebook", NOTEBOOKS, ids=notebook_ids())
    def test_has_title(self, notebook):
        """First cell is a markdown title."""
        data = json.loads(notebook.read_text(encoding="utf-8"))
        first = data["cells"][0]
        assert first["cell_type"] == "markdown", "First cell should be markdown"
        source = "".join(first.get("source", []))
        assert source.strip().startswith("#"), "First cell should be a heading"

    @pytest.mark.parametrize("notebook", NOTEBOOKS, ids=notebook_ids())
    def test_no_hardcoded_secrets(self, notebook):
        """No secrets or tokens in notebook cells."""
        data = json.loads(notebook.read_text(encoding="utf-8"))
        secrets_patterns = ["glpat-", "ghp_", "sk-", "AKIA", "password="]

        for i, cell in enumerate(data["cells"]):
            source = "".join(cell.get("source", [])).lower()
            for pattern in secrets_patterns:
                assert pattern.lower() not in source, (
                    f"Cell {i} contains potential secret: '{pattern}'"
                )

    @pytest.mark.parametrize("notebook", NOTEBOOKS, ids=notebook_ids())
    def test_imports_are_at_top(self, notebook):
        """Import statements are concentrated in early cells."""
        data = json.loads(notebook.read_text(encoding="utf-8"))
        code_cells = [c for c in data["cells"] if c["cell_type"] == "code"]

        # Find last cell with import statement
        last_import_cell = 0
        for i, cell in enumerate(code_cells):
            source = "".join(cell.get("source", []))
            lines = source.strip().split("\n")
            has_import = any(
                l.strip().startswith(("import ", "from "))
                for l in lines
                if not l.strip().startswith("#")
            )
            if has_import:
                last_import_cell = i

        # Notebooks are sectioned — imports in each section is OK.
        # Just ensure the FIRST import is in the first 3 cells.
        first_import_cell = None
        for i, cell in enumerate(code_cells):
            source = "".join(cell.get("source", []))
            lines = source.strip().split("\n")
            has_import = any(
                l.strip().startswith(("import ", "from "))
                for l in lines
                if not l.strip().startswith("#")
            )
            if has_import:
                first_import_cell = i
                break

        assert first_import_cell is not None, "No imports found"
        assert first_import_cell <= 2, (
            f"First import in cell {first_import_cell} — "
            f"setup imports should be in the first cells"
        )
