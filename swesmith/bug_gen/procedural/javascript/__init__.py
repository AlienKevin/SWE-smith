from swesmith.bug_gen.procedural.base import ProceduralModifier

from swesmith.bug_gen.procedural.javascript.operations import (
    OperationChangeModifier,
    OperationFlipOperatorModifier,
    OperationSwapOperandsModifier,
    OperationChangeConstantsModifier,
    OperationBreakChainsModifier,
)
from swesmith.bug_gen.procedural.javascript.control_flow import (
    ControlIfElseInvertModifier,
    ControlShuffleLinesModifier,
)
from swesmith.bug_gen.procedural.javascript.remove import (
    RemoveLoopModifier,
    RemoveConditionalModifier,
    RemoveAssignmentModifier,
)

MODIFIERS_JAVASCRIPT: list[ProceduralModifier] = [
    # Operation modifiers (5)
    OperationChangeModifier(likelihood=0.2),
    OperationFlipOperatorModifier(likelihood=0.2),
    OperationSwapOperandsModifier(likelihood=0.2),
    OperationChangeConstantsModifier(likelihood=0.2),
    OperationBreakChainsModifier(likelihood=0.2),
    # Control flow modifiers (2)
    ControlIfElseInvertModifier(likelihood=0.2),
    ControlShuffleLinesModifier(likelihood=0.2),
    # Remove modifiers (3)
    RemoveLoopModifier(likelihood=0.2),
    RemoveConditionalModifier(likelihood=0.2),
    RemoveAssignmentModifier(likelihood=0.2),
]
