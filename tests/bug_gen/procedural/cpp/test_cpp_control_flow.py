import pytest
from swesmith.bug_gen.adapters.cpp import get_entities_from_file_cpp
from swesmith.bug_gen.procedural.cpp.control_flow import (
    ControlIfElseInvertModifier,
    ControlShuffleLinesModifier,
)


@pytest.mark.parametrize(
    "src,expected_variants",
    [
        (
            """int foo(int x) {
    if (x > 0) {
        return 1;
    } else {
        return -1;
    }
}""",
            [
                "int foo(int x) {\n    if (x > 0) {\n        return -1;\n    } else {\n        return 1;\n    }\n}",
            ],
        ),
        (
            """int bar(bool flag) {
    if (flag) {
        return 100;
    } else {
        return 200;
    }
}""",
            [
                "int bar(bool flag) {\n    if (flag) {\n        return 200;\n    } else {\n        return 100;\n    }\n}",
            ],
        ),
    ],
)
def test_control_if_else_invert_modifier(tmp_path, src, expected_variants):
    """Test that ControlIfElseInvertModifier swaps if-else bodies."""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = ControlIfElseInvertModifier(likelihood=1.0, seed=42)

    found_variant = False
    result = None
    for _ in range(20):
        result = modifier.modify(entities[0])
        if result is not None:
            if any(
                result.rewrite.strip() == variant.strip()
                for variant in expected_variants
            ):
                found_variant = True
                break

    assert found_variant, (
        f"Expected one of {expected_variants}, but got {result.rewrite if result else 'None'}"
    )


def test_control_if_else_invert_bare_if(tmp_path):
    """Test that ControlIfElseInvertModifier handles bare if statements (no else)."""
    src = """int foo(int x) {
    if (x > 0) {
        return 1;
    }
    return 0;
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = ControlIfElseInvertModifier(likelihood=1.0, seed=42)

    result = None
    for _ in range(20):
        result = modifier.modify(entities[0])
        if result is not None:
            # Should convert to: if (x > 0) {} else { return 1; }
            assert "else" in result.rewrite, f"Expected 'else' in result: {result.rewrite}"
            break

    assert result is not None, "Expected modifier to produce a result for bare if statement"


def test_control_shuffle_lines_modifier(tmp_path):
    """Test that ControlShuffleLinesModifier shuffles statements."""
    src = """void foo() {
    int a = 1;
    int b = 2;
    int c = 3;
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = ControlShuffleLinesModifier(likelihood=1.0, seed=42)

    found_different = False
    result = None
    for _ in range(20):
        result = modifier.modify(entities[0])
        if result is not None and result.rewrite.strip() != src.strip():
            found_different = True
            # Check that all statements are still present
            assert "int a = 1" in result.rewrite
            assert "int b = 2" in result.rewrite
            assert "int c = 3" in result.rewrite
            break

    assert found_different, "Expected modifier to shuffle statements differently"


def test_control_shuffle_lines_single_statement(tmp_path):
    """Test that ControlShuffleLinesModifier returns None when there's only one statement."""
    src = """void foo() {
    int a = 1;
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = ControlShuffleLinesModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is None, "Expected None when there's only one statement to shuffle"


def test_control_if_else_no_if_statements(tmp_path):
    """Test that ControlIfElseInvertModifier returns None when no if statements are present."""
    src = """int foo() {
    return 42;
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = ControlIfElseInvertModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is None, "Expected None when no if statements are present"


def test_control_if_else_else_if_chain(tmp_path):
    """Test that ControlIfElseInvertModifier handles else-if chains."""
    src = """int foo(int x) {
    if (x > 0) {
        return 1;
    } else if (x < 0) {
        return -1;
    } else {
        return 0;
    }
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = ControlIfElseInvertModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    # Should produce some modification
    assert result is not None, "Expected modifier to handle else-if chain"
    assert result.rewrite != src, "Expected result to differ from source"
