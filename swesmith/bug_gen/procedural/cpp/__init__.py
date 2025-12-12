"""
C++-specific procedural modifications for bug generation.
"""

from swesmith.bug_gen.procedural.base import ProceduralModifier
from swesmith.bug_gen.procedural.cpp.control_flow import (
    ControlIfElseInvertModifier,
    ControlShuffleLinesModifier,
)
from swesmith.bug_gen.procedural.cpp.operations import (
    OperationBreakChainsModifier,
    OperationChangeConstantsModifier,
    OperationChangeModifier,
    OperationFlipOperatorModifier,
    OperationSwapOperandsModifier,
)
from swesmith.bug_gen.procedural.cpp.remove import (
    RemoveAssignModifier,
    RemoveConditionalModifier,
    RemoveLoopModifier,
)
from swesmith.bug_gen.procedural.cpp.replace_strings import (
    ReplaceStringTypoModifier,
)

MODIFIERS_CPP: list[ProceduralModifier] = [
    ControlIfElseInvertModifier(likelihood=1.0),  # Increased from 0.2 - very effective
    ControlShuffleLinesModifier(likelihood=0.2),
    RemoveAssignModifier(likelihood=0.2),
    RemoveConditionalModifier(likelihood=0.25),
    RemoveLoopModifier(likelihood=0.25),
    OperationBreakChainsModifier(likelihood=0.9),
    OperationChangeConstantsModifier(likelihood=0.3),
    OperationChangeModifier(likelihood=1.0),
    OperationFlipOperatorModifier(likelihood=1.0),
    OperationSwapOperandsModifier(likelihood=1.0),
    ReplaceStringTypoModifier(likelihood=1.0),
]
