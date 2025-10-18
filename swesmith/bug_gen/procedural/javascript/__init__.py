from swesmith.bug_gen.procedural.base import ProceduralModifier

from swesmith.bug_gen.procedural.javascript.operations import (
    LogicBugModifier
)

MODIFIERS_JAVASCRIPT: list[ProceduralModifier] = [
    LogicBugModifier(likelihood=1.0)
]
