"""
JavaScript logic bug modifier for procedural bug generation.
"""

import re
from swesmith.bug_gen.procedural.javascript.base import JavaScriptProceduralModifier
from swesmith.constants import CodeProperty


class LogicBugModifier(JavaScriptProceduralModifier):
    """Creates realistic logic bugs by changing function calls and operators."""

    explanation: str = "The logic in conditions or function calls might be incorrect."
    name: str = "func_pm_logic_bug"
    conditions: list = [CodeProperty.IS_FUNCTION, CodeProperty.HAS_BINARY_OP]

    def _apply_modification(self, code: str) -> str:
        """Create logic bugs using safe regex patterns."""
        modified_code = code

        # Safe replacements that create logic bugs, not syntax errors
        logic_replacements = [
            # Comparison operators - use word boundaries
            (r'\b==\b', '!='),
            (r'\b!=\b', '=='),
            (r'\b===\b', '!=='),
            (r'\b!==\b', '==='),

            # Math function calls - only replace when they're function calls
            (r'\bMath\.max\b', 'Math.min'),
            (r'\bMath\.min\b', 'Math.max'),
            (r'\bMath\.floor\b', 'Math.ceil'),
            (r'\bMath\.ceil\b', 'Math.floor'),

            # String method calls - only replace when they're method calls
            (r'\.toUpperCase\(\)', '.toLowerCase()'),
            (r'\.toLowerCase\(\)', '.toUpperCase()'),

            # Boolean constants - use word boundaries
            (r'\btrue\b', 'false'),
            (r'\bfalse\b', 'true'),

            # Numeric constants that create logic bugs
            (r'\b0\b', '1'),
            (r'\b1\b', '0'),
            (r'\b100\b', '110'),
            (r'\b200\b', '220'),
        ]

        # Apply one random replacement
        for pattern, replacement in logic_replacements:
            if self.flip() and re.search(pattern, modified_code):
                modified_code = re.sub(pattern, replacement, modified_code, 1)
                break

        return modified_code

