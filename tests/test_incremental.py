"""Tests for incremental update tracker."""

import tempfile
from pathlib import Path

from research_rag.incremental import IncrementalTracker


class TestIncrementalTracker:
    """Test file change detection for incremental ingestion."""

    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.manifest = self.tmpdir / "manifest.json"
        self.tracker = IncrementalTracker(manifest_path=self.manifest)
        self.pdf1 = self.tmpdir / "paper1.pdf"
        self.pdf1.write_bytes(b"%PDF-1.4 fake content 1")
        self.pdf2 = self.tmpdir / "paper2.pdf"
        self.pdf2.write_bytes(b"%PDF-1.4 fake content 2")

    def test_new_file_is_changed(self):
        assert self.tracker.has_changed(self.pdf1) is True

    def test_mark_ingested(self):
        self.tracker.mark_ingested(self.pdf1)
        assert self.tracker.has_changed(self.pdf1) is False

    def test_file_change_detected(self):
        self.tracker.mark_ingested(self.pdf1)
        self.pdf1.write_bytes(b"%PDF-1.4 modified content")
        assert self.tracker.has_changed(self.pdf1) is True

    def test_filter_changed(self):
        self.tracker.mark_ingested(self.pdf1)
        self.pdf2.write_bytes(b"%PDF-1.4 modified 2")
        changed = self.tracker.filter_changed([self.pdf1, self.pdf2])
        assert len(changed) == 1
        assert changed[0] == self.pdf2

    def test_persistence(self):
        self.tracker.mark_ingested(self.pdf1)
        tracker2 = IncrementalTracker(manifest_path=self.manifest)
        assert tracker2.has_changed(self.pdf1) is False

    def test_remove(self):
        self.tracker.mark_ingested(self.pdf1)
        self.tracker.remove(self.pdf1)
        assert self.tracker.has_changed(self.pdf1) is True

    def test_tracked_count(self):
        self.tracker.mark_ingested(self.pdf1)
        self.tracker.mark_ingested(self.pdf2)
        assert self.tracker.tracked_count == 2
