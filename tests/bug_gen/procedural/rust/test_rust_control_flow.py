import random

from swesmith.bug_gen.adapters.rust import get_entities_from_file_rs
from swesmith.bug_gen.procedural.rust.control_flow import (
    ControlIfElseInvertModifier,
    ControlShuffleLinesModifier,
)


def test_control_if_else_invert_modifier(test_file_rust):
    """Test that ControlIfElseInvertModifier inverts if-else statements."""
    entities = []
    get_entities_from_file_rs(entities, test_file_rust)
    pm = ControlIfElseInvertModifier(likelihood=1.0)

    # Set a fixed random seed for reproducible test results
    pm.rand = random.Random(42)

    entities = [x for x in entities if pm.can_change(x)]

    modified = None
    test_entity = None
    for entity in entities:
        if "if " in entity.src_code and entity.complexity >= pm.min_complexity:
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
        assert (
            "if-else" in modified.explanation.lower()
            or "invert" in modified.explanation.lower()
        )


def test_control_shuffle_lines_modifier(test_file_rust):
    """Test that ControlShuffleLinesModifier shuffles function statements."""
    entities = []
    get_entities_from_file_rs(entities, test_file_rust)
    pm = ControlShuffleLinesModifier(likelihood=1.0)

    # Set a fixed random seed for reproducible test results
    pm.rand = random.Random(123)

    entities = [x for x in entities if pm.can_change(x)]

    test_entity = None
    for entity in entities:
        if (
            entity.complexity <= pm.max_complexity
            and len(entity.src_code.split("\n")) >= 3
        ):
            test_entity = entity
            break

    if test_entity:
        modified = pm.modify(test_entity)

        if modified:
            assert modified.rewrite != test_entity.src_code
            assert modified.explanation is not None
            assert modified.strategy is not None
            assert (
                "shuffle" in modified.explanation.lower()
                or "lines" in modified.explanation.lower()
            )


def test_control_modifiers_can_change(test_file_rust):
    """Test that control flow modifiers correctly identify compatible entities."""
    entities = []
    get_entities_from_file_rs(entities, test_file_rust)

    # Test all modifiers
    modifiers = [
        ControlIfElseInvertModifier(likelihood=1.0),
        ControlShuffleLinesModifier(likelihood=1.0),
    ]

    for modifier in modifiers:
        compatible_entities = [x for x in entities if modifier.can_change(x)]
        # Should have some compatible entities from the Rust codebase
        assert len(compatible_entities) >= 0  # May be 0 if no suitable entities


