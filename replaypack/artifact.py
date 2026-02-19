"""Artifact system for .rpk file format.

Deterministic, versioned artifact format for replay recordings.
"""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
from pathlib import Path

from replaypack.core.storage import Recording


CURRENT_SCHEMA_VERSION = "1.0.0"


@dataclass
class ArtifactHeader:
    """Header for .rpk artifact files."""
    schema_version: str
    created_at: str  # ISO timestamp
    generator: str  # Tool that created the artifact
    checksum: str  # SHA256 of content
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArtifactHeader":
        return cls(**data)


@dataclass
class ArtifactMetadata:
    """Metadata for artifact."""
    recording_count: int
    step_count: int
    total_size_bytes: int
    compression: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class Artifact:
    """ReplayPack artifact (.rpk file).
    
    Human-readable JSON with stable ordering and versioned schema.
    """
    
    def __init__(
        self,
        recording: Recording,
        header: Optional[ArtifactHeader] = None,
        metadata: Optional[ArtifactMetadata] = None
    ):
        """Initialize artifact.
        
        Args:
            recording: The recording to package.
            header: Artifact header (auto-generated if None).
            metadata: Artifact metadata (auto-generated if None).
        """
        self.recording = recording
        self.header = header or self._generate_header(recording)
        self.metadata = metadata or self._generate_metadata(recording)
    
    def _generate_header(self, recording: Recording) -> ArtifactHeader:
        """Generate default header."""
        from datetime import datetime, timezone
        
        return ArtifactHeader(
            schema_version=CURRENT_SCHEMA_VERSION,
            created_at=datetime.now(timezone.utc).isoformat(),
            generator="replaypack/0.1.0",
            checksum=""  # Will be computed on save
        )
    
    def _generate_metadata(self, recording: Recording) -> ArtifactMetadata:
        """Generate metadata from recording."""
        return ArtifactMetadata(
            recording_count=1,
            step_count=len(recording.steps),
            total_size_bytes=0,  # Will be computed on save
            compression=None
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert artifact to dictionary."""
        return {
            "_header": self.header.to_dict(),
            "_metadata": self.metadata.to_dict(),
            "_schema_version": CURRENT_SCHEMA_VERSION,
            "recording": json.loads(self.recording.to_json()),
        }
    
    def to_json(self) -> str:
        """Serialize to canonical JSON."""
        # First get data with empty checksum
        data = self.to_dict()
        original_checksum = data["_header"]["checksum"]
        data["_header"]["checksum"] = ""
        
        # Compute checksum
        content = json.dumps(data, sort_keys=True, separators=(',', ':'))
        computed_checksum = hashlib.sha256(content.encode()).hexdigest()
        
        # Update header with checksum
        data["_header"]["checksum"] = computed_checksum
        self.header = self.header.__class__(**{**self.header.__dict__, "checksum": computed_checksum})
        
        # Re-serialize with checksum
        return json.dumps(data, indent=2, sort_keys=True)
    
    def save(self, path: Path | str) -> None:
        """Save artifact to file.
        
        Args:
            path: File path to save to.
        """
        path = Path(path)
        path.write_text(self.to_json(), encoding='utf-8')
    
    @classmethod
    def load(cls, path: Path | str) -> "Artifact":
        """Load artifact from file.
        
        Args:
            path: File path to load from.
            
        Returns:
            Loaded Artifact.
            
        Raises:
            ArtifactError: If file is corrupted or invalid.
        """
        path = Path(path)
        
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            raise ArtifactError(f"Invalid JSON: {e}")
        except FileNotFoundError:
            raise ArtifactError(f"File not found: {path}")
        
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Artifact":
        """Create artifact from dictionary.
        
        Args:
            data: Dictionary containing artifact data.
            
        Returns:
            Artifact instance.
            
        Raises:
            ArtifactError: If data is invalid.
        """
        # Validate schema version
        schema_version = data.get("_schema_version", "unknown")
        
        # Handle version migrations
        if schema_version != CURRENT_SCHEMA_VERSION:
            data = cls._migrate(data, schema_version)
        
        # Load recording
        recording_data = data.get("recording")
        if not recording_data:
            raise ArtifactError("Missing recording data")
        
        recording = Recording.from_json(json.dumps(recording_data))
        
        # Load header and metadata
        header = ArtifactHeader.from_dict(data.get("_header", {}))
        metadata = ArtifactMetadata(**data.get("_metadata", {}))
        
        return cls(recording=recording, header=header, metadata=metadata)
    
    @classmethod
    def _migrate(cls, data: Dict[str, Any], from_version: str) -> Dict[str, Any]:
        """Migrate data from older schema version.
        
        Args:
            data: Data to migrate.
            from_version: Version the data is in.
            
        Returns:
            Migrated data.
        """
        # Currently no migrations needed (v1.0.0 is first version)
        # Future versions will add migration logic here
        return data
    
    def verify_checksum(self) -> bool:
        """Verify artifact checksum.
        
        Returns:
            True if checksum is valid.
        """
        data = self.to_dict()
        stored_checksum = data["_header"]["checksum"]
        
        # Compute checksum without the checksum field
        header_copy = data["_header"].copy()
        header_copy["checksum"] = ""
        data_copy = {**data, "_header": header_copy}
        
        content = json.dumps(data_copy, sort_keys=True, separators=(',', ':'))
        computed_checksum = hashlib.sha256(content.encode()).hexdigest()
        
        return stored_checksum == computed_checksum


class ArtifactError(Exception):
    """Error loading or saving artifact."""
    pass


class ArtifactBundle:
    """Bundle multiple recordings into single artifact."""
    
    def __init__(self, artifacts: List[Artifact]):
        """Initialize bundle.
        
        Args:
            artifacts: List of artifacts to bundle.
        """
        self.artifacts = artifacts
    
    def save(self, path: Path | str) -> None:
        """Save bundle to file.
        
        Args:
            path: File path to save to.
        """
        path = Path(path)
        
        data = {
            "_type": "bundle",
            "_schema_version": CURRENT_SCHEMA_VERSION,
            "artifacts": [a.to_dict() for a in self.artifacts],
        }
        
        path.write_text(
            json.dumps(data, indent=2, sort_keys=True),
            encoding='utf-8'
        )
    
    @classmethod
    def load(cls, path: Path | str) -> "ArtifactBundle":
        """Load bundle from file.
        
        Args:
            path: File path to load from.
            
        Returns:
            Loaded ArtifactBundle.
        """
        path = Path(path)
        data = json.loads(path.read_text(encoding='utf-8'))
        
        artifacts = [Artifact.from_dict(a) for a in data.get("artifacts", [])]
        return cls(artifacts)
