import pytest
from swesmith.bug_gen.procedural.rust.operations import (
    OperationChangeModifier,
    OperationFlipOperatorModifier,
    OperationSwapOperandsModifier,
    OperationBreakChainsModifier,
    OperationChangeConstantsModifier,
    FLIPPED_OPERATORS,
)


@pytest.mark.parametrize(
    "src,expected_variants",
    [
        (
            """fn foo(a: i32, b: i32) -> i32 {
    a + b
}""",
            [
                "fn foo(a: i32, b: i32) -> i32 {\n    a - b\n}",
                "fn foo(a: i32, b: i32) -> i32 {\n    a * b\n}",
                "fn foo(a: i32, b: i32) -> i32 {\n    a / b\n}",
                "fn foo(a: i32, b: i32) -> i32 {\n    a % b\n}",
            ],
        ),
        (
            """fn bar(x: i32, y: i32) -> bool {
    x == y
}""",
            [
                "fn bar(x: i32, y: i32) -> bool {\n    x != y\n}",
                "fn bar(x: i32, y: i32) -> bool {\n    x < y\n}",
                "fn bar(x: i32, y: i32) -> bool {\n    x <= y\n}",
                "fn bar(x: i32, y: i32) -> bool {\n    x > y\n}",
                "fn bar(x: i32, y: i32) -> bool {\n    x >= y\n}",
            ],
        ),
        (
            """fn baz(a: u32, b: u32) -> u32 {
    a & b
}""",
            [
                "fn baz(a: u32, b: u32) -> u32 {\n    a | b\n}",
                "fn baz(a: u32, b: u32) -> u32 {\n    a ^ b\n}",
            ],
        ),
    ],
)
def test_operation_change_modifier(src, expected_variants):
    """Test that OperationChangeModifier changes operators within the same category."""
    from swesmith.bug_gen.procedural.rust.operations import RUST_LANGUAGE
    from tree_sitter import Parser

    parser = Parser(RUST_LANGUAGE)
    tree = parser.parse(bytes(src, "utf8"))

    modifier = OperationChangeModifier(likelihood=1.0, seed=42)

    found_variant = False
    for _ in range(20):
        result = modifier._change_operations(src, tree.root_node)
        if result != src and any(
            result.strip() == variant.strip() for variant in expected_variants
        ):
            found_variant = True
            break

    assert found_variant, f"Expected one of {expected_variants}, but got {result}"


@pytest.mark.parametrize(
    "src,expected",
    [
        (
            """fn foo(a: i32, b: i32) -> i32 {
    a + b
}""",
            """fn foo(a: i32, b: i32) -> i32 {
    a - b
}""",
        ),
        (
            """fn bar(x: i32, y: i32) -> bool {
    x == y
}""",
            """fn bar(x: i32, y: i32) -> bool {
    x != y
}""",
        ),
        (
            """fn baz(a: i32, b: i32) -> bool {
    a < b
}""",
            """fn baz(a: i32, b: i32) -> bool {
    a > b
}""",
        ),
        (
            """fn qux(x: bool, y: bool) -> bool {
    x && y
}""",
            """fn qux(x: bool, y: bool) -> bool {
    x || y
}""",
        ),
    ],
)
def test_operation_flip_operator_modifier(src, expected):
    """Test that OperationFlipOperatorModifier flips operators to their opposites."""
    from swesmith.bug_gen.procedural.rust.operations import RUST_LANGUAGE
    from tree_sitter import Parser

    parser = Parser(RUST_LANGUAGE)
    tree = parser.parse(bytes(src, "utf8"))

    modifier = OperationFlipOperatorModifier(likelihood=1.0, seed=42)
    result = modifier._flip_operators(src, tree.root_node)

    assert result.strip() == expected.strip(), f"Expected {expected}, got {result}"


