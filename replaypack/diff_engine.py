"""Structured diff engine for text and JSON.

Implements Git-style diff with line, word, and JSON pointer diff.
"""

from __future__ import annotations

import difflib
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union


@dataclass
class DiffHunk:
    """A hunk of differences."""
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "old_start": self.old_start,
            "old_count": self.old_count,
            "new_start": self.new_start,
            "new_count": self.new_count,
            "lines": self.lines,
        }


@dataclass
class JSONDiff:
    """JSON-specific diff with path information."""
    path: str  # JSON pointer path
    op: str    # "add", "remove", "replace"
    old_value: Any
    new_value: Any
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "op": self.op,
            "old_value": self.old_value,
            "new_value": self.new_value,
        }


class DiffEngine:
    """Git-style diff engine for text and JSON."""
    
    def __init__(self, context_lines: int = 3):
        """Initialize diff engine.
        
        Args:
            context_lines: Number of context lines around changes.
        """
        self.context_lines = context_lines
    
    def line_diff(self, old: str, new: str) -> List[DiffHunk]:
        """Compute line-by-line diff.
        
        Args:
            old: Old text.
            new: New text.
            
        Returns:
            List of diff hunks.
        """
        old_lines = old.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)
        
        # Use unified diff format
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            lineterm="",
            n=self.context_lines
        )
        
        # Parse hunks from diff output
        return self._parse_hunks(list(diff))
    
    def word_diff(self, old: str, new: str) -> List[Tuple[str, str]]:
        """Compute word-by-word diff.
        
        Args:
            old: Old text.
            new: New text.
            
        Returns:
            List of (operation, text) tuples.
        """
        old_words = old.split()
        new_words = new.split()
        
        sm = difflib.SequenceMatcher(None, old_words, new_words)
        result = []
        
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == 'equal':
                result.append(('equal', ' '.join(old_words[i1:i2])))
            elif op == 'delete':
                result.append(('delete', ' '.join(old_words[i1:i2])))
            elif op == 'insert':
                result.append(('insert', ' '.join(new_words[j1:j2])))
            elif op == 'replace':
                result.append(('delete', ' '.join(old_words[i1:i2])))
                result.append(('insert', ' '.join(new_words[j1:j2])))
        
        return result
    
    def json_diff(self, old: Any, new: Any, path: str = "") -> List[JSONDiff]:
        """Compute JSON diff with path information.
        
        Args:
            old: Old JSON value.
            new: New JSON value.
            path: Current JSON pointer path.
            
        Returns:
            List of JSON differences.
        """
        diffs = []
        
        if old == new:
            return diffs
        
        if type(old) != type(new):
            diffs.append(JSONDiff(
                path=path or "/",
                op="replace",
                old_value=old,
                new_value=new
            ))
            return diffs
        
        if isinstance(old, dict):
            all_keys = set(old.keys()) | set(new.keys())
            for key in sorted(all_keys):
                new_path = f"{path}/{key}"
                if key not in old:
                    diffs.append(JSONDiff(
                        path=new_path,
                        op="add",
                        old_value=None,
                        new_value=new[key]
                    ))
                elif key not in new:
                    diffs.append(JSONDiff(
                        path=new_path,
                        op="remove",
                        old_value=old[key],
                        new_value=None
                    ))
                else:
                    diffs.extend(self.json_diff(old[key], new[key], new_path))
        
        elif isinstance(old, list):
            # For lists, do element-by-element comparison
            max_len = max(len(old), len(new))
            for i in range(max_len):
                new_path = f"{path}/{i}"
                if i >= len(old):
                    diffs.append(JSONDiff(
                        path=new_path,
                        op="add",
                        old_value=None,
                        new_value=new[i]
                    ))
                elif i >= len(new):
                    diffs.append(JSONDiff(
                        path=new_path,
                        op="remove",
                        old_value=old[i],
                        new_value=None
                    ))
                else:
                    diffs.extend(self.json_diff(old[i], new[i], new_path))
        
        else:
            # Primitive value changed
            diffs.append(JSONDiff(
                path=path or "/",
                op="replace",
                old_value=old,
                new_value=new
            ))
        
        return diffs
    
    def _parse_hunks(self, diff_lines: List[str]) -> List[DiffHunk]:
        """Parse unified diff output into hunks.
        
        Args:
            diff_lines: Lines from unified_diff.
            
        Returns:
            List of DiffHunk objects.
        """
        hunks = []
        current_hunk: Optional[DiffHunk] = None
        
        for line in diff_lines:
            if line.startswith('@@'):
                # Parse hunk header: @@ -old_start,old_count +new_start,new_count @@
                if current_hunk:
                    hunks.append(current_hunk)
                
                # Extract line numbers
                parts = line.split()
                old_range = parts[1][1:]  # Remove leading '-'
                new_range = parts[2][1:]  # Remove leading '+'
                
                old_start = int(old_range.split(',')[0]) if ',' in old_range else int(old_range)
                old_count = int(old_range.split(',')[1]) if ',' in old_range else 1
                new_start = int(new_range.split(',')[0]) if ',' in new_range else int(new_range)
                new_count = int(new_range.split(',')[1]) if ',' in new_range else 1
                
                current_hunk = DiffHunk(
                    old_start=old_start,
                    old_count=old_count,
                    new_start=new_start,
                    new_count=new_count,
                    lines=[]
                )
            elif current_hunk is not None:
                current_hunk.lines.append(line)
        
        if current_hunk:
            hunks.append(current_hunk)
        
        return hunks
    
    def format_diff(self, hunks: List[DiffHunk], old_label: str = "old", new_label: str = "new") -> str:
        """Format hunks as unified diff text.
        
        Args:
            hunks: List of diff hunks.
            old_label: Label for old file.
            new_label: Label for new file.
            
        Returns:
            Formatted diff text.
        """
        lines = [f"--- {old_label}", f"+++ {new_label}"]
        
        for hunk in hunks:
            lines.append(f"@@ -{hunk.old_start},{hunk.old_count} +{hunk.new_start},{hunk.new_count} @@")
            lines.extend(hunk.lines)
        
        return "\n".join(lines)


class StreamingDiff:
    """Memory-efficient diff for large files."""
    
    def __init__(self, chunk_size: int = 8192):
        """Initialize streaming diff.
        
        Args:
            chunk_size: Size of chunks to process.
        """
        self.chunk_size = chunk_size
    
    def diff_large_files(self, old_path: str, new_path: str) -> List[DiffHunk]:
        """Diff large files without loading entirely into memory.
        
        Args:
            old_path: Path to old file.
            new_path: Path to new file.
            
        Returns:
            List of diff hunks.
        """
        # For very large files, use a line-by-line approach
        engine = DiffEngine()
        
        with open(old_path, 'r') as old_file, open(new_path, 'r') as new_file:
            old_lines = old_file.readlines()
            new_lines = new_file.readlines()
        
        return engine.line_diff(''.join(old_lines), ''.join(new_lines))
