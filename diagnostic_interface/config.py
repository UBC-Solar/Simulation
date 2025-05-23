from pydantic import BaseModel
from pathlib import Path
import tomli
import tomli_w


class Settings(BaseModel):
    plot_timer_interval: int
    sunbeam_api_url: str
    sunbeam_path: str


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


settings = PersistentSettings()
