"""StackFrame representation for memory profiling."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class StackFrame:
    """Represents a single execution call site in a stack trace."""

    name: str
    filename: str = "<unknown>"
    line_number: int = 0

    @property
    def short_filename(self) -> str:
        """Return the base file name or abbreviated module path."""
        if not self.filename or self.filename == "<unknown>":
            return "<unknown>"
        try:
            return Path(self.filename).name
        except Exception:
            return self.filename

    @property
    def identifier(self) -> str:
        """Produce a stable unique signature for grouping identical frames."""
        return f"{self.short_filename}:{self.line_number}:{self.name}"

    @property
    def display_name(self) -> str:
        """Friendly label formatted for terminal and flamegraph visualization."""
        if self.line_number > 0:
            return f"{self.name} ({self.short_filename}:{self.line_number})"
        return self.name

    def to_dict(self) -> dict:
        """Serialize frame to dictionary."""
        return {
            "name": self.name,
            "filename": self.filename,
            "line_number": self.line_number,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StackFrame":
        """Deserialize frame from dictionary."""
        return cls(
            name=data.get("name", "unknown"),
            filename=data.get("filename", "<unknown>"),
            line_number=int(data.get("line_number", 0)),
        )

    @classmethod
    def from_raw_string(cls, raw: str) -> "StackFrame":
        """Parse frame from Brendan Gregg folded token or raw string."""
        raw = raw.strip()
        if not raw:
            return cls(name="<unknown>")

        # Handle format: filename:line:func or func(filename:line) or plain func
        if "(" in raw and raw.endswith(")"):
            name, rest = raw[:-1].split("(", 1)
            parts = rest.split(":")
            filename = parts[0] if parts else "<unknown>"
            line = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
            return cls(name=name.strip(), filename=filename.strip(), line_number=line)

        parts = raw.split(":")
        if len(parts) == 3 and parts[1].isdigit():
            return cls(filename=parts[0], line_number=int(parts[1]), name=parts[2])
        if len(parts) == 2 and parts[1].isdigit():
            return cls(name=parts[0], filename="<unknown>", line_number=int(parts[1]))

        return cls(name=raw)
