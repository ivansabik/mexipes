import contextlib
import fcntl
import json
import logging
import os
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from mexipes.schemas.publication import PublicationMetadata
from mexipes.schemas.recipe import RecipeStatus

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)

_STATUS_INDEX_FILENAME = "_index.json"
_NEXT_RECIPE_ID_FILENAME = "_next_id.txt"


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

    def load_publication_info(self, publication_id: int) -> dict | None:
        """Load ingest-time ``publication_info.json`` (original filename, md5, etc.)."""
        file_path = self.get_publication_dir(publication_id) / "publication_info.json"
        if not file_path.exists():
            return None
        try:
            return json.loads(file_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def publication_export_info(self, publication_id: int) -> dict:
        """Summary for consolidated export: source file path and document title."""
        info = self.load_publication_info(publication_id)
        metadata = self.load_publication_metadata(publication_id)
        original_filename = info.get("original_filename") if info else None
        rel_path = f"publications/{publication_id}/source.pdf"
        return {
            "id": publication_id,
            "file": original_filename or rel_path,
            "source_pdf": rel_path,
            "title": metadata.document_title if metadata else None,
        }

    def save_stage_output(self, publication_id: int, recipe_id: int, stage_name: str, data: BaseModel) -> None:
        recipe_dir = self.get_recipe_dir(publication_id, recipe_id)
        file_path = recipe_dir / f"{stage_name}.json"
        file_path.write_text(data.model_dump_json(indent=4), encoding="utf-8")

    def load_stage_output(
        self,
        publication_id: int,
        recipe_id: int,
        stage_name: str,
        model_cls: type[T],
        *,
        strict: bool = False,
    ) -> T | None:
        recipe_dir = self.get_recipe_dir(publication_id, recipe_id)
        file_path = recipe_dir / f"{stage_name}.json"
        if not file_path.exists():
            return None
        try:
            return model_cls.model_validate_json(file_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("Failed to load %s: %s", file_path, e)
            if strict:
                raise
            return None

    def _status_index_path(self, publication_id: int) -> Path:
        return self.get_publication_dir(publication_id) / _STATUS_INDEX_FILENAME

    def _read_status_from_disk(self, publication_id: int, recipe_id: int) -> RecipeStatus:
        """Read recipe status from status.json without creating directories."""
        status_file = self.data_dir / "publications" / str(publication_id) / "recipes" / str(recipe_id) / "status.json"
        if not status_file.exists():
            return RecipeStatus.EXTRACTED
        try:
            data = json.loads(status_file.read_text(encoding="utf-8"))
            return RecipeStatus(data["status"])
        except Exception:
            return RecipeStatus.EXTRACTED

    def _save_status_index(self, publication_id: int, index: dict[str, str]) -> None:
        index_path = self._status_index_path(publication_id)
        tmp_path = index_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(index, indent=4, sort_keys=True), encoding="utf-8")
        tmp_path.replace(index_path)

    def rebuild_status_index(self, publication_id: int) -> dict[str, str]:
        """Rebuild publication _index.json by scanning recipe status.json files."""
        index: dict[str, str] = {}
        recipes_dir = self.get_publication_dir(publication_id) / "recipes"
        if recipes_dir.exists():
            for recipe_path in recipes_dir.iterdir():
                if recipe_path.is_dir() and recipe_path.name.isdigit():
                    recipe_id = int(recipe_path.name)
                    index[str(recipe_id)] = self._read_status_from_disk(publication_id, recipe_id).value
        self._save_status_index(publication_id, index)
        return index

    def load_status_index(self, publication_id: int) -> dict[str, str]:
        """Load publication status index, rebuilding from disk when missing or corrupt."""
        index_path = self._status_index_path(publication_id)
        if not index_path.exists():
            return self.rebuild_status_index(publication_id)
        try:
            return json.loads(index_path.read_text(encoding="utf-8"))
        except Exception:
            logger.warning("Corrupt status index for publication %s; rebuilding", publication_id)
            return self.rebuild_status_index(publication_id)

    def get_status(self, publication_id: int, recipe_id: int) -> RecipeStatus:
        return self._read_status_from_disk(publication_id, recipe_id)

    def set_status(self, publication_id: int, recipe_id: int, status: RecipeStatus, error: str | None = None) -> None:
        recipe_dir = self.get_recipe_dir(publication_id, recipe_id)
        status_file = recipe_dir / "status.json"
        status_data = {
            "status": status.value,
            "error": error,
        }
        status_file.write_text(json.dumps(status_data, indent=4), encoding="utf-8")

        index = self.load_status_index(publication_id)
        index[str(recipe_id)] = status.value
        self._save_status_index(publication_id, index)

    def find_recipes_at_status(self, status: RecipeStatus) -> list[tuple[int, int]]:
        results = []
        publications_dir = self.data_dir / "publications"
        if not publications_dir.exists():
            return results
        for pub_path in sorted(publications_dir.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 999999):
            if not pub_path.is_dir() or not pub_path.name.isdigit():
                continue
            publication_id = int(pub_path.name)
            index = self.load_status_index(publication_id)
            for recipe_id_str, status_str in index.items():
                if not recipe_id_str.isdigit():
                    continue
                try:
                    if RecipeStatus(status_str) == status:
                        results.append((publication_id, int(recipe_id_str)))
                except ValueError:
                    continue
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

    def _max_recipe_id(self, publication_id: int) -> int:
        recipes_dir = self.get_publication_dir(publication_id) / "recipes"
        if not recipes_dir.exists():
            return 0
        max_id = 0
        for entry in recipes_dir.iterdir():
            if entry.is_dir() and entry.name.isdigit():
                with contextlib.suppress(ValueError):
                    max_id = max(max_id, int(entry.name))
        return max_id

    def get_next_recipe_id(self, publication_id: int) -> int:
        """Allocate the next recipe ID atomically using a locked counter file."""
        pub_dir = self.get_publication_dir(publication_id)
        (pub_dir / "recipes").mkdir(parents=True, exist_ok=True)
        counter_path = pub_dir / _NEXT_RECIPE_ID_FILENAME

        with open(counter_path, "a+", encoding="utf-8") as counter_file:
            fcntl.flock(counter_file.fileno(), fcntl.LOCK_EX)
            try:
                counter_file.seek(0)
                raw = counter_file.read().strip()
                scanned_next = max(self._max_recipe_id(publication_id) + 1, 1)
                if raw:
                    try:
                        next_id = max(int(raw), scanned_next)
                    except ValueError:
                        next_id = scanned_next
                else:
                    next_id = scanned_next

                counter_file.seek(0)
                counter_file.truncate()
                counter_file.write(str(next_id + 1))
                counter_file.flush()
                os.fsync(counter_file.fileno())
                return next_id
            finally:
                fcntl.flock(counter_file.fileno(), fcntl.LOCK_UN)

    def get_next_publication_id(self) -> int:
        publications_dir = self.data_dir / "publications"
        max_id = 0
        for entry in publications_dir.iterdir():
            if entry.is_dir() and entry.name.isdigit():
                with contextlib.suppress(ValueError):
                    max_id = max(max_id, int(entry.name))
        return max_id + 1
