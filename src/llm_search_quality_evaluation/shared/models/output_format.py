from enum import Enum


class OutputFormat(str, Enum):
    """Supported output formats for dataset generation."""
    QUEPID = "quepid"
    RRE = "rre"
    MTEB = "mteb"

    def __str__(self) -> str:
        return self.value

