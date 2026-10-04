"""Same-origin registry UI; data endpoints enforce the existing JWT/RBAC."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def mount_registry_ui(app: FastAPI):
    directory = Path(__file__).resolve().parent / "static" / "registry"
    app.mount("/registry/assets", StaticFiles(directory=directory), name="registry-assets")

    @app.get("/registry", include_in_schema=False)
    def registry_page():
        return FileResponse(directory / "index.html", headers={
            "Cache-Control": "no-store",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
        })
