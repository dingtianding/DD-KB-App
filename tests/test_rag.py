import tempfile
import unittest
from pathlib import Path

from rag.generation import _output_text
from rag.retrieval import SearchIndex
from rag.retrieval import chunk_markdown


class RetrievalTests(unittest.TestCase):
    def test_relevant_document_ranks_first(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "python.md").write_text("# Python\n\n## Testing\nUse pytest fixtures for isolation.")
            (root / "aws.md").write_text("# AWS\n\nS3 stores objects in buckets.")
            results = SearchIndex(root).search("pytest testing")
            self.assertEqual(results[0]["path"], "python.md")
            self.assertEqual(results[0]["section"], "Testing")

    def test_empty_query_returns_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(SearchIndex(Path(directory)).search("  "), [])

    def test_search_refreshes_after_markdown_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            note = root / "note.md"
            note.write_text("# Notes\n\nA deployment checklist.")
            index = SearchIndex(root)
            self.assertEqual(index.search("kubernetes"), [])
            note.write_text("# Notes\n\nA kubernetes deployment checklist.")
            self.assertEqual(index.search("kubernetes")[0]["path"], "note.md")

    def test_refresh_detects_added_and_removed_documents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index = SearchIndex(root)
            note = root / "new.md"
            note.write_text("# New\n\nUnique hummingbird fact.")
            self.assertEqual(index.search("hummingbird")[0]["path"], "new.md")
            note.unlink()
            self.assertEqual(index.search("hummingbird"), [])

    def test_nested_headings_keep_parent_context(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            note = root / "stories.md"
            note.write_text("# Stories\n\n## China launch\n\n### Action\n\nBuilt rotating mirrors.")
            chunks = chunk_markdown(note, root)
            self.assertEqual(chunks[-1].section, "China launch › Action")

    def test_inbox_and_templates_are_not_indexed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Inbox").mkdir()
            (root / "Templates").mkdir()
            (root / "Inbox" / "scratch.md").write_text("Secret temporary hummingbird note")
            (root / "Templates" / "prompt.md").write_text("Hummingbird template")
            (root / "durable.md").write_text("# Durable\n\nBackend idempotency.")
            index = SearchIndex(root)
            self.assertEqual(index.search("hummingbird"), [])
            self.assertEqual(index.search("idempotency")[0]["path"], "durable.md")

    def test_hidden_and_obsidian_files_are_not_indexed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".obsidian").mkdir()
            (root / ".private").mkdir()
            (root / ".obsidian" / "plugin.md").write_text("Hidden hummingbird plugin")
            (root / ".private" / "scratch.md").write_text("Hidden hummingbird scratch")
            (root / "public.md").write_text("# Public\n\nDurable kestrel note.")
            index = SearchIndex(root)
            self.assertEqual(index.search("hummingbird"), [])
            self.assertEqual(index.search("kestrel")[0]["path"], "public.md")


class GenerationTests(unittest.TestCase):
    def test_collects_text_across_response_items(self):
        response = {"output": [
            {"type": "reasoning", "content": []},
            {"type": "message", "content": [{"type": "output_text", "text": "First"}]},
            {"type": "message", "content": [{"type": "output_text", "text": "Second"}]},
        ]}
        self.assertEqual(_output_text(response), "First\nSecond")


if __name__ == "__main__":
    unittest.main()
