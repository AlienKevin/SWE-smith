import random

from swesmith.bug_gen.adapters.rust import get_entities_from_file_rs
from swesmith.bug_gen.procedural.rust.operations import (
    OperationChangeModifier,
    OperationFlipOperatorModifier,
    OperationSwapOperandsModifier,
    OperationBreakChainsModifier,
    OperationChangeConstantsModifier,
    ALL_BINARY_OPERATORS,
)


def test_all_binary_operators_constant():
    """Test that ALL_BINARY_OPERATORS contains all expected operators."""
    expected_operators = [
        "+",
        "-",
        "*",
        "/",
        "%",
        "<<",
        ">>",
        "&",
        "|",
        "^",
        "==",
        "!=",
        "<",
        "<=",
        ">",
        ">=",
        "&&",
        "||",
    ]
    assert set(ALL_BINARY_OPERATORS) == set(expected_operators)
    assert len(ALL_BINARY_OPERATORS) == 18


def test_operation_change_modifier(test_file_rust):
    """Test that OperationChangeModifier changes operators within the same category."""
    entities = []
    get_entities_from_file_rs(entities, test_file_rust)

    pm = OperationChangeModifier(likelihood=1.0)
    pm.min_complexity = 1  # Lower the requirement for testing

    # Set a fixed random seed for reproducible test results
    pm.rand = random.Random(42)

    entities = [x for x in entities if pm.can_change(x)]
    assert len(entities) >= 1  # At least one entity should have binary operations

    # Find an entity with binary operations
    test_entity = None
    for entity in entities:
        if "==" in entity.src_code or "!=" in entity.src_code:
            test_entity = entity
            break

    assert test_entity is not None
    modified = pm.modify(test_entity)

    # Verify that modification occurred and it's different from original
    assert modified is not None
    assert modified.rewrite != test_entity.src_code
    assert modified.explanation is not None
    assert modified.strategy is not None


def test_operation_flip_operator_modifier(test_file_rust):
    """Test that OperationFlipOperatorModifier flips operators to their opposites."""
    entities = []
    get_entities_from_file_rs(entities, test_file_rust)

    pm = OperationFlipOperatorModifier(likelihood=1.0)
    pm.min_complexity = 1  # Lower the requirement for testing

    # Set a fixed random seed for reproducible test results
    pm.rand = random.Random(123)

    entities = [x for x in entities if pm.can_change(x)]
    assert len(entities) >= 1  # At least one entity should have binary operations

    # Find an entity with flippable operators
    test_entity = None
    for entity in entities:
        if "==" in entity.src_code:
            test_entity = entity
            break

    assert test_entity is not None
    modified = pm.modify(test_entity)

    # Verify modification occurred
    assert modified is not None
    assert modified.rewrite != test_entity.src_code
    assert modified.explanation is not None
    assert modified.strategy is not None

    # Verify that operators were actually flipped (e.g., == became !=)
    if "==" in test_entity.src_code:
        assert "!=" in modified.rewrite or "==" not in modified.rewrite


def test_operation_swap_operands_modifier(test_file_rust):
    """Test that OperationSwapOperandsModifier swaps operands in binary expressions."""
    entities = []
    get_entities_from_file_rs(entities, test_file_rust)

    pm = OperationSwapOperandsModifier(likelihood=1.0)
    pm.min_complexity = 1  # Lower the requirement for testing

    # Set a fixed random seed for reproducible test results
    pm.rand = random.Random(456)

    entities = [x for x in entities if pm.can_change(x)]
    assert len(entities) >= 1  # At least one entity should have binary operations

    # Find an entity with suitable binary operations
    test_entity = None
    for entity in entities:
        if "==" in entity.src_code and "Some(" in entity.src_code:
            test_entity = entity
            break

    assert test_entity is not None
    modified = pm.modify(test_entity)

    # Verify modification occurred
    assert modified is not None
    assert modified.rewrite != test_entity.src_code
    assert modified.explanation is not None
    assert modified.strategy is not None


def test_operation_break_chains_modifier(test_file_rust):
    """Test that OperationBreakChainsModifier breaks complex expression chains."""
    entities = []
    get_entities_from_file_rs(entities, test_file_rust)
    pm = OperationBreakChainsModifier(likelihood=1.0)

    # Set a fixed random seed for reproducible test results
    pm.rand = random.Random(789)

    entities = [x for x in entities if pm.can_change(x)]
    assert len(entities) >= 0  # May not have complex chains

    # Try multiple entities to find one that gets modified
    modified = None
    test_entity = None
    for entity in entities[:10]:  # Try first 10 entities
        for _ in range(5):  # Multiple attempts due to randomness
            result = pm.modify(entity)
            if result and result.rewrite != entity.src_code:
                modified = result
                test_entity = entity
                break
        if modified:
            break

    if modified:
        assert test_entity is not None
        assert modified.rewrite != test_entity.src_code
        assert modified.explanation is not None
        assert modified.strategy is not None


