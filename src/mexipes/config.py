from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from .env file into os.environ for litellm
load_dotenv()


class StageConfig(BaseModel):
    model: str
    temperature: float = 0.1
    max_retries: int = 3


class ImageQualityConfig(BaseModel):
    enabled: bool = True
    min_sharpness: float = 120.0
    min_brightness: float = 90.0
    max_brightness: float = 250.0


class Settings(BaseSettings):
    data_dir: Path = Path("./data")

    extraction: StageConfig = StageConfig(model="gemini/gemini-2.5-flash")
    metadata: StageConfig = StageConfig(model="gemini/gemini-2.5-flash")
    rewrite: StageConfig = StageConfig(
        model="gemini/gemini-2.5-pro", temperature=0.2
    )  # Defaulting to Gemini 2.5 Pro since user selected Gemini 3.5 Flash High/Pro models, but we can easily configure this in .env
    describe: StageConfig = StageConfig(model="gemini/gemini-2.5-flash")
    localize: StageConfig = StageConfig(model="gemini/gemini-2.5-flash", temperature=0.3)
    tagging: StageConfig = StageConfig(model="gemini/gemini-2.5-flash")
    substitution: StageConfig = StageConfig(model="gemini/gemini-2.5-flash")
    image_quality: ImageQualityConfig = ImageQualityConfig()

    model_config = SettingsConfigDict(env_prefix="MEXIPES_", env_file=".env", env_nested_delimiter="_", extra="ignore")


settings = Settings()
