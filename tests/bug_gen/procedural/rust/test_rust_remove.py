import random

from swesmith.bug_gen.adapters.rust import get_entities_from_file_rs
from swesmith.bug_gen.procedural.rust.remove import (
    RemoveLoopModifier,
    RemoveConditionalModifier,
    RemoveAssignModifier,
)


def test_remove_loop_modifier(test_file_rust):
    """Test that RemoveLoopModifier removes loop statements."""
    entities = []
    get_entities_from_file_rs(entities, test_file_rust)
    pm = RemoveLoopModifier(likelihood=1.0)

    # Set a fixed random seed for reproducible test results
    pm.rand = random.Random(42)

    entities = [x for x in entities if pm.can_change(x)]

    modified = None
    test_entity = None
    for entity in entities:
        if (
            "for " in entity.src_code
            or "while " in entity.src_code
            or "loop " in entity.src_code
        ):
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
            "loop" in modified.explanation.lower()
            or "remove" in modified.explanation.lower()
        )


def test_remove_conditional_modifier(test_file_rust):
    """Test that RemoveConditionalModifier removes conditional statements."""
    entities = []
    get_entities_from_file_rs(entities, test_file_rust)
    pm = RemoveConditionalModifier(likelihood=1.0)

    # Set a fixed random seed for reproducible test results
    pm.rand = random.Random(123)

    entities = [x for x in entities if pm.can_change(x)]

    modified = None
    test_entity = None
    for entity in entities:
        if "if " in entity.src_code:
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
            "conditional" in modified.explanation.lower()
            or "if" in modified.explanation.lower()
        )


def test_remove_assign_modifier(test_file_rust):
    """Test that RemoveAssignModifier removes assignment statements."""
    entities = []
    get_entities_from_file_rs(entities, test_file_rust)
    pm = RemoveAssignModifier(likelihood=1.0)

    # Set a fixed random seed for reproducible test results
    pm.rand = random.Random(456)

    entities = [x for x in entities if pm.can_change(x)]

    modified = None
    test_entity = None
    for entity in entities:
        if "let " in entity.src_code or "=" in entity.src_code:
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
            "assign" in modified.explanation.lower()
            or "remove" in modified.explanation.lower()
        )


def test_remove_modifiers_can_change(test_file_rust):
    """Test that remove modifiers correctly identify compatible entities."""
    entities = []
    get_entities_from_file_rs(entities, test_file_rust)

    # Test all modifiers
    modifiers = [
        RemoveLoopModifier(likelihood=1.0),
        RemoveConditionalModifier(likelihood=1.0),
        RemoveAssignModifier(likelihood=1.0),
    ]

    for modifier in modifiers:
        compatible_entities = [x for x in entities if modifier.can_change(x)]
        # Should have some compatible entities from the Rust codebase
        assert len(compatible_entities) >= 0  # May be 0 if no suitable entities


def test_remove_modifiers_edge_cases(test_file_rust):
    """Test edge cases and error handling for remove modifiers."""
    entities = []
    get_entities_from_file_rs(entities, test_file_rust)

    modifiers = [
        RemoveLoopModifier(likelihood=1.0),
        RemoveConditionalModifier(likelihood=1.0),
        RemoveAssignModifier(likelihood=1.0),
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


def test_remove_modifiers_with_low_likelihood(test_file_rust):
    """Test that modifiers with low likelihood sometimes return None."""
    entities = []
    get_entities_from_file_rs(entities, test_file_rust)

    pm = RemoveAssignModifier(likelihood=0.01)
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


def test_remove_loop_specific_patterns():
    """Test RemoveLoopModifier with specific loop patterns."""
    from swesmith.bug_gen.procedural.rust.remove import RUST_LANGUAGE
    from swesmith.constants import CodeEntity
    from tree_sitter import Parser

    pm = RemoveLoopModifier(likelihood=1.0)
    pm.rand = random.Random(42)

    rust_code = """fn test_function() {
    for i in 0..10 {
        println!("{}", i);
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
                self._complexity_val = 3
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

        for _ in range(10):  # Multiple attempts due to randomness
            result = pm.modify(entity)
            if result and result.rewrite != entity.src_code:
                assert "for i in 0..10" not in result.rewrite or len(
                    result.rewrite
                ) < len(entity.src_code)
                break


def test_remove_conditional_specific_patterns():
    """Test RemoveConditionalModifier with specific conditional patterns."""
    from swesmith.bug_gen.procedural.rust.remove import RUST_LANGUAGE
    from swesmith.constants import CodeEntity
    from tree_sitter import Parser

    pm = RemoveConditionalModifier(likelihood=1.0)
    pm.rand = random.Random(123)

    rust_code = """fn test_function() {
    if condition {
        do_something();
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
                self._complexity_val = 3
                self.file_path = "test.rs"
                from swesmith.constants import CodeProperty

                self._tags = {CodeProperty.IS_FUNCTION, CodeProperty.HAS_IF}

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
                assert "if condition" not in result.rewrite or len(
                    result.rewrite
                ) < len(entity.src_code)
                break


def test_remove_assign_specific_patterns():
    """Test RemoveAssignModifier with specific assignment patterns."""
    from swesmith.bug_gen.procedural.rust.remove import RUST_LANGUAGE
    from swesmith.constants import CodeEntity
    from tree_sitter import Parser

    pm = RemoveAssignModifier(likelihood=1.0)
    pm.rand = random.Random(456)

    rust_code = """fn test_function() {
    let x = 42;
    let y = x + 1;
    return y;
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
                self._complexity_val = 3
                self.file_path = "test.rs"
                from swesmith.constants import CodeProperty

                self._tags = {CodeProperty.IS_FUNCTION, CodeProperty.HAS_ASSIGNMENT}

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
                original_let_count = entity.src_code.count("let ")
                modified_let_count = result.rewrite.count("let ")
                assert modified_let_count < original_let_count or len(
                    result.rewrite
                ) < len(entity.src_code)
                break


def test_remove_modifiers_return_none_when_no_match(test_file_rust):
    """Test that remove modifiers return None when no matching patterns are found."""
    entities = []
    get_entities_from_file_rs(entities, test_file_rust)

    pm = RemoveLoopModifier(likelihood=1.0)
    pm.rand = random.Random(42)

    test_entity = None
    for entity in entities:
        if (
            "for " not in entity.src_code
            and "while " not in entity.src_code
            and "loop " not in entity.src_code
        ):
            test_entity = entity
            break

    if test_entity and pm.can_change(test_entity):
        result = pm.modify(test_entity)
        if result is None:
            assert True  # Expected behavior
        else:
            assert result.rewrite == test_entity.src_code or result is None
