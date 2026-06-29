import contextlib
import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from mexipes.schemas.publication import PublicationMetadata
from mexipes.schemas.recipe import RecipeStatus

T = TypeVar("T", bound=BaseModel)


class RecipeStore:
    """Manages file-based persistence and recipe pipeline state."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "staging").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "publications").mkdir(parents=True, exist_ok=True)

    def get_publication_dir(self, publication_id: int) -> Path:
        publication_dir = self.data_dir / "publications" / str(publication_id)
        publication_dir.mkdir(parents=True, exist_ok=True)
        return publication_dir

    def get_recipe_dir(self, publication_id: int, recipe_id: int) -> Path:
        recipe_dir = self.get_publication_dir(publication_id) / "recipes" / str(recipe_id)
        recipe_dir.mkdir(parents=True, exist_ok=True)
        return recipe_dir

    def get_images_dir(self, publication_id: int, recipe_id: int) -> Path:
        images_dir = self.get_recipe_dir(publication_id, recipe_id) / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        return images_dir

    def save_publication_metadata(self, publication_id: int, metadata: PublicationMetadata) -> None:
        publication_dir = self.get_publication_dir(publication_id)
        file_path = publication_dir / "metadata.json"
        file_path.write_text(metadata.model_dump_json(indent=4), encoding="utf-8")

    def load_publication_metadata(self, publication_id: int) -> PublicationMetadata | None:
        publication_dir = self.get_publication_dir(publication_id)
        file_path = publication_dir / "metadata.json"
        if not file_path.exists():
            return None
        return PublicationMetadata.model_validate_json(file_path.read_text(encoding="utf-8"))

    def save_stage_output(self, publication_id: int, recipe_id: int, stage_name: str, data: BaseModel) -> None:
        recipe_dir = self.get_recipe_dir(publication_id, recipe_id)
        file_path = recipe_dir / f"{stage_name}.json"
        file_path.write_text(data.model_dump_json(indent=4), encoding="utf-8")

    def load_stage_output(self, publication_id: int, recipe_id: int, stage_name: str, model_cls: type[T]) -> T | None:
        recipe_dir = self.get_recipe_dir(publication_id, recipe_id)
        file_path = recipe_dir / f"{stage_name}.json"
        if not file_path.exists():
            return None
        try:
            return model_cls.model_validate_json(file_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def get_status(self, publication_id: int, recipe_id: int) -> RecipeStatus:
        recipe_dir = self.get_recipe_dir(publication_id, recipe_id)
        status_file = recipe_dir / "status.json"
        if not status_file.exists():
            return RecipeStatus.EXTRACTED
        try:
            data = json.loads(status_file.read_text(encoding="utf-8"))
            return RecipeStatus(data["status"])
        except Exception:
            return RecipeStatus.EXTRACTED

    def set_status(self, publication_id: int, recipe_id: int, status: RecipeStatus, error: str | None = None) -> None:
        recipe_dir = self.get_recipe_dir(publication_id, recipe_id)
        status_file = recipe_dir / "status.json"
        status_data = {
            "status": status.value,
            "error": error,
        }
        status_file.write_text(json.dumps(status_data, indent=4), encoding="utf-8")

    def find_recipes_at_status(self, status: RecipeStatus) -> list[tuple[int, int]]:
        results = []
        publications_dir = self.data_dir / "publications"
        if not publications_dir.exists():
            return results
        for pub_path in sorted(publications_dir.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 999999):
            if not pub_path.is_dir() or not pub_path.name.isdigit():
                continue
            publication_id = int(pub_path.name)
            recipes_dir = pub_path / "recipes"
            if not recipes_dir.exists():
                continue
            for recipe_path in sorted(recipes_dir.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 999999):
                if not recipe_path.is_dir() or not recipe_path.name.isdigit():
                    continue
                recipe_id = int(recipe_path.name)
                if self.get_status(publication_id, recipe_id) == status:
                    results.append((publication_id, recipe_id))
        return results

    def find_all_recipes(self) -> list[tuple[int, int]]:
        results = []
        publications_dir = self.data_dir / "publications"
        if not publications_dir.exists():
            return results
        for pub_path in sorted(publications_dir.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 999999):
            if not pub_path.is_dir() or not pub_path.name.isdigit():
                continue
            publication_id = int(pub_path.name)
            recipes_dir = pub_path / "recipes"
            if not recipes_dir.exists():
                continue
            for recipe_path in sorted(recipes_dir.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 999999):
                if not recipe_path.is_dir() or not recipe_path.name.isdigit():
                    continue
                recipe_id = int(recipe_path.name)
                results.append((publication_id, recipe_id))
        return results

    def get_next_recipe_id(self, publication_id: int) -> int:
        recipes_dir = self.get_publication_dir(publication_id) / "recipes"
        if not recipes_dir.exists():
            return 1
        max_id = 0
        for entry in recipes_dir.iterdir():
            if entry.is_dir() and entry.name.isdigit():
                with contextlib.suppress(ValueError):
                    max_id = max(max_id, int(entry.name))
        return max_id + 1

    def get_next_publication_id(self) -> int:
        publications_dir = self.data_dir / "publications"
        max_id = 0
        for entry in publications_dir.iterdir():
            if entry.is_dir() and entry.name.isdigit():
                with contextlib.suppress(ValueError):
                    max_id = max(max_id, int(entry.name))
        return max_id + 1
