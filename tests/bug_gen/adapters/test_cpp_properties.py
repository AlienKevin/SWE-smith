import pytest
from swesmith.bug_gen.adapters.cpp import get_entities_from_file_cpp

@pytest.mark.parametrize(
    "func_definition,expected_complexity",
    [
        ("void f() { if (true) { return; } }", 2),
        ("void f() { for (int i = 0; i < 10; i++) { } }", 2),
        ("void f() { while (true) { break; } }", 2),
        ("void f() { do { } while (true); }", 2),
        ("void f() { try { } catch (...) { } }", 2),
        ("void f() { switch (x) { case 1: break; } }", 2),
        ("void f() { for (auto x : vec) { } }", 2), # range-based for
    ],
)
def test_get_entities_from_file_cpp_complexity_control_flow(tmp_path, func_definition, expected_complexity):
    source_file = tmp_path / "complexity.cpp"
    source_file.write_text(func_definition)
    entities = []
    get_entities_from_file_cpp(entities, str(source_file))
    assert len(entities) == 1
    assert entities[0].complexity == expected_complexity

def test_get_entities_from_file_cpp_complexity_nested(tmp_path):
    source_code = """
    void complexFunction(int x, int y, int z) {
        if (x > 0) {
            for (int i = 0; i < y; i++) {
                if (i == z) {
                    return;
                }
            }
        } else {
            switch (z) {
                case 1:
                    break;
                case 2:
                    break;
                default:
                    break;
            }
        }
    }
    """
    source_file = tmp_path / "nested.cpp"
    source_file.write_text(source_code)
    entities = []
    get_entities_from_file_cpp(entities, str(source_file))
    assert len(entities) == 1
    # Base: 1
    # if (x > 0): +1
    # for: +1
    # if (i == z): +1
    # switch/case 1: +1
    # switch/case 2: +1
    # default case: +1 (case_statement includes default)
    # Total: 1 + 1 + 1 + 1 + 1 + 1 + 1 = 7
    assert entities[0].complexity == 7

def test_get_entities_from_file_cpp_boolean_operators_complexity(tmp_path):
    # Currently C++ adapter does NOT increase complexity for boolean ops, unlike JS adapter.
    # We test for the current behavior (1).
    source_code = """
    void f(bool a, bool b, bool c) {
        bool res = a && b || c;
    }
    """
    source_file = tmp_path / "bool.cpp"
    source_file.write_text(source_code)
    entities = []
    get_entities_from_file_cpp(entities, str(source_file))
    assert len(entities) == 1
    assert entities[0].complexity == 1

def test_get_entities_from_file_cpp_methods(tmp_path):
    source_code = """
    class MyClass {
    public:
        void myMethod(int x) {
            if (x > 0) return;
        }
    };
    """
    source_file = tmp_path / "methods.cpp"
    source_file.write_text(source_code)
    entities = []
    get_entities_from_file_cpp(entities, str(source_file))
    # It parses 'myMethod' inside the class?
    # Based on cpp.py logic:
    # Query for function_definition.
    # C++ tree-sitter often treats methods inside classes as function_definitions too.
    # Let's verify if it catches it.
    # If standard 'function_definition' query is used, it should be found.
    
    assert len(entities) == 1
    assert entities[0].name == "myMethod"
    assert entities[0].complexity == 2

def test_get_entities_from_file_cpp_empty(tmp_path):
    source_file = tmp_path / "empty.cpp"
    source_file.write_text("")
    entities = []
    get_entities_from_file_cpp(entities, str(source_file))
    assert len(entities) == 0

def test_get_entities_from_file_cpp_comments_only(tmp_path):
    source_file = tmp_path / "comments.cpp"
    source_file.write_text("// Just a comment\n// Another comment")
    entities = []
    get_entities_from_file_cpp(entities, str(source_file))
    assert len(entities) == 0
