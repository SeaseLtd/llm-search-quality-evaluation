from typing import Optional


class LLMScoreResponse:
    """Parses and validates an LLM score response."""

    def __init__(self, score: int, scale: str = "graded", explanation: Optional[str] = None):
        """Validate the score and explanation.

        Raises ValueError for an invalid scale or score, or a non-string explanation.
        Blank or whitespace-only explanations are normalized to None.
        """
        if scale not in ["binary", "graded"]:
            raise ValueError(f"Invalid scale: {scale}. Must be 'binary' or 'graded'.")

        if scale == "binary" and score not in {0, 1}:
            raise ValueError(f"Score must be 0 or 1 for binary scale, got {score}")
        elif scale == "graded" and score not in {0, 1, 2}:
            raise ValueError(f"Score must be 0, 1, or 2 for graded scale, got {score}")

        self.score = score

        if explanation is not None and not isinstance(explanation, str):
            raise ValueError("`explanation`, if provided, must be a string.")
        if isinstance(explanation, str) and not explanation.strip():
            explanation = None
        self.explanation = explanation

    def get_score(self) -> int:
        """Return the validated score."""
        return self.score
