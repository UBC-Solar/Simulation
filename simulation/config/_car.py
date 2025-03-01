from pydantic import BaseModel, ConfigDict


class CarConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str

