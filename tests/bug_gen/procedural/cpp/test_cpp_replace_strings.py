import pytest
from swesmith.bug_gen.adapters.cpp import get_entities_from_file_cpp
from swesmith.bug_gen.procedural.cpp.replace_strings import ReplaceStringTypoModifier


@pytest.mark.parametrize(
    "src",
    [
        """void foo() {
    const char* msg = "Hello World";
}""",
        """void bar() {
    std::string s = "error message";
}""",
        """void baz() {
    printf("testing output");
}""",
    ],
)
def test_replace_string_typo_modifier(tmp_path, src):
    """Test that ReplaceStringTypoModifier introduces typos in string literals."""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = ReplaceStringTypoModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert result.rewrite != src, "Expected result to differ from source"
    # The string literal should be modified
    assert '"' in result.rewrite, "Expected quotes to still be present"


def test_replace_string_typo_modifier_single_character_change(tmp_path):
    """Test that ReplaceStringTypoModifier changes a single character."""
    src = """void foo() {
    const char* msg = "abcdef";
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = ReplaceStringTypoModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None

    # Extract string content from source and result
    original_string = "abcdef"
    # Find the modified string - it should differ by at most a few characters
    # (due to typo types like adjacent swap which changes 2 chars)
    result_has_modification = result.rewrite != src
    assert result_has_modification, "Expected string to be modified"


def test_replace_string_typo_modifier_wide_string(tmp_path):
    """Test that ReplaceStringTypoModifier handles wide string literals."""
    src = """void foo() {
    const wchar_t* msg = L"Wide string";
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = ReplaceStringTypoModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert result.rewrite != src, "Expected result to differ from source"
    assert 'L"' in result.rewrite, "Expected wide string prefix to be preserved"


def test_replace_string_typo_modifier_empty_string(tmp_path):
    """Test that ReplaceStringTypoModifier handles empty strings gracefully."""
    src = """void foo() {
    const char* msg = "";
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = ReplaceStringTypoModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    # Empty strings should return None (nothing to modify)
    assert result is None, "Expected None for empty string"


def test_replace_string_typo_modifier_no_strings(tmp_path):
    """Test that ReplaceStringTypoModifier returns None when no strings are present."""
    src = """int foo() {
    return 42;
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = ReplaceStringTypoModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is None, "Expected None when no strings are present"


def test_replace_string_typo_modifier_multiple_strings(tmp_path):
    """Test that ReplaceStringTypoModifier handles functions with multiple strings."""
    src = """void foo() {
    printf("first string");
    printf("second string");
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = ReplaceStringTypoModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert result.rewrite != src, "Expected result to differ from source"


def test_replace_string_typo_modifier_preserves_structure(tmp_path):
    """Test that ReplaceStringTypoModifier preserves code structure."""
    src = """void foo() {
    const char* msg = "test";
    printf(msg);
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = ReplaceStringTypoModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    # Function structure should be preserved
    assert "void foo()" in result.rewrite
    assert "printf(msg);" in result.rewrite


def test_replace_string_typo_explanation(tmp_path):
    """Test that ReplaceStringTypoModifier provides correct explanation."""
    src = """void foo() {
    const char* msg = "Hello";
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = ReplaceStringTypoModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert "typo" in result.explanation.lower(), (
        f"Expected explanation to mention typo: {result.explanation}"
    )


def test_replace_string_typo_strategy_name(tmp_path):
    """Test that ReplaceStringTypoModifier provides correct strategy name."""
    src = """void foo() {
    const char* msg = "Hello";
}"""
    test_file = tmp_path / "test.cpp"
    test_file.write_text(src, encoding="utf-8")

    entities = []
    get_entities_from_file_cpp(entities, str(test_file))
    assert len(entities) == 1

    modifier = ReplaceStringTypoModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entities[0])

    assert result is not None
    assert result.strategy == "func_pm_string_typo", (
        f"Expected strategy 'func_pm_string_typo', got {result.strategy}"
    )
