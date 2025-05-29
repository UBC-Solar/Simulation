from __future__ import annotations
from pathlib import Path
from typing import Any, Generic, Type, TypeVar

import tomli
import tomli_w
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

T = TypeVar("T", bound=BaseModel)


class PersistentConfig(Generic[T]):
    """
    Generic wrapper around a Pydantic BaseModel that
    loads from / saves to a TOML file, with atomic writes
    and auto-saving on attribute mutation.
    """
    def __init__(self, model_cls: Type[T], path: Path):
        self._model_cls = model_cls
        self._path = path
        self._model: T = self._load()

    def _load(self) -> T:
        if self._path.exists():
            with self._path.open("rb") as f:
                data = tomli.load(f)

                return self._model_cls(**data)

        # if doesn't already, exist, use default
        return self._model_cls()

    def save(self) -> None:
        # atomic write: write to .tmp then replace
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tomli_w.dump(self._model.model_dump(), tmp.open("wb"))
        tmp.replace(self._path)

    def __getattr__(self, name: str) -> Any:
        # proxy all unknown attrs to the model
        return getattr(self._model, name)

    def __setattr__(self, name: str, value: Any) -> None:
        # internal attributes bypass proxy
        if name in {"_model", "_model_cls", "_path"}:
            super().__setattr__(name, value)
            return

        # if model has the field, set/save; else normal setattr
        if name in self._model.model_fields:
            setattr(self._model, name, value)
            self.save()
        else:
            super().__setattr__(name, value)

class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    plot_timer_interval: int = Field(5, gt=0, description="seconds between plot refresh")
    sunbeam_api_url: str = Field(..., description="Base URL for Sunbeam API")
    sunbeam_path: str = Field(..., description="Filesystem path to Sunbeam project")
    sunlink_path: str = Field(..., description="Filesystem path to Sunlink project")


class CommandSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sunbeam_up_cmd: str = Field(..., description="docker-compose up command for Sunbeam")
    sunbeam_down_cmd: str = Field(..., description="docker-compose down command for Sunbeam")
    sunlink_up_cmd: str = Field(..., description="docker-compose up command for Sunlink")
    sunlink_down_cmd: str = Field(..., description="docker-compose down command for Sunlink")
    telemetry_enable_cmd: str = Field(..., description="command to enable the telemetry link")


BASE = Path(__file__).parent

settings = PersistentConfig(Settings, BASE / "settings.toml")
command_settings = PersistentConfig(CommandSettings, BASE / "commands.toml")
