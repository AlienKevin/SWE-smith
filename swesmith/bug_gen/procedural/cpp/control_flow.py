"""
Control flow-related procedural modifications for C++ code.
"""

import random

import tree_sitter_cpp as tscpp
from tree_sitter import Language, Parser

from swesmith.bug_gen.procedural.base import CommonPMs
from swesmith.bug_gen.procedural.cpp.base import CppProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity

CPP_LANGUAGE = Language(tscpp.language())


class ControlIfElseInvertModifier(CppProceduralModifier):
    """Invert if-else branches."""

    explanation: str = CommonPMs.CONTROL_IF_ELSE_INVERT.explanation
    name: str = CommonPMs.CONTROL_IF_ELSE_INVERT.name
    conditions: list = CommonPMs.CONTROL_IF_ELSE_INVERT.conditions
    min_complexity: int = 1  # Reduced from 5 to allow simpler code

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        if not self.flip():
            return None

        parser = Parser(CPP_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        modified_code = self._invert_if_else_statements(
            code_entity.src_code, tree.root_node
        )

        if modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _invert_if_else_statements(self, code: str, node) -> str:
        """Invert if-else statements (including else-if chains)."""
        candidates = []
        self._find_if_else_statements(node, candidates)
        # Also find if statements without else (we can add else with empty body)
        self._find_if_statements(node, candidates)

        if not candidates:
            return code

        target = random.choice(candidates)

        # Extract components
        condition = None
        if_body = None
        else_body = None

        for i, child in enumerate(target.children):
            if child.type == "parenthesized_expression":
                condition = code[child.start_byte : child.end_byte]
            elif child.type == "compound_statement" and if_body is None:
                if_body = code[child.start_byte : child.end_byte]
            elif child.type == "else":
                # Next sibling should be the else body
                if i + 1 < len(target.children):
                    else_node = target.children[i + 1]
                    if else_node.type == "compound_statement":
                        else_body = code[else_node.start_byte : else_node.end_byte]
                    elif else_node.type == "if_statement":
                        # Handle else-if: extract the if body as else body
                        for subchild in else_node.children:
                            if subchild.type == "compound_statement":
                                else_body = code[
                                    subchild.start_byte : subchild.end_byte
                                ]
                                break

        if condition and if_body:
            if else_body:
                # Swap bodies WITHOUT negating condition (creates actual bug)
                inverted = f"if {condition} {else_body} else {if_body}"
            else:
                # If no else, create one with empty body (inverts the logic)
                inverted = f"if {condition} {{}} else {if_body}"
            return code[: target.start_byte] + inverted + code[target.end_byte :]

        return code

    def _find_if_else_statements(self, node, candidates):
        """Find if-else statements (including else-if chains)."""
        if node.type == "if_statement":
            # Check if it has an else branch (including else-if)
            has_else = False

            for i, child in enumerate(node.children):
                if child.type == "else":
                    has_else = True
                    break

            # Accept both simple if-else and else-if chains
            if has_else:
                candidates.append(node)

        for child in node.children:
            self._find_if_else_statements(child, candidates)

    def _find_if_statements(self, node, candidates):
        """Find if statements without else (to add else with empty body)."""
        if node.type == "if_statement":
            # Check if it has an else branch
            has_else = False
            for child in node.children:
                if child.type == "else":
                    has_else = True
                    break

            # Only add if statements without else
            if not has_else:
                candidates.append(node)

        for child in node.children:
            self._find_if_statements(child, candidates)


class ControlShuffleLinesModifier(CppProceduralModifier):
    """Shuffle independent lines within a block."""

    explanation: str = CommonPMs.CONTROL_SHUFFLE_LINES.explanation
    name: str = CommonPMs.CONTROL_SHUFFLE_LINES.name
    conditions: list = CommonPMs.CONTROL_SHUFFLE_LINES.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        if not self.flip():
            return None

        parser = Parser(CPP_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        modified_code = self._shuffle_lines(code_entity.src_code, tree.root_node)

        if modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _shuffle_lines(self, code: str, node) -> str:
        """Shuffle statements in blocks."""
        candidates = []
        self._find_blocks(node, candidates)

        if not candidates:
            return code

        target = random.choice(candidates)
        statements = [
            child
            for child in target.children
            if child.type
            in [
                "expression_statement",
                "declaration",
                "return_statement",
            ]
        ]

        if len(statements) < 2:
            return code

        # Extract statement texts
        stmt_texts = [code[stmt.start_byte : stmt.end_byte] for stmt in statements]

        # Shuffle
        original_order = stmt_texts.copy()
        random.shuffle(stmt_texts)

        # If nothing changed, try again or return original
        if stmt_texts == original_order:
            return code

        # Reconstruct the block
        first_stmt = statements[0]
        last_stmt = statements[-1]

        # Get the indentation from the first statement
        indent_start = first_stmt.start_byte
        while indent_start > 0 and code[indent_start - 1] in [" ", "\t"]:
            indent_start -= 1

        indent = code[indent_start : first_stmt.start_byte]

        # Build new block content
        new_block = "\n".join(indent + stmt for stmt in stmt_texts)

        return (
            code[:indent_start] + new_block + "\n" + indent[:-4]
            if len(indent) >= 4
            else indent
        ) + code[last_stmt.end_byte :]

    def _find_blocks(self, node, candidates):
        """Find blocks with multiple statements."""
        if node.type == "compound_statement":
            statements = [
                child
                for child in node.children
                if child.type
                in [
                    "expression_statement",
                    "declaration",
                    "return_statement",
                ]
            ]
            if len(statements) >= 2:
                candidates.append(node)
        for child in node.children:
            self._find_blocks(child, candidates)