@pytest.mark.parametrize(
    "src,expected",
    [
        (
            """fn foo(a: i32, b: i32) -> i32 {
    a + b
}""",
            """fn foo(a: i32, b: i32) -> i32 {
    b + a
}""",
        ),
        (
            """fn bar(x: i32, y: i32) -> bool {
    x < y
}""",
            """fn bar(x: i32, y: i32) -> bool {
    y < x
}""",
        ),
        (
            """fn baz(a: i32, b: i32) -> i32 {
    a - b
}""",
            """fn baz(a: i32, b: i32) -> i32 {
    b - a
}""",
        ),
    ],
)
def test_operation_swap_operands_modifier(src, expected):
    """Test that OperationSwapOperandsModifier swaps operands in binary expressions."""
    from swesmith.bug_gen.procedural.rust.operations import RUST_LANGUAGE
    from tree_sitter import Parser

    parser = Parser(RUST_LANGUAGE)
    tree = parser.parse(bytes(src, "utf8"))

    modifier = OperationSwapOperandsModifier(likelihood=1.0, seed=42)
    result = modifier._swap_operands(src, tree.root_node)

    assert result.strip() == expected.strip(), f"Expected {expected}, got {result}"


@pytest.mark.parametrize(
    "src,expected_variants",
    [
        (
            """fn foo(a: i32, b: i32, c: i32) -> i32 {
    a + b + c
}""",
            [
                "fn foo(a: i32, b: i32, c: i32) -> i32 {\n    a\n}",
                "fn foo(a: i32, b: i32, c: i32) -> i32 {\n    c\n}",
            ],
        ),
        (
            """fn bar(x: i32, y: i32, z: i32) -> i32 {
    x * (y * z)
}""",
            [
                "fn bar(x: i32, y: i32, z: i32) -> i32 {\n    z\n}",
                "fn bar(x: i32, y: i32, z: i32) -> i32 {\n    x * (y * z)\n}",
            ],
        ),
        (
            """fn baz(a: i32, b: i32) -> i32 {
    a + b
}""",
            [
                "fn baz(a: i32, b: i32) -> i32 {\n    a + b\n}",
            ],
        ),
    ],
)
def test_operation_break_chains_modifier(src, expected_variants):
    """Test that OperationBreakChainsModifier breaks operation chains."""
    from swesmith.bug_gen.procedural.rust.operations import RUST_LANGUAGE
    from tree_sitter import Parser

    parser = Parser(RUST_LANGUAGE)
    tree = parser.parse(bytes(src, "utf8"))

    modifier = OperationBreakChainsModifier(likelihood=1.0, seed=42)
    result = modifier._break_chains(src, tree.root_node)

    assert any(result.strip() == variant.strip() for variant in expected_variants), (
        f"Expected one of {expected_variants}, got {result}"
    )


@pytest.mark.parametrize(
    "src,expected_variants",
    [
        (
            """fn foo() -> i32 {
    2 + x
}""",
            [
                "fn foo() -> i32 {\n    1 + x\n}",
                "fn foo() -> i32 {\n    3 + x\n}",
            ],
        ),
        (
            """fn bar() -> i32 {
    y - 5
}""",
            [
                "fn bar() -> i32 {\n    y - 4\n}",
                "fn bar() -> i32 {\n    y - 6\n}",
            ],
        ),
        (
            """fn baz() -> i32 {
    10 * 20
}""",
            [
                "fn baz() -> i32 {\n    9 * 20\n}",
                "fn baz() -> i32 {\n    11 * 20\n}",
                "fn baz() -> i32 {\n    10 * 19\n}",
                "fn baz() -> i32 {\n    10 * 21\n}",
                "fn baz() -> i32 {\n    9 * 19\n}",
                "fn baz() -> i32 {\n    9 * 21\n}",
                "fn baz() -> i32 {\n    11 * 19\n}",
                "fn baz() -> i32 {\n    11 * 21\n}",
            ],
        ),
        (
            """fn qux(a: i32, b: i32) -> i32 {
    a / b
}""",
            [
                "fn qux(a: i32, b: i32) -> i32 {\n    a / b\n}",
            ],
        ),
    ],
)
def test_operation_change_constants_modifier(src, expected_variants):
    """Test that OperationChangeConstantsModifier changes integer constants."""
    from swesmith.bug_gen.procedural.rust.operations import RUST_LANGUAGE
    from tree_sitter import Parser

    parser = Parser(RUST_LANGUAGE)
    tree = parser.parse(bytes(src, "utf8"))

    modifier = OperationChangeConstantsModifier(likelihood=1.0, seed=42)
    result = modifier._change_constants(src, tree.root_node)

    assert any(result.strip() == variant.strip() for variant in expected_variants), (
        f"Expected one of {expected_variants}, got {result}"
    )


def test_operation_flip_operator_mappings():
    """Test that OperationFlipOperatorModifier uses correct operator mappings."""
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
