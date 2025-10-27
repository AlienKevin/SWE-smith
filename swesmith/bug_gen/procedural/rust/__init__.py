from swesmith.bug_gen.procedural.base import ProceduralModifier
from swesmith.bug_gen.procedural.rust.control_flow import (
    ControlIfElseInvertModifier,
    ControlShuffleLinesModifier,
)
from swesmith.bug_gen.procedural.rust.operations import (
    OperationBreakChainsModifier,
    OperationChangeConstantsModifier,
    OperationChangeModifier,
    OperationFlipOperatorModifier,
    OperationSwapOperandsModifier,
)
from swesmith.bug_gen.procedural.rust.remove import (
    RemoveAssignModifier,
    RemoveConditionalModifier,
    RemoveLoopModifier,
)

MODIFIERS_RUST: list[ProceduralModifier] = [
    ControlIfElseInvertModifier(likelihood=0.9),
    ControlShuffleLinesModifier(likelihood=0.1),
    RemoveAssignModifier(likelihood=0.1),
    RemoveConditionalModifier(likelihood=0.1),
    RemoveLoopModifier(likelihood=0.1),
    OperationBreakChainsModifier(likelihood=0.9),
    OperationChangeConstantsModifier(likelihood=0.9),
    OperationChangeModifier(likelihood=0.9),
    OperationFlipOperatorModifier(likelihood=0.9),
    OperationSwapOperandsModifier(likelihood=0.9),
]
