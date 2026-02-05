import pytest
from swesmith.bug_gen.adapters.java import get_entities_from_file_java
from swesmith.bug_gen.procedural.java.operations import (
    OperationChangeModifier,
    OperationFlipOperatorModifier,
    OperationSwapOperandsModifier,
    OperationChangeConstantsModifier,
)


@pytest.mark.parametrize(
    "src,possible_results",
    [
        (
            """public int add(int a, int b) {
    return a + b;
}""",
            [
                "return a - b;",
                "return a * b;",
                "return a / b;",
                "return a % b;",
            ],
        ),
        (
            """public boolean compare(int x, int y) {
    return x < y;
}""",
            [
                "return x > y;",
                "return x <= y;",
                "return x >= y;",
                "return x == y;",
                "return x != y;",
            ],
        ),
    ],
)
def test_operation_change_modifier(tmp_path, src, possible_results):
    """Test that OperationChangeModifier changes operations."""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationChangeModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert any(expected in result.rewrite for expected in possible_results), (
        f"Expected one of {possible_results} in {result.rewrite}"
    )


@pytest.mark.parametrize(
    "src,expected_mapping",
    [
        (
            """public boolean foo(int x) {
    return x < 10;
}""",
            {"<": ">="},
        ),
        (
            """public boolean bar(int x) {
    return x == 0;
}""",
            {"==": "!="},
        ),
        (
            """public boolean baz(boolean a, boolean b) {
    return a && b;
}""",
            {"&&": "||"},
        ),
    ],
)
def test_operation_flip_operator_modifier(tmp_path, src, expected_mapping):
    """Test that OperationFlipOperatorModifier flips operators correctly."""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationFlipOperatorModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    for original, flipped in expected_mapping.items():
        if original in src:
            assert flipped in result.rewrite, (
                f"Expected {flipped} in result after flipping {original}"
            )


@pytest.mark.parametrize(
    "src",
    [
        """public int foo(int a, int b) {
    return a + b;
}""",
        """public boolean bar(int x, int y) {
    return x < y;
}""",
    ],
)
def test_operation_swap_operands_modifier(tmp_path, src):
    """Test that OperationSwapOperandsModifier swaps operands."""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationSwapOperandsModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert result.rewrite != src, "Expected operands to be swapped"


@pytest.mark.parametrize(
    "src",
    [
        """public int foo() {
    return 42;
}""",
        """public double bar() {
    return 3.14;
}""",
        """public int baz(int x) {
    return x + 10;
}""",
    ],
)
def test_operation_change_constants_modifier(tmp_path, src):
    """Test that OperationChangeConstantsModifier changes numeric constants."""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationChangeConstantsModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert result.rewrite != src, "Expected constant to be changed"


def test_operation_change_modifier_no_string_concat(tmp_path):
    """Test that OperationChangeModifier doesn't change string concatenation."""
    src = """public String foo(String a) {
    return a + "suffix";
}"""
    test_file = tmp_path / "Test.java"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_java(entities, str(test_file))
    assert len(entities) == 1

    modifier = OperationChangeModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    # Should return None because we skip string concatenation
    assert result is None or "+" in result.rewrite
