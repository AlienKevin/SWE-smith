"""
Base class for JavaScript procedural modifications.
"""

from abc import ABC
from swesmith.bug_gen.procedural.base import ProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity


class JavaScriptProceduralModifier(ProceduralModifier, ABC):
    """Base class for JavaScript-specific procedural modifications using AST."""

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        # Simple string-based modification for JavaScript
        # In a real implementation, you'd use a proper JavaScript AST parser
        modified_code = self._apply_modification(code_entity.src_code)

        if modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            cost=0.0,
            strategy=self.name,
        )

    def _apply_modification(self, code: str) -> str:
        """Apply the specific modification to the code."""
        # This will be overridden by subclasses
        return code
