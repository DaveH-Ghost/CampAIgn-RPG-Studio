"""Frontend asset revision and import-map cache busting."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_index_injects_import_map_and_asset_rev(client):
    res = client.get("/")
    assert res.status_code == 200
    assert res.headers.get("cache-control", "").startswith("no-store")
    body = res.text
    assert "{{ASSET_REV}}" not in body
    assert "<!-- IMPORT_MAP -->" not in body
    assert '<script type="importmap">' in body
    assert "/static/ui.js?v=" in body
    assert "/static/plugins.js?v=" in body
    assert "/static/app.js?v=" in body
    assert 'href="/static/styles.css?v=' in body


def test_static_js_is_not_stored(client):
    res = client.get("/static/ui.js")
    assert res.status_code == 200
    assert "no-store" in res.headers.get("cache-control", "")


def test_asset_revision_changes_when_frontend_file_changes(tmp_path, monkeypatch):
    from backend import frontend_assets as fa

    fake_root = tmp_path / "frontend"
    fake_root.mkdir()
    (fake_root / "app.js").write_text("export {};\n", encoding="utf-8")
    (fake_root / "index.html").write_text(
        "<head><!-- IMPORT_MAP --><link href=\"/static/styles.css?v={{ASSET_REV}}\" />"
        "<script type=\"module\" src=\"/static/app.js?v={{ASSET_REV}}\"></script></head>",
        encoding="utf-8",
    )

    monkeypatch.setattr(fa, "_FRONTEND_DIR", fake_root)
    fa.clear_asset_revision_cache()
    rev1 = fa.asset_revision()
    html1 = fa.render_index_html()
    assert rev1 in html1
    assert f"/static/app.js?v={rev1}" in html1

    (fake_root / "ui.js").write_text("export const x = 1;\n", encoding="utf-8")
    fa.clear_asset_revision_cache()
    rev2 = fa.asset_revision()
    assert rev1 != rev2
    html2 = fa.render_index_html()
    assert f"/static/ui.js?v={rev2}" in html2
