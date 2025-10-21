import pytest
from swesmith.bug_gen.procedural.rust.remove import (
    RemoveLoopModifier,
    RemoveConditionalModifier,
    RemoveAssignModifier,
)


@pytest.mark.parametrize(
    "src,expected",
    [
        (
            """fn foo() -> i32 {
    for i in 0..3 {
        println!("{}", i);
    }
    return 1;
}""",
            """fn foo() -> i32 {
    
    return 1;
}""",
        ),
        (
            """fn bar() -> i32 {
    while true {
        break;
    }
    return 2;
}""",
            """fn bar() -> i32 {
    
    return 2;
}""",
        ),
        (
            """fn baz() -> i32 {
    let mut sum = 0;
    for i in 0..10 {
        sum += i;
    }
    sum
}""",
            """fn baz() -> i32 {
    let mut sum = 0;
    
    sum
}""",
        ),
    ],
)
def test_remove_loop_modifier(src, expected):
    """Test that RemoveLoopModifier removes loop statements."""
    from swesmith.bug_gen.procedural.rust.remove import RUST_LANGUAGE
    from tree_sitter import Parser

    parser = Parser(RUST_LANGUAGE)
    tree = parser.parse(bytes(src, "utf8"))

    modifier = RemoveLoopModifier(likelihood=1.0, seed=42)
    result = modifier._remove_loops(src, tree.root_node)

    assert result.strip() == expected.strip(), (
        f"Expected:\n{expected}\n\nGot:\n{result}"
    )


@pytest.mark.parametrize(
    "src,expected",
    [
        (
            """fn foo(x: i32) -> i32 {
    if x > 0 {
        return x;
    }
    return 0;
}""",
            """fn foo(x: i32) -> i32 {
    
    return 0;
}""",
        ),
        (
            """fn bar(x: i32) -> i32 {
    if x < 0 {
        return -1;
    } else {
        return 1;
    }
}""",
            """fn bar(x: i32) -> i32 {
    
}""",
        ),
        (
            """fn baz(x: i32) -> i32 {
    let mut result = 0;
    if x > 10 {
        result = x * 2;
    }
    result
}""",
            """fn baz(x: i32) -> i32 {
    let mut result = 0;
    
    result
}""",
        ),
    ],
)
def test_remove_conditional_modifier(src, expected):
    """Test that RemoveConditionalModifier removes conditional statements."""
    from swesmith.bug_gen.procedural.rust.remove import RUST_LANGUAGE
    from tree_sitter import Parser

    parser = Parser(RUST_LANGUAGE)
    tree = parser.parse(bytes(src, "utf8"))

    modifier = RemoveConditionalModifier(likelihood=1.0, seed=42)
    result = modifier._remove_conditionals(src, tree.root_node)

    assert result.strip() == expected.strip(), (
        f"Expected:\n{expected}\n\nGot:\n{result}"
    )


@pytest.mark.parametrize(
    "src,expected",
    [
        (
            """fn foo() -> i32 {
    let x = 1;
    return x;
}""",
            """fn foo() -> i32 {
    
    return x;
}""",
        ),
        (
            """fn bar() -> i32 {
    let mut y = 2;
    y += 3;
    return y;
}""",
            """fn bar() -> i32 {
    
    y += 3;
    return y;
}""",
        ),
        (
            """fn baz() -> i32 {
    let z: i32 = 10;
    z * 2
}""",
            """fn baz() -> i32 {
    
    z * 2
}""",
        ),
        (
            """fn qux() -> i32 {
    let mut a = 5;
    a *= 2;
    a
}""",
            """fn qux() -> i32 {
    
    a *= 2;
    a
}""",
        ),
    ],
)
def test_remove_assign_modifier(src, expected):
    """Test that RemoveAssignModifier removes assignment statements."""
    from swesmith.bug_gen.procedural.rust.remove import RUST_LANGUAGE
    from tree_sitter import Parser

    parser = Parser(RUST_LANGUAGE)
    tree = parser.parse(bytes(src, "utf8"))

    modifier = RemoveAssignModifier(likelihood=1.0, seed=42)
    result = modifier._remove_assignments(src, tree.root_node)

    assert result.strip() == expected.strip(), (
        f"Expected:\n{expected}\n\nGot:\n{result}"
    )
