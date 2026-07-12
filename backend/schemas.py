"""Request bodies for campaign-rpg-studio API routes."""

from pydantic import BaseModel, Field


class CommandRequest(BaseModel):
    line: str = Field(min_length=1)


class ActiveAgentRequest(BaseModel):
    name_or_id: str = Field(min_length=1)


class ActiveAreaRequest(BaseModel):
    area_id: str = Field(min_length=1)


class TurnRequest(BaseModel):
    agent_id: str | None = None
    include_examples: bool | None = None


class ManualTurnRequest(BaseModel):
    agent_id: str | None = None
    compound_turn: dict[str, object]


class EventRequest(BaseModel):
    text: str = Field(min_length=1)
    agent_ids: list[str] | None = None


class CreateAreaRequest(BaseModel):
    area_id: str = Field(min_length=1)
    description: str = ""
    width: int = Field(default=5, ge=1)
    height: int = Field(default=5, ge=1)


class EditAreaRequest(BaseModel):
    area_id: str = Field(min_length=1)
    description: str | None = None
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)


class DeleteAreaRequest(BaseModel):
    area_id: str = Field(min_length=1)


class PromptBlockItem(BaseModel):
    type: str = Field(min_length=1)
    name: str | None = None
    content: str | None = None
    options: dict[str, object] | None = None


class PromptBlocksRequest(BaseModel):
    blocks: list[PromptBlockItem] = Field(min_length=1)


class PromptBlocksPreviewRequest(BaseModel):
    blocks: list[PromptBlockItem] = Field(min_length=1)
    agent_id: str | None = None


class VisionUnitsRequest(BaseModel):
    units: str = ""
    units_per_tile: int | None = Field(default=None, ge=1)


class CoordinateModeRequest(BaseModel):
    mode: str = Field(min_length=1)


class LlmSettingsRequest(BaseModel):
    api_key: str | None = None
    model: str | None = None


class EntityPrivateDataRequest(BaseModel):
    entity_id: str = Field(min_length=1)
    private_data: str = ""


class EntityTemplateSaveRequest(BaseModel):
    kind: str = Field(min_length=1)
    entity_id: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    include_memory: bool = False


class EntityTemplateSpawnRequest(BaseModel):
    position: list[int] = Field(min_length=2, max_length=2)
    area_id: str | None = None


class EntityTemplateImportRequest(BaseModel):
    filename: str = Field(min_length=1)
    template: dict[str, object]


class EntityTemplateSpawnFromBodyRequest(BaseModel):
    template: dict[str, object]
    position: list[int] = Field(min_length=2, max_length=2)
    area_id: str | None = None


class CreateDecorationRequest(BaseModel):
    kind: str = Field(min_length=1)
    image: str = Field(min_length=1)
    area_id: str | None = None
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    z_index: int | None = None
    repeat: str = "repeat"
    decoration_id: str | None = None
    label: str = "decor"


class UpdateDecorationRequest(BaseModel):
    decoration_id: str = Field(min_length=1)
    area_id: str | None = None
    image: str | None = None
    x: int | None = None
    y: int | None = None
    width: int | None = None
    height: int | None = None
    z_index: int | None = None
    repeat: str | None = None


class DeleteDecorationRequest(BaseModel):
    decoration_id: str = Field(min_length=1)
    area_id: str | None = None


class ReorderDecorationRequest(BaseModel):
    decoration_id: str = Field(min_length=1)
    direction: str = Field(min_length=1)
    area_id: str | None = None
