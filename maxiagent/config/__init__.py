from .config import config_by_name, getenv

config_name: str | None = getenv("ENV")

current_config = config_by_name[config_name]
print(f"current_config: {current_config}")

__all__: list[str] = ["current_config"]