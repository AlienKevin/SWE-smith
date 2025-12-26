"""
JavaScript remove modifiers for procedural bug generation using tree-sitter.
"""

import tree_sitter_javascript as tsjs
from swesmith.bug_gen.procedural.base import CommonPMs
from swesmith.bug_gen.procedural.javascript.base import JavaScriptProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity
from tree_sitter import Language, Parser

JS_LANGUAGE = Language(tsjs.language())


class RemoveLoopModifier(JavaScriptProceduralModifier):
    """Remove loop statements (for, while, do-while, for-in, for-of)"""

    explanation: str = CommonPMs.REMOVE_LOOP.explanation
    name: str = CommonPMs.REMOVE_LOOP.name
    conditions: list = CommonPMs.REMOVE_LOOP.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Remove a loop from the code."""
        # Parse the code
        parser = Parser(JS_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        # Find and remove loop statements
        modified_code = self._remove_loops(code_entity.src_code, tree.root_node)

        if modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _remove_loops(self, source_code: str, node) -> str:
        """Recursively find and remove loop statements."""
        removals = []

        def collect_loops(n):
            if n.type in [
                "for_statement",
                "for_in_statement",
                "for_of_statement",
                "while_statement",
                "do_statement",
            ]:
                if self.flip():
                    removals.append(n)
            for child in n.children:
                collect_loops(child)

        collect_loops(node)

        if not removals:
            return source_code

        # Apply removals from end to start to preserve byte offsets
        modified_source = source_code
        for loop_node in reversed(removals):
            start_byte = loop_node.start_byte
            end_byte = loop_node.end_byte

            # Remove the entire loop statement
            modified_source = modified_source[:start_byte] + modified_source[end_byte:]

        return modified_source


class RemoveConditionalModifier(JavaScriptProceduralModifier):
    """Remove conditional statements (if statements)"""

    explanation: str = CommonPMs.REMOVE_CONDITIONAL.explanation
    name: str = CommonPMs.REMOVE_CONDITIONAL.name
    conditions: list = CommonPMs.REMOVE_CONDITIONAL.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Remove an if statement from the code."""
        # Parse the code
        parser = Parser(JS_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        # Find and remove conditional statements
        modified_code = self._remove_conditionals(code_entity.src_code, tree.root_node)

        if modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _remove_conditionals(self, source_code: str, node) -> str:
        """Recursively find and remove if statements."""
        removals = []

        def collect_conditionals(n):
            if n.type == "if_statement":
                if self.flip():
                    removals.append(n)
            for child in n.children:
                collect_conditionals(child)

        collect_conditionals(node)

        if not removals:
            return source_code

        # Apply removals from end to start to preserve byte offsets
        modified_source = source_code
        for cond_node in reversed(removals):
            start_byte = cond_node.start_byte
            end_byte = cond_node.end_byte

            # Remove the entire conditional statement
            modified_source = modified_source[:start_byte] + modified_source[end_byte:]

        return modified_source


class RemoveAssignmentModifier(JavaScriptProceduralModifier):
    """Remove assignment statements"""

    explanation: str = CommonPMs.REMOVE_ASSIGNMENT.explanation
    name: str = CommonPMs.REMOVE_ASSIGNMENT.name
    conditions: list = CommonPMs.REMOVE_ASSIGNMENT.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Remove an assignment statement from the code."""
        # Parse the code
        parser = Parser(JS_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        # Find and remove assignment statements
        modified_code = self._remove_assignments(code_entity.src_code, tree.root_node)

        if modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _remove_assignments(self, source_code: str, node) -> str:
        """Recursively find and remove assignment statements."""
        removals = []

        def collect_assignments(n):
            # Look for assignment expressions and variable declarations
            if n.type in [
                "assignment_expression",
                "variable_declaration",
                "augmented_assignment_expression",
            ]:
                if self.flip():
                    # For expression statements, remove the whole statement including semicolon
                    if n.parent and n.parent.type == "expression_statement":
                        removals.append(n.parent)
                    else:
                        removals.append(n)
            for child in n.children:
                collect_assignments(child)

        collect_assignments(node)

        if not removals:
            return source_code

        # Apply removals from end to start to preserve byte offsets
        modified_source = source_code
        for assign_node in reversed(removals):
            start_byte = assign_node.start_byte
            end_byte = assign_node.end_byte

            # Find the end of the line (include semicolon and newline)
            while end_byte < len(modified_source) and modified_source[end_byte] in [
                " ",
                "\t",
                ";",
            ]:
                end_byte += 1
            if end_byte < len(modified_source) and modified_source[end_byte] == "\n":
                end_byte += 1

            # Remove the assignment statement
            modified_source = modified_source[:start_byte] + modified_source[end_byte:]

        return modified_source