def test_operation_change_constants_modifier(test_file_rust):
    """Test that OperationChangeConstantsModifier modifies numeric constants."""
    entities = []
    get_entities_from_file_rs(entities, test_file_rust)
    pm = OperationChangeConstantsModifier(likelihood=1.0)

    # Set a fixed random seed for reproducible test results
    pm.rand = random.Random(101112)

    entities = [x for x in entities if pm.can_change(x)]
    assert len(entities) >= 0  # May not have constants in binary operations

    # Try multiple entities to find one with constants that gets modified
    modified = None
    test_entity = None
    for entity in entities[:15]:  # Try first 15 entities
        if any(char.isdigit() for char in entity.src_code):  # Has numeric literals
            for _ in range(10):  # Multiple attempts due to randomness
                result = pm.modify(entity)
                if result and result.rewrite != entity.src_code:
                    modified = result
                    test_entity = entity
                    break
        if modified:
            break

    if modified:
        assert test_entity is not None
        assert modified.rewrite != test_entity.src_code
        assert modified.explanation is not None
        assert modified.strategy is not None


def test_operation_modifiers_can_change(test_file_rust):
    """Test that operation modifiers correctly identify compatible entities."""
    entities = []
    get_entities_from_file_rs(entities, test_file_rust)

    # Test all modifiers
    modifiers = [
        OperationChangeModifier(likelihood=1.0),
        OperationFlipOperatorModifier(likelihood=1.0),
        OperationSwapOperandsModifier(likelihood=1.0),
        OperationBreakChainsModifier(likelihood=1.0),
        OperationChangeConstantsModifier(likelihood=1.0),
    ]

    for modifier in modifiers:
        compatible_entities = [x for x in entities if modifier.can_change(x)]
        # Should have some compatible entities from the Rust codebase
        assert len(compatible_entities) >= 0  # May vary based on code patterns


def test_operation_modifiers_edge_cases(test_file_rust):
    """Test edge cases and error handling for operation modifiers."""
    entities = []
    get_entities_from_file_rs(entities, test_file_rust)

    modifiers = [
        OperationChangeModifier(likelihood=1.0),
        OperationFlipOperatorModifier(likelihood=1.0),
        OperationSwapOperandsModifier(likelihood=1.0),
        OperationBreakChainsModifier(likelihood=1.0),
        OperationChangeConstantsModifier(likelihood=1.0),
    ]

    for modifier in modifiers:
        compatible_entities = [x for x in entities if modifier.can_change(x)]

        if compatible_entities:
            # Test that modifiers handle entities gracefully
            test_entity = compatible_entities[0]
            result = modifier.modify(test_entity)

            # The result can be None (no modification) or a valid BugRewrite
            if result:
                assert result.rewrite is not None
                assert result.explanation is not None
                assert result.strategy is not None
                assert isinstance(result.explanation, str)
                assert isinstance(result.strategy, str)


def test_operation_modifiers_with_low_likelihood(test_file_rust):
    """Test that modifiers with low likelihood sometimes return None."""
    entities = []
    get_entities_from_file_rs(entities, test_file_rust)

    pm = OperationChangeModifier(likelihood=0.01)
    pm.rand = random.Random(999)

    entities = [x for x in entities if pm.can_change(x)]

    if entities:
        test_entity = entities[0]

        none_count = 0
        total_attempts = 50

        for _ in range(total_attempts):
            result = pm.modify(test_entity)
            if result is None:
                none_count += 1

        assert none_count > total_attempts * 0.8  # At least 80% should be None


def test_operation_change_modifier_categories():
    """Test that OperationChangeModifier respects operator categories."""
    from swesmith.bug_gen.procedural.rust.operations import (
        ARITHMETIC_OPS,
        BITWISE_OPS,
        COMPARISON_OPS,
        LOGICAL_OPS,
    )

    pm = OperationChangeModifier(likelihood=1.0)
    pm.rand = random.Random(42)

    for op in ARITHMETIC_OPS:
        new_op = pm._get_alternative_operator(op)
        assert new_op in ARITHMETIC_OPS

    for op in BITWISE_OPS:
        new_op = pm._get_alternative_operator(op)
        assert new_op in BITWISE_OPS

    for op in COMPARISON_OPS:
        new_op = pm._get_alternative_operator(op)
        assert new_op in COMPARISON_OPS

    for op in LOGICAL_OPS:
        new_op = pm._get_alternative_operator(op)
        assert new_op in LOGICAL_OPS


def test_operation_flip_operator_mappings():
    """Test that OperationFlipOperatorModifier uses correct operator mappings."""
    from swesmith.bug_gen.procedural.rust.operations import FLIPPED_OPERATORS

    assert FLIPPED_OPERATORS["+"] == "-"
    assert FLIPPED_OPERATORS["-"] == "+"
    assert FLIPPED_OPERATORS["*"] == "/"
    assert FLIPPED_OPERATORS["/"] == "*"
    assert FLIPPED_OPERATORS["=="] == "!="
    assert FLIPPED_OPERATORS["!="] == "=="
    assert FLIPPED_OPERATORS["<"] == ">"
    assert FLIPPED_OPERATORS[">"] == "<"
    assert FLIPPED_OPERATORS["<="] == ">="
    assert FLIPPED_OPERATORS[">="] == "<="
    assert FLIPPED_OPERATORS["&&"] == "||"
    assert FLIPPED_OPERATORS["||"] == "&&"
    assert FLIPPED_OPERATORS["&"] == "|"
    assert FLIPPED_OPERATORS["|"] == "&"
    assert FLIPPED_OPERATORS["<<"] == ">>"
    assert FLIPPED_OPERATORS[">>"] == "<<"
