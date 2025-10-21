import pytest
from swesmith.bug_gen.procedural.rust.control_flow import (
    ControlIfElseInvertModifier,
    ControlShuffleLinesModifier,
)


@pytest.mark.parametrize(
    "src,expected",
    [
        (
            """fn foo(x: i32) -> i32 {
    if x > 0 {
        return 1;
    } else {
        return -1;
    }
}""",
            """fn foo(x: i32) -> i32 {
    if x > 0 {
        return -1;
    } else {
        return 1;
    }
}""",
        ),
        (
            """fn bar(condition: bool) -> &str {
    if condition {
        "true"
    } else {
        "false"
    }
}""",
            """fn bar(condition: bool) -> &str {
    if condition {
        "false"
    } else {
        "true"
    }
}""",
        ),
        (
            """fn baz(x: i32) -> i32 {
    if x == 0 {
        let y = 1;
        y + 2
    } else {
        let z = 3;
        z + 4
    }
}""",
            """fn baz(x: i32) -> i32 {
    if x == 0 {
        let z = 3;
        z + 4
    } else {
        let y = 1;
        y + 2
    }
}""",
        ),
    ],
)
def test_control_if_else_invert_modifier(src, expected):
    """Test that ControlIfElseInvertModifier inverts if-else bodies."""
    from swesmith.bug_gen.procedural.rust.control_flow import RUST_LANGUAGE
    from tree_sitter import Parser

    parser = Parser(RUST_LANGUAGE)
    tree = parser.parse(bytes(src, "utf8"))

    modifier = ControlIfElseInvertModifier(likelihood=1.0, seed=42)
    result = modifier._invert_if_else_statements(src, tree.root_node)

    assert result.strip() == expected.strip(), (
        f"Expected:\n{expected}\n\nGot:\n{result}"
    )


@pytest.mark.parametrize(
    "src,expected_variants",
    [
        (
            """fn foo() {
    let a = 1;
    let b = 2;
}""",
            [
                "fn foo() {\n    let a = 1;\n    let b = 2;\n}",
                "fn foo() {\n    let b = 2;\n    let a = 1;\n}",
            ],
        ),
        (
            """fn bar() {
    let x = 1;
    let y = 2;
    let z = 3;
}""",
            [
                "fn bar() {\n    let x = 1;\n    let y = 2;\n    let z = 3;\n}",
                "fn bar() {\n    let x = 1;\n    let z = 3;\n    let y = 2;\n}",
                "fn bar() {\n    let y = 2;\n    let x = 1;\n    let z = 3;\n}",
                "fn bar() {\n    let y = 2;\n    let z = 3;\n    let x = 1;\n}",
                "fn bar() {\n    let z = 3;\n    let x = 1;\n    let y = 2;\n}",
                "fn bar() {\n    let z = 3;\n    let y = 2;\n    let x = 1;\n}",
            ],
        ),
        (
            """fn baz() {
    let x = 42;
}""",
            [
                "fn baz() {\n    let x = 42;\n}",
            ],
        ),
    ],
)
def test_control_shuffle_lines_modifier(src, expected_variants):
    """Test that ControlShuffleLinesModifier shuffles function statements."""
    from swesmith.bug_gen.procedural.rust.control_flow import RUST_LANGUAGE
    from tree_sitter import Parser

    parser = Parser(RUST_LANGUAGE)
    tree = parser.parse(bytes(src, "utf8"))

    modifier = ControlShuffleLinesModifier(likelihood=1.0, seed=42)
    result = modifier._shuffle_function_statements(src, tree.root_node)

    assert any(result.strip() == variant.strip() for variant in expected_variants), (
        f"Expected one of:\n{expected_variants}\n\nGot:\n{result}"
    )