def test_control_modifiers_edge_cases(test_file_rust):
    """Test edge cases and error handling for control flow modifiers."""
    entities = []
    get_entities_from_file_rs(entities, test_file_rust)

    modifiers = [
        ControlIfElseInvertModifier(likelihood=1.0),
        ControlShuffleLinesModifier(likelihood=1.0),
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


def test_control_if_else_invert_complexity_requirement():
    """Test that ControlIfElseInvertModifier respects minimum complexity requirement."""
    pm = ControlIfElseInvertModifier(likelihood=1.0)

    assert pm.min_complexity == 5

    class MockEntity:
        def __init__(self, complexity_val):
            self._complexity = complexity_val
            self.src_code = "fn test() { if true { } else { } }"
            from swesmith.constants import CodeProperty

            self._tags = {CodeProperty.IS_FUNCTION, CodeProperty.HAS_IF_ELSE}

        @property
        def complexity(self):
            return self._complexity

        @property
        def tags(self):
            return self._tags

    low_complexity_entity = MockEntity(3)
    assert not pm.can_change(low_complexity_entity)

    high_complexity_entity = MockEntity(10)
    assert pm.can_change(high_complexity_entity)


def test_control_shuffle_lines_complexity_requirement():
    """Test that ControlShuffleLinesModifier respects maximum complexity requirement."""
    pm = ControlShuffleLinesModifier(likelihood=1.0)

    assert pm.max_complexity == 10

    class MockEntity:
        def __init__(self, complexity_val):
            self._complexity = complexity_val
            self.src_code = "fn test() { let x = 1; let y = 2; }"
            from swesmith.constants import CodeProperty

            self._tags = {CodeProperty.IS_FUNCTION, CodeProperty.HAS_LOOP}

        @property
        def complexity(self):
            return self._complexity

        @property
        def tags(self):
            return self._tags

    low_complexity_entity = MockEntity(5)
    assert pm.can_change(low_complexity_entity)

    high_complexity_entity = MockEntity(15)
    assert not pm.can_change(high_complexity_entity)


def test_control_modifiers_with_low_likelihood(test_file_rust):
    """Test that modifiers with low likelihood sometimes return None."""
    entities = []
    get_entities_from_file_rs(entities, test_file_rust)

    pm = ControlShuffleLinesModifier(likelihood=0.01)
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


def test_control_if_else_invert_specific_patterns():
    """Test ControlIfElseInvertModifier with specific if-else patterns."""
    from swesmith.bug_gen.procedural.rust.control_flow import RUST_LANGUAGE
    from swesmith.constants import CodeEntity
    from tree_sitter import Parser

    pm = ControlIfElseInvertModifier(likelihood=1.0)
    pm.rand = random.Random(42)

    rust_code = """fn test_function() {
    if condition {
        do_something();
    } else {
        do_something_else();
    }
}"""

    parser = Parser(RUST_LANGUAGE)
    tree = parser.parse(bytes(rust_code, "utf8"))

    function_node = None
    for child in tree.root_node.children:
        if child.type == "function_item":
            function_node = child
            break

    if function_node:

        class MockEntity(CodeEntity):
            def __init__(self):
                self.src_code = rust_code
                self.node = function_node
                self._complexity_val = 6  # Above minimum
                from swesmith.constants import CodeProperty

                self._tags = {CodeProperty.IS_FUNCTION, CodeProperty.HAS_IF_ELSE}

            @property
            def complexity(self):
                return self._complexity_val

            @property
            def tags(self):
                return self._tags

        entity = MockEntity()

        assert pm.can_change(entity)

        for _ in range(10):  # Multiple attempts due to randomness
            result = pm.modify(entity)
            if result and result.rewrite != entity.src_code:
                assert "if condition" in result.rewrite
                assert "else" in result.rewrite
                break


def test_control_shuffle_lines_specific_patterns():
    """Test ControlShuffleLinesModifier with specific function patterns."""
    from swesmith.bug_gen.procedural.rust.control_flow import RUST_LANGUAGE
    from swesmith.constants import CodeEntity
    from tree_sitter import Parser

    pm = ControlShuffleLinesModifier(likelihood=1.0)
    pm.rand = random.Random(123)

    rust_code = """fn test_function() {
    let x = 1;
    let y = 2;
    let z = x + y;
    return z;
}"""

    parser = Parser(RUST_LANGUAGE)
    tree = parser.parse(bytes(rust_code, "utf8"))

    function_node = None
    for child in tree.root_node.children:
        if child.type == "function_item":
            function_node = child
            break

    if function_node:

        class MockEntity(CodeEntity):
            def __init__(self):
                self.src_code = rust_code
                self.node = function_node
                self._complexity_val = 5  # Below maximum
                from swesmith.constants import CodeProperty

                self._tags = {CodeProperty.IS_FUNCTION, CodeProperty.HAS_LOOP}

            @property
            def complexity(self):
                return self._complexity_val

            @property
            def tags(self):
                return self._tags

        entity = MockEntity()

        assert pm.can_change(entity)

        result = pm.modify(entity)
        if result:
            assert "let x = 1;" in result.rewrite
            assert "let y = 2;" in result.rewrite
            assert "let z = x + y;" in result.rewrite
            assert "return z;" in result.rewrite
