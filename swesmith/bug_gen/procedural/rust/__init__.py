from swesmith.bug_gen.procedural.base import ProceduralModifier
from swesmith.bug_gen.procedural.rust.operations import (
    OperationBreakChainsModifier,
    OperationChangeConstantsModifier,
    OperationChangeModifier,
    OperationFlipOperatorModifier,
    OperationSwapOperandsModifier,
)

MODIFIERS_RUST: list[ProceduralModifier] = [
    OperationBreakChainsModifier(likelihood=0.4),
    OperationChangeConstantsModifier(likelihood=0.4),
    OperationChangeModifier(likelihood=0.4),
    OperationFlipOperatorModifier(likelihood=0.4),
    OperationSwapOperandsModifier(likelihood=0.4),
]
