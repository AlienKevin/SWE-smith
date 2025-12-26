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
    OperationChangeModifier(likelihood=0.5),
    OperationFlipOperatorModifier(likelihood=0.5),
    OperationSwapOperandsModifier(likelihood=0.5),
    OperationChangeConstantsModifier(likelihood=0.5),
    OperationBreakChainsModifier(likelihood=0.5),
    # Control flow modifiers (2)
    ControlIfElseInvertModifier(likelihood=0.5),
    ControlShuffleLinesModifier(likelihood=0.5),
    # Remove modifiers (3)
    RemoveLoopModifier(likelihood=0.5),
    RemoveConditionalModifier(likelihood=0.5),
    RemoveAssignmentModifier(likelihood=0.5),
]
