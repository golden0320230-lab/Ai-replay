"""Test Skill 5: Structured Diff Engine.

Adversarial test suite validating:
- Line diff
- Word diff
- JSON pointer diff
- Hunk grouping
- Large file handling
- Deeply nested JSON
"""

import json
import time

import pytest

from replaypack.diff_engine import DiffEngine, JSONDiff


class TestLineDiff:
    """Test line-by-line diff."""
    
    def test_simple_line_diff(self):
        """Basic line diff works."""
        engine = DiffEngine()
        
        old = "line1\nline2\nline3"
        new = "line1\nmodified\nline3"
        
        hunks = engine.line_diff(old, new)
        
        assert len(hunks) > 0
    
    def test_added_lines(self):
        """Added lines are detected."""
        engine = DiffEngine()
        
        old = "line1\nline2"
        new = "line1\nnew_line\nline2"
        
        hunks = engine.line_diff(old, new)
        
        # Should have at least one hunk with added line
        assert len(hunks) >= 1


class TestWordDiff:
    """Test word-by-word diff."""
    
    def test_simple_word_diff(self):
        """Basic word diff works."""
        engine = DiffEngine()
        
        old = "the quick brown fox"
        new = "the slow brown fox"
        
        result = engine.word_diff(old, new)
        
        # Should show 'quick' deleted and 'slow' inserted
        assert any(op == 'delete' and 'quick' in text for op, text in result)
        assert any(op == 'insert' and 'slow' in text for op, text in result)
    
    def test_unchanged_words(self):
        """Unchanged words are marked as equal."""
        engine = DiffEngine()
        
        old = "hello world"
        new = "hello world"
        
        result = engine.word_diff(old, new)
        
        assert all(op == 'equal' for op, text in result)


class TestJSONDiff:
    """Test JSON diff with path information."""
    
    def test_simple_json_diff(self):
        """Basic JSON diff works."""
        engine = DiffEngine()
        
        old = {"name": "Alice", "age": 30}
        new = {"name": "Alice", "age": 31}
        
        diffs = engine.json_diff(old, new)
        
        assert len(diffs) == 1
        assert diffs[0].path == "/age"
        assert diffs[0].op == "replace"
        assert diffs[0].old_value == 30
        assert diffs[0].new_value == 31
    
    def test_nested_json_diff(self):
        """Nested JSON diff produces correct paths."""
        engine = DiffEngine()
        
        old = {"user": {"profile": {"name": "Alice"}}}
        new = {"user": {"profile": {"name": "Bob"}}}
        
        diffs = engine.json_diff(old, new)
        
        assert len(diffs) == 1
        assert diffs[0].path == "/user/profile/name"
    
    def test_deeply_nested_json(self):
        """JSON nested >10 levels is handled."""
        engine = DiffEngine()
        
        # Create deeply nested structure
        old = {"value": 0}
        new = {"value": 0}
        for i in range(15):
            old = {"level": old}
            new = {"level": new}
        
        # Modify the deepest value
        new["level"]["level"]["level"]["level"]["level"]["level"]["level"]["level"]["level"]["level"]["level"]["level"]["level"]["level"]["level"]["value"] = 1
        
        diffs = engine.json_diff(old, new)
        
        assert len(diffs) == 1
        assert "value" in diffs[0].path
    
    def test_array_diff(self):
        """Array differences are detected."""
        engine = DiffEngine()
        
        old = {"items": [1, 2, 3]}
        new = {"items": [1, 2, 4]}
        
        diffs = engine.json_diff(old, new)
        
        assert len(diffs) == 1
        assert diffs[0].path == "/items/2"
        assert diffs[0].old_value == 3
        assert diffs[0].new_value == 4


class TestPerformance:
    """Test performance requirements."""
    
    def test_medium_run_performance(self):
        """Diff completes in <500ms for medium runs."""
        engine = DiffEngine()
        
        # Create medium-sized JSON structures
        old = {"items": [{"id": i, "data": f"value_{i}"} for i in range(1000)]}
        new = {"items": [{"id": i, "data": f"value_{i}"} for i in range(1000)]}
        new["items"][500]["data"] = "modified"
        
        start = time.time()
        diffs = engine.json_diff(old, new)
        duration = time.time() - start
        
        assert duration < 0.5  # 500ms
        assert len(diffs) == 1


class TestHunkGrouping:
    """Test hunk grouping functionality."""
    
    def test_hunk_formatting(self):
        """Hunks can be formatted as unified diff."""
        engine = DiffEngine()
        
        old = "line1\nline2\nline3"
        new = "line1\nmodified\nline3"
        
        hunks = engine.line_diff(old, new)
        formatted = engine.format_diff(hunks, "old.txt", "new.txt")
        
        assert "--- old.txt" in formatted
        assert "+++ new.txt" in formatted
        assert "@@" in formatted
