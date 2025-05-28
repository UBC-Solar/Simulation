from pydantic import BaseModel
from pathlib import Path
import tomli
import tomli_w
from typing import Protocol, cast


class Settings(BaseModel):
    plot_timer_interval: int
    sunbeam_api_url: str
    sunbeam_path: str
    sunlink_path: str


class CommandSettings(BaseModel):
    sunbeam_up_cmd: str
    sunbeam_down_cmd: str
    sunlink_up_cmd: str
    sunlink_down_cmd: str
    telemetry_enable_cmd: str


class CommandSettingsProtocol(Protocol):
    @property
    def sunbeam_up_cmd(self) -> str: ...
    @property
    def sunbeam_down_cmd(self) -> str: ...
    @property
    def sunlink_up_cmd(self) -> str: ...
    @property
    def sunlink_down_cmd(self) -> str: ...
    @property
    def telemetry_enable_cmd(self) -> str: ...
    @sunbeam_up_cmd.setter
    def sunbeam_up_cmd(self, value: str): ...
    @sunbeam_down_cmd.setter
    def sunbeam_down_cmd(self, value: str): ...
    @sunlink_up_cmd.setter
    def sunlink_up_cmd(self, value: str): ...
    @sunlink_down_cmd.setter
    def sunlink_down_cmd(self, value: str): ...
    @telemetry_enable_cmd.setter
    def telemetry_enable_cmd(self, value: str): ...


class SettingsProtocol(Protocol):
    @property
    def plot_timer_interval(self) -> int: ...
    @property
    def sunbeam_api_url(self) -> str: ...
    @property
    def sunbeam_path(self) -> str: ...
    @property
    def sunlink_path(self) -> str: ...
    @plot_timer_interval.setter
    def plot_timer_interval(self, new_interval: int) -> None: ...
    @sunbeam_api_url.setter
    def sunbeam_api_url(self, new_url: str) -> None: ...
    @sunbeam_path.setter
    def sunbeam_path(self, new_path: str) -> None: ...
    @sunlink_path.setter
    def sunlink_path(self, new_path: str) -> None: ...


class PersistentSettings:
    def __init__(self, path: Path = Path(__file__).parent / "settings.toml"):
        self._path = path
        self._model = self._load()

    def _load(self) -> Settings:
        if self._path.exists():
            with self._path.open("rb") as f:
                data = tomli.load(f)
            return Settings(**data)
        else:
            return Settings()

    def save(self):
        with self._path.open("wb") as f:
            tomli_w.dump(self._model.model_dump(), f)

    def __getattr__(self, item):
        return getattr(self._model, item)

    def __setattr__(self, key, value):
        if key in {"_path", "_model"}:
            return super().__setattr__(key, value)
        setattr(self._model, key, value)
        self.save()


class PersistentCommandSettings:
    def __init__(self, path: Path = Path(__file__).parent / "commands.toml"):
        self._path = path
        self._model = self._load()

    def _load(self) -> CommandSettings:
        if self._path.exists():
            with self._path.open("rb") as f:
                data = tomli.load(f)
            return CommandSettings(**data)
        else:
            return CommandSettings()

    def save(self):
        with self._path.open("wb") as f:
            tomli_w.dump(self._model.model_dump(), f)

    def __getattr__(self, item):
        return getattr(self._model, item)

    def __setattr__(self, key, value):
        if key in {"_path", "_model"}:
            return super().__setattr__(key, value)
        setattr(self._model, key, value)
        self.save()


settings = cast(SettingsProtocol, PersistentSettings())
command_settings = cast(CommandSettingsProtocol, PersistentCommandSettings())
