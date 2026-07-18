"""campaign-rpg-studio FastAPI application."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

from datetime import datetime, timezone

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from campaign_rpg_engine import estimate_prompt_tokens
from backend.plugin_registry import merged_interact_template_vars

from backend.interaction_handlers_api import get_interaction_handlers_catalog
from backend.entity_private_data_api import put_entity_private_data
from backend.area_api import create_area as api_create_area
from backend.area_api import delete_area as api_delete_area
from backend.area_api import edit_area as api_edit_area
from backend.decorations_api import (
    create_decoration as api_create_decoration,
    delete_decoration as api_delete_decoration,
    reorder_decoration as api_reorder_decoration,
    update_decoration as api_update_decoration,
)
from backend.decoration_assets_api import upload_decoration_asset
from backend.command_dispatch import dispatch_command
from backend.entity_templates_api import (
    delete_entity_template,
    download_entity_template_file,
    export_entity_template_download,
    get_entity_template,
    list_entity_templates,
    save_entity_from_world,
    save_entity_template,
    spawn_entity_from_template_data,
    spawn_entity_template,
)
from backend.area_templates_api import (
    delete_area_template,
    download_area_template_file,
    export_area_template_download,
    get_area_template,
    list_area_templates,
    save_area_from_world,
    save_area_template,
    spawn_area_from_template_data,
    spawn_area_template,
)
from backend.schemas import (
    AreaTemplateImportRequest,
    AreaTemplateSaveRequest,
    AreaTemplateSpawnFromBodyRequest,
    AreaTemplateSpawnRequest,
    ActiveAgentRequest,
    ActiveAreaRequest,
    CommandRequest,
    CreateAreaRequest,
    CreateDecorationRequest,
    DeleteAreaRequest,
    DeleteDecorationRequest,
    EditAreaRequest,
    EntityPrivateDataRequest,
    EntityTemplateImportRequest,
    EntityTemplateSaveRequest,
    EntityTemplateSpawnFromBodyRequest,
    EntityTemplateSpawnRequest,
    EventRequest,
    LlmSettingsRequest,
    PromptBlocksPreviewRequest,
    PromptBlocksRequest,
    ReorderDecorationRequest,
    TurnRequest,
    ManualTurnRequest,
    UpdateDecorationRequest,
    VisionUnitsRequest,
    CoordinateModeRequest,
)
from backend.session_store import get_session_store
from backend.snapshot_compat import normalize_state_snapshot
from backend.turn_runner import run_llm_turn, run_manual_turn
from backend.turn_verbs_api import get_turn_verbs_catalog
from backend.version import engine_version, studio_version
from backend.vision_units_api import put_vision_units as api_put_vision_units
from backend.coordinate_mode_api import put_coordinate_mode as api_put_coordinate_mode
from backend.plugin_upload import load_all_plugins, upload_plugin
from backend.plugins_api import (
    get_player_turn_assist_route,
    get_plugin_panel_route,
    get_plugins_catalog,
    on_session_imported,
    post_disable_plugin,
    post_enable_plugin,
    post_plugin_action,
)
from backend.lorebooks_api import (
    create_lorebook,
    delete_lorebook,
    export_lorebook_download,
    get_lorebook,
    get_lorebook_scan_config,
    list_lorebooks,
    load_demo_lorebook,
    put_lorebook,
    put_lorebook_scan_config,
    upload_lorebook,
)
from backend.memory_modules_api import get_memory_modules_catalog
from backend.settings_api import get_llm_settings, put_llm_settings
from backend.prompt_api import (
    get_prompt_block_catalog_route as api_get_prompt_block_catalog,
    get_prompt_blocks as api_get_prompt_blocks,
    get_prompt_slots as api_get_prompt_slots,
    preview_prompt_blocks as api_preview_prompt_blocks,
    put_prompt_blocks as api_put_prompt_blocks,
    reset_prompt_blocks as api_reset_prompt_blocks,
)

_STUDIO_DIR = Path(__file__).resolve().parent.parent
_FRONTEND_DIR = _STUDIO_DIR / "frontend"
# Sibling engine checkout (co-dev); optional for uvicorn reload.
_ENGINE_ROOT = _STUDIO_DIR.parent / "CampAIgn-RPG-Engine"


def _ensure_reference_handlers() -> None:
    from reference_handlers import register_reference_handlers

    register_reference_handlers()


@asynccontextmanager
async def _app_lifespan(_app: FastAPI):
    _ensure_reference_handlers()
    load_all_plugins()
    yield


def create_app() -> FastAPI:
    _ensure_reference_handlers()
    load_all_plugins()
    app = FastAPI(title="campaign-rpg-studio", version=studio_version(), lifespan=_app_lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:8765",
            "http://localhost:8765",
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/interaction-handlers")
    def get_interaction_handlers() -> dict[str, object]:
        return get_interaction_handlers_catalog(get_session_store().session)

    @app.get("/api/turn-verbs")
    def get_turn_verbs() -> dict[str, object]:
        return get_turn_verbs_catalog(get_session_store().session)

    @app.get("/api/player-turn-assist")
    def get_player_turn_assist() -> dict[str, object]:
        return get_player_turn_assist_route(get_session_store().session)

    @app.get("/api/health")
    def health() -> dict[str, object]:
        return {
            "ok": True,
            "version": studio_version(),
            "campaign_rpg_engine_version": engine_version(),
        }

    @app.get("/api/interact-template-vars")
    def get_interact_template_vars() -> dict[str, object]:
        return {"vars": merged_interact_template_vars(get_session_store().session)}

    @app.get("/api/state")
    def get_state() -> dict:
        snap = get_session_store().session.snapshot(include_private=True)
        return normalize_state_snapshot(snap)

    @app.put("/api/vision-units")
    def put_vision_units_route(body: VisionUnitsRequest) -> dict[str, object]:
        return api_put_vision_units(
            get_session_store().session,
            units=body.units,
            units_per_tile=body.units_per_tile,
        )

    @app.put("/api/coordinate-mode")
    def put_coordinate_mode_route(body: CoordinateModeRequest) -> dict[str, object]:
        return api_put_coordinate_mode(
            get_session_store().session,
            mode=body.mode,
        )

    @app.post("/api/command")
    def post_command(body: CommandRequest) -> dict[str, object]:
        """Run a stepper-style command (create/edit/delete, listings)."""
        store = get_session_store()
        session = store.session
        result = dispatch_command(session, body.line.strip())
        payload: dict[str, object] = {"ok": result.ok, "message": result.message}
        if result.ok:
            store.clear_undo()
            payload["snapshot"] = normalize_state_snapshot(
                session.snapshot(include_private=True)
            )
            payload["can_undo"] = False
            payload["undo_remaining"] = 0
        return payload

    @app.put("/api/entity-private-data")
    def put_entity_private_data_route(body: EntityPrivateDataRequest) -> dict[str, object]:
        """Set app-owned private_data on an agent or object (not CLI / LLM)."""
        return put_entity_private_data(
            get_session_store().session,
            entity_id=body.entity_id.strip(),
            private_data=body.private_data,
        )

    @app.post("/api/create-area")
    def post_create_area(body: CreateAreaRequest) -> dict[str, object]:
        """Create a new empty area (same pattern as /api/event)."""
        session = get_session_store().session
        return api_create_area(
            session,
            area_id=body.area_id.strip().lower(),
            description=body.description,
            width=body.width,
            height=body.height,
        )

    @app.post("/api/edit-area")
    def post_edit_area(body: EditAreaRequest) -> dict[str, object]:
        """Edit an area description and/or grid size."""
        session = get_session_store().session
        return api_edit_area(
            session,
            area_id=body.area_id.strip().lower(),
            description=body.description,
            width=body.width,
            height=body.height,
        )

    @app.post("/api/delete-area")
    def post_delete_area(body: DeleteAreaRequest) -> dict[str, object]:
        """Delete an empty area."""
        session = get_session_store().session
        return api_delete_area(session, area_id=body.area_id.strip().lower())

    @app.post("/api/decorations")
    def post_create_decoration(body: CreateDecorationRequest) -> dict[str, object]:
        session = get_session_store().session
        result = api_create_decoration(
            session,
            kind=body.kind,
            image=body.image,
            area_id=body.area_id,
            x=body.x,
            y=body.y,
            width=body.width,
            height=body.height,
            z_index=body.z_index,
            repeat=body.repeat,
            decoration_id=body.decoration_id,
            label=body.label,
        )
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("message", "Create failed"))
        return result

    @app.put("/api/decorations")
    def put_update_decoration(body: UpdateDecorationRequest) -> dict[str, object]:
        session = get_session_store().session
        result = api_update_decoration(
            session,
            decoration_id=body.decoration_id,
            area_id=body.area_id,
            image=body.image,
            x=body.x,
            y=body.y,
            width=body.width,
            height=body.height,
            z_index=body.z_index,
            repeat=body.repeat,
        )
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("message", "Update failed"))
        return result

    @app.delete("/api/decorations")
    def delete_decoration_route(body: DeleteDecorationRequest) -> dict[str, object]:
        session = get_session_store().session
        result = api_delete_decoration(
            session,
            decoration_id=body.decoration_id,
            area_id=body.area_id,
        )
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("message", "Delete failed"))
        return result

    @app.post("/api/decorations/reorder")
    def post_reorder_decoration(body: ReorderDecorationRequest) -> dict[str, object]:
        session = get_session_store().session
        result = api_reorder_decoration(
            session,
            decoration_id=body.decoration_id,
            direction=body.direction,
            area_id=body.area_id,
        )
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("message", "Reorder failed"))
        return result

    @app.post("/api/decoration-assets/upload")
    async def upload_decoration_asset_route(file: UploadFile = File(...)) -> dict[str, object]:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Missing filename.")
        raw = await file.read()
        try:
            return upload_decoration_asset(data=raw, filename=file.filename)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/active-agent")
    def post_active_agent(body: ActiveAgentRequest) -> dict[str, object]:
        result = get_session_store().session.set_active_agent(body.name_or_id)
        return {"ok": result.ok, "message": result.message}

    @app.post("/api/active-area")
    def post_active_area(body: ActiveAreaRequest) -> dict[str, object]:
        session = get_session_store().session
        result = session.set_active_area(body.area_id)
        payload: dict[str, object] = {"ok": result.ok, "message": result.message}
        if result.ok:
            payload["snapshot"] = normalize_state_snapshot(
                session.snapshot(include_private=True)
            )
        return payload

    @app.post("/api/turn")
    def post_turn(body: TurnRequest) -> dict[str, object]:
        return run_llm_turn(
            get_session_store().session,
            agent_id=body.agent_id,
            include_examples=body.include_examples,
        )

    @app.post("/api/turn/manual")
    def post_manual_turn(body: ManualTurnRequest) -> dict[str, object]:
        return run_manual_turn(
            get_session_store().session,
            body.compound_turn,
            agent_id=body.agent_id,
        )

    @app.get("/api/turn/undo")
    def get_turn_undo_status() -> dict[str, object]:
        return get_session_store().undo_status()

    @app.post("/api/turn/undo")
    def post_turn_undo() -> dict[str, object]:
        return get_session_store().undo_turn()

    @app.get("/api/prompt")
    def get_prompt(agent_id: str | None = None) -> dict[str, object]:
        session = get_session_store().session
        if agent_id is not None and session.get_agent(agent_id) is None:
            return {"ok": False, "message": f"Agent {agent_id!r} not found."}
        prompt = session.build_prompt(agent_id)
        return {
            "ok": True,
            "prompt": prompt,
            "length": len(prompt),
            "prompt_tokens": estimate_prompt_tokens(prompt),
            "include_examples": session.include_examples,
        }

    @app.get("/api/prompt-blocks")
    def get_prompt_blocks_route(agent_id: str | None = None) -> dict[str, object]:
        return api_get_prompt_blocks(get_session_store().session, agent_id=agent_id)

    @app.put("/api/prompt-blocks")
    def put_prompt_blocks_route(body: PromptBlocksRequest) -> dict[str, object]:
        items = [block.model_dump() for block in body.blocks]
        return api_put_prompt_blocks(get_session_store().session, items)

    @app.post("/api/prompt-blocks/preview")
    def preview_prompt_blocks_route(body: PromptBlocksPreviewRequest) -> dict[str, object]:
        items = [block.model_dump() for block in body.blocks]
        return api_preview_prompt_blocks(
            get_session_store().session,
            items,
            agent_id=body.agent_id,
        )

    @app.post("/api/prompt-blocks/reset")
    def reset_prompt_blocks_route() -> dict[str, object]:
        return api_reset_prompt_blocks(get_session_store().session)

    @app.get("/api/prompt-slots")
    def get_prompt_slots_route(agent_id: str | None = None) -> dict[str, object]:
        return api_get_prompt_slots(get_session_store().session, agent_id)

    @app.get("/api/prompt-block-catalog")
    def get_prompt_block_catalog_route() -> dict[str, object]:
        return api_get_prompt_block_catalog(get_session_store().session)

    @app.get("/api/memory-modules")
    def get_memory_modules_route() -> dict[str, object]:
        return get_memory_modules_catalog()

    @app.get("/api/lorebooks")
    def get_lorebooks_route() -> dict[str, object]:
        return list_lorebooks(get_session_store().session)

    @app.post("/api/lorebooks")
    def create_lorebook_route(body: dict | None = None) -> dict[str, object]:
        result = create_lorebook(get_session_store().session, body or {})
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("message", "Create failed"))
        return result

    @app.post("/api/lorebooks/load-demo")
    def load_demo_lorebook_route() -> dict[str, object]:
        result = load_demo_lorebook(get_session_store().session)
        if not result.get("ok"):
            raise HTTPException(status_code=404, detail=result.get("message", "Not found"))
        return result

    @app.get("/api/lorebooks/scan-config")
    def get_lorebook_scan_config_route(agent_id: str | None = None) -> dict[str, object]:
        result = get_lorebook_scan_config(
            get_session_store().session,
            agent_id=agent_id,
        )
        if not result.get("ok"):
            raise HTTPException(status_code=404, detail=result.get("message", "Not found"))
        return result

    @app.put("/api/lorebooks/scan-config")
    def put_lorebook_scan_config_route(body: dict) -> dict[str, object]:
        result = put_lorebook_scan_config(get_session_store().session, body)
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("message", "Update failed"))
        return result

    @app.get("/api/lorebooks/{book_id}")
    def get_lorebook_route(book_id: str) -> dict[str, object]:
        result = get_lorebook(get_session_store().session, book_id)
        if not result.get("ok"):
            raise HTTPException(status_code=404, detail=result.get("message", "Not found"))
        return result

    @app.get("/api/lorebooks/{book_id}/download")
    def download_lorebook_route(book_id: str) -> Response:
        result = export_lorebook_download(get_session_store().session, book_id)
        if not result.get("ok"):
            raise HTTPException(status_code=404, detail=result.get("message", "Not found"))
        filename = str(result["filename"])
        body = json.dumps(result["payload"], indent=2, ensure_ascii=False)
        return Response(
            content=body,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.put("/api/lorebooks/{book_id}")
    def put_lorebook_route(book_id: str, body: dict) -> dict[str, object]:
        result = put_lorebook(get_session_store().session, book_id, body)
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("message", "Update failed"))
        return result

    @app.delete("/api/lorebooks/{book_id}")
    def delete_lorebook_route(book_id: str) -> dict[str, object]:
        result = delete_lorebook(get_session_store().session, book_id)
        if not result.get("ok"):
            raise HTTPException(status_code=404, detail=result.get("message", "Not found"))
        return result

    @app.post("/api/lorebooks/upload")
    async def upload_lorebook_route(file: UploadFile = File(...)) -> dict[str, object]:
        if not file.filename or not file.filename.lower().endswith(".json"):
            raise HTTPException(status_code=400, detail="Upload must be a .json file.")
        raw = await file.read()
        try:
            source = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=400, detail="Lorebook file must be UTF-8 text."
            ) from exc
        result = upload_lorebook(
            get_session_store().session,
            source=source,
            filename=file.filename,
        )
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("message", "Upload failed"))
        return result

    @app.get("/api/entity-templates")
    def get_entity_templates_route() -> dict[str, object]:
        return list_entity_templates()

    @app.get("/api/entity-templates/{template_id}")
    def get_entity_template_route(template_id: str) -> dict[str, object]:
        result = get_entity_template(template_id)
        if not result.get("ok"):
            raise HTTPException(status_code=404, detail=result.get("message", "Not found"))
        return result

    @app.post("/api/entity-templates/import")
    def import_entity_template_route(body: EntityTemplateImportRequest) -> dict[str, object]:
        result = save_entity_template(body.template, filename=body.filename)
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("message", "Import failed"))
        return result

    @app.post("/api/entity-templates/save-from-entity")
    def save_entity_template_route(body: EntityTemplateSaveRequest) -> dict[str, object]:
        result = save_entity_from_world(
            get_session_store().session,
            kind=body.kind,
            entity_id=body.entity_id,
            filename=body.filename,
            include_memory=body.include_memory,
        )
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("message", "Save failed"))
        return result

    @app.post("/api/entity-templates/export-from-entity")
    def export_entity_template_route(body: EntityTemplateSaveRequest) -> Response:
        result = export_entity_template_download(
            get_session_store().session,
            kind=body.kind,
            entity_id=body.entity_id,
            filename=body.filename,
            include_memory=body.include_memory,
        )
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("message", "Export failed"))
        filename = str(result["filename"])
        payload = json.dumps(result["template"], indent=2, ensure_ascii=False)
        return Response(
            content=payload,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.get("/api/entity-templates/{template_id}/download")
    def download_entity_template_route(template_id: str) -> Response:
        result = download_entity_template_file(template_id)
        if not result.get("ok"):
            raise HTTPException(status_code=404, detail=result.get("message", "Not found"))
        filename = str(result["filename"])
        payload = json.dumps(result["template"], indent=2, ensure_ascii=False)
        return Response(
            content=payload,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.post("/api/entity-templates/spawn-from-template")
    def spawn_entity_from_template_route(
        body: EntityTemplateSpawnFromBodyRequest,
    ) -> dict[str, object]:
        result = spawn_entity_from_template_data(
            get_session_store().session,
            body.template,
            position=body.position,
            area_id=body.area_id,
        )
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("message", "Spawn failed"))
        return result

    @app.post("/api/entity-templates/{template_id}/spawn")
    def spawn_entity_template_route(
        template_id: str,
        body: EntityTemplateSpawnRequest,
    ) -> dict[str, object]:
        result = spawn_entity_template(
            get_session_store().session,
            template_id,
            position=body.position,
            area_id=body.area_id,
        )
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("message", "Spawn failed"))
        return result

    @app.delete("/api/entity-templates/{template_id}")
    def delete_entity_template_route(template_id: str) -> dict[str, object]:
        result = delete_entity_template(template_id)
        if not result.get("ok"):
            raise HTTPException(status_code=404, detail=result.get("message", "Not found"))
        return result

    @app.get("/api/area-templates")
    def get_area_templates_route() -> dict[str, object]:
        return list_area_templates()

    @app.get("/api/area-templates/{template_id}")
    def get_area_template_route(template_id: str) -> dict[str, object]:
        result = get_area_template(template_id)
        if not result.get("ok"):
            raise HTTPException(status_code=404, detail=result.get("message", "Not found"))
        return result

    @app.post("/api/area-templates/import")
    def import_area_template_route(body: AreaTemplateImportRequest) -> dict[str, object]:
        result = save_area_template(body.template, filename=body.filename)
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("message", "Import failed"))
        return result

    @app.post("/api/area-templates/save-from-area")
    def save_area_template_route(body: AreaTemplateSaveRequest) -> dict[str, object]:
        result = save_area_from_world(
            get_session_store().session,
            area_id=body.area_id,
            filename=body.filename,
            name=body.name,
            include_hidden_objects=body.include_hidden_objects,
        )
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("message", "Save failed"))
        return result

    @app.post("/api/area-templates/export-from-area")
    def export_area_template_route(body: AreaTemplateSaveRequest) -> Response:
        result = export_area_template_download(
            get_session_store().session,
            area_id=body.area_id,
            filename=body.filename,
            name=body.name,
            include_hidden_objects=body.include_hidden_objects,
        )
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("message", "Export failed"))
        filename = str(result["filename"])
        payload = json.dumps(result["template"], indent=2, ensure_ascii=False)
        return Response(
            content=payload,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.get("/api/area-templates/{template_id}/download")
    def download_area_template_route(template_id: str) -> Response:
        result = download_area_template_file(template_id)
        if not result.get("ok"):
            raise HTTPException(status_code=404, detail=result.get("message", "Not found"))
        filename = str(result["filename"])
        payload = json.dumps(result["template"], indent=2, ensure_ascii=False)
        return Response(
            content=payload,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.post("/api/area-templates/spawn-from-template")
    def spawn_area_from_template_route(
        body: AreaTemplateSpawnFromBodyRequest,
    ) -> dict[str, object]:
        result = spawn_area_from_template_data(
            get_session_store().session,
            body.template,
            area_id=body.area_id,
            mode=body.mode,
        )
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("message", "Spawn failed"))
        return result

    @app.post("/api/area-templates/{template_id}/spawn")
    def spawn_area_template_route(
        template_id: str,
        body: AreaTemplateSpawnRequest,
    ) -> dict[str, object]:
        result = spawn_area_template(
            get_session_store().session,
            template_id,
            area_id=body.area_id,
            mode=body.mode,
        )
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("message", "Spawn failed"))
        return result

    @app.delete("/api/area-templates/{template_id}")
    def delete_area_template_route(template_id: str) -> dict[str, object]:
        result = delete_area_template(template_id)
        if not result.get("ok"):
            raise HTTPException(status_code=404, detail=result.get("message", "Not found"))
        return result

    @app.get("/api/plugins")
    def get_plugins_route() -> dict[str, object]:
        return get_plugins_catalog(get_session_store().session)

    @app.post("/api/plugins/{plugin_id}/enable")
    def enable_plugin_route(plugin_id: str) -> dict[str, object]:
        result = post_enable_plugin(get_session_store().session, plugin_id)
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("message", "Enable failed"))
        return result

    @app.post("/api/plugins/{plugin_id}/disable")
    def disable_plugin_route(plugin_id: str) -> dict[str, object]:
        result = post_disable_plugin(get_session_store().session, plugin_id)
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("message", "Disable failed"))
        return result

    @app.get("/api/plugins/{plugin_id}/panel")
    def get_plugin_panel_api_route(plugin_id: str) -> dict[str, object]:
        result = get_plugin_panel_route(get_session_store().session, plugin_id)
        if not result.get("ok"):
            raise HTTPException(status_code=404, detail=result.get("message", "Not found"))
        return result

    @app.post("/api/plugins/{plugin_id}/action")
    def post_plugin_action_route(plugin_id: str, body: dict) -> dict[str, object]:
        result = post_plugin_action(get_session_store().session, plugin_id, body)
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("message", "Action failed"))
        return result

    @app.post("/api/plugins/upload")
    async def upload_plugin_route(file: UploadFile = File(...)) -> dict[str, object]:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Missing filename.")
        lower = file.filename.lower()
        if not (lower.endswith(".py") or lower.endswith(".zip")):
            raise HTTPException(status_code=400, detail="Upload must be a .py file or .zip package.")
        raw = await file.read()
        try:
            if lower.endswith(".py"):
                source = raw.decode("utf-8")
            else:
                source = raw
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=400, detail="Plugin file must be UTF-8 text.") from exc
        try:
            if lower.endswith(".py"):
                return upload_plugin(source=source, filename=file.filename)
            return upload_plugin(source=raw, filename=file.filename)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/settings/llm")
    def get_llm_settings_route() -> dict[str, object]:
        return get_llm_settings()

    @app.put("/api/settings/llm")
    def put_llm_settings_route(body: LlmSettingsRequest) -> dict[str, object]:
        return put_llm_settings(api_key=body.api_key, model=body.model)

    @app.get("/api/session/export")
    def export_session_route() -> JSONResponse:
        store = get_session_store()
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        filename = f"realm-session-{stamp}.json"
        return JSONResponse(
            content=store.export_session(),
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    @app.post("/api/session/import")
    async def import_session_route(body: dict) -> dict[str, object]:
        store = get_session_store()
        try:
            store.import_session(body)
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        session = store.session
        agent = session.get_active_agent()
        return {
            "ok": True,
            "message": (
                f"Session loaded (turn {session.session_turn}, "
                f"active agent {agent.name}, {len(session.areas)} area(s))."
            ),
        }

    @app.post("/api/event")
    def post_event(body: EventRequest) -> dict[str, object]:
        session = get_session_store().session
        result = session.emit_area_event(body.text, agent_ids=body.agent_ids)
        payload: dict[str, object] = {"ok": result.ok, "message": result.message}
        if result.ok:
            payload["snapshot"] = normalize_state_snapshot(
                session.snapshot(include_private=True)
            )
        return payload

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(_FRONTEND_DIR / "index.html")

    if _FRONTEND_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=_FRONTEND_DIR), name="static")

    return app


app = create_app()

_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 8765
_DEFAULT_URL = f"http://{_DEFAULT_HOST}:{_DEFAULT_PORT}"


def main() -> None:
    import argparse
    import threading
    import webbrowser

    import uvicorn

    parser = argparse.ArgumentParser(prog="campaign-rpg-studio")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the default browser on startup",
    )
    args = parser.parse_args()

    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(_DEFAULT_URL)).start()

    reload_dirs = [str(_STUDIO_DIR)]
    if _ENGINE_ROOT.is_dir():
        reload_dirs.append(str(_ENGINE_ROOT))

    uvicorn.run(
        "backend.app:app",
        host=_DEFAULT_HOST,
        port=_DEFAULT_PORT,
        reload=True,
        reload_dirs=reload_dirs,
        reload_excludes=[".custom_plugins/*"],
    )


if __name__ == "__main__":
    main()
