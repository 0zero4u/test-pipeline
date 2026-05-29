"""Incremental update support for Research RAG."""

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class IncrementalTracker:
    """Tracks file hashes to detect changed PDFs for incremental re-ingestion.

    Maintains a manifest of file_path → sha256 hashes. On re-ingest,
    only files with changed hashes are processed.
    """

    def __init__(self, manifest_path: Optional[Path] = None):
        self.manifest_path = manifest_path or Path("./data/ingestion_manifest.json")
        self._manifest: dict[str, str] = {}
        if self.manifest_path.exists():
            self._load()

    def has_changed(self, file_path: Path) -> bool:
        """Check if a file has changed since last ingestion.

        Args:
            file_path: Path to PDF file.

        Returns:
            True if file is new or changed, False if unchanged.
        """
        key = str(file_path.resolve())
        current_hash = self._hash_file(file_path)
        old_hash = self._manifest.get(key)
        return current_hash != old_hash

    def mark_ingested(self, file_path: Path) -> None:
        """Record the current hash after successful ingestion.

        Args:
            file_path: Path to PDF file that was ingested.
        """
        key = str(file_path.resolve())
        self._manifest[key] = self._hash_file(file_path)
        self._save()

    def filter_changed(self, file_paths: list[Path]) -> list[Path]:
        """Filter a list of files to only those that are new or changed.

        Args:
            file_paths: List of PDF paths to check.

        Returns:
            List of paths that need (re-)ingestion.
        """
        changed = [fp for fp in file_paths if self.has_changed(fp)]
        logger.info(
            "Incremental check: %d/%d files need ingestion",
            len(changed),
            len(file_paths),
        )
        return changed

    def remove(self, file_path: Path) -> None:
        """Remove a file from the manifest.

        Args:
            file_path: Path to remove.
        """
        key = str(file_path.resolve())
        self._manifest.pop(key, None)
        self._save()

    @property
    def tracked_count(self) -> int:
        return len(self._manifest)

    def _hash_file(self, file_path: Path) -> str:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()[:16]

    def _save(self) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.manifest_path, "w") as f:
            json.dump(self._manifest, f, indent=2)

    def _load(self) -> None:
        try:
            with open(self.manifest_path) as f:
                self._manifest = json.load(f)
            logger.info("Loaded manifest with %d tracked files", len(self._manifest))
        except Exception as exc:
            logger.warning("Failed to load manifest: %s", exc)
            self._manifest = {}
