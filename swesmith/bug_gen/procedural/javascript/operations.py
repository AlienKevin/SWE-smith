"""
JavaScript operation modifiers for procedural bug generation using tree-sitter.
"""

import tree_sitter_javascript as tsjs
from swesmith.bug_gen.procedural.javascript.base import JavaScriptProceduralModifier
from swesmith.bug_gen.procedural.base import CommonPMs
from swesmith.constants import CodeProperty, BugRewrite, CodeEntity
from tree_sitter import Language, Parser

JS_LANGUAGE = Language(tsjs.language())


class OperationChangeModifier(JavaScriptProceduralModifier):
    """Change operators within similar groups (e.g., +/-, *//%, etc.)"""

    explanation: str = CommonPMs.OPERATION_CHANGE.explanation
    name: str = CommonPMs.OPERATION_CHANGE.name
    conditions: list = CommonPMs.OPERATION_CHANGE.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Change operators to others in their group."""
        if not self.flip():
            return None

        parser = Parser(JS_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        modified_code = self._change_operators(code_entity.src_code, tree.root_node)

        if modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _change_operators(self, source_code: str, node) -> str:
        """Find and change binary operators within their groups."""
        changes = []

        # Operator groups
        operator_groups = {
            "+": ["+", "-"],
            "-": ["+", "-"],
            "*": ["*", "/", "%"],
            "/": ["*", "/", "%"],
            "%": ["*", "/", "%"],
            "&": ["&", "|", "^"],
            "|": ["&", "|", "^"],
            "^": ["&", "|", "^"],
            "<<": ["<<", ">>"],
            ">>": ["<<", ">>"],
        }

        def collect_binary_ops(n):
            if n.type == "binary_expression":
                # Find the operator child
                for child in n.children:
                    if child.type in operator_groups:
                        operator = child.type
                        group = operator_groups[operator]
                        # Choose a different operator from the group
                        other_ops = [op for op in group if op != operator]
                        if other_ops and self.flip():
                            new_op = self.rand.choice(other_ops)
                            changes.append({"node": child, "new_op": new_op})
                        break

            for child in n.children:
                collect_binary_ops(child)

        collect_binary_ops(node)

        if not changes:
            return source_code

        # Work with bytes for modifications
        modified_source = source_code.encode("utf-8")
        for change in reversed(changes):
            node = change["node"]
            new_op = change["new_op"]

            modified_source = (
                modified_source[: node.start_byte]
                + new_op.encode("utf-8")
                + modified_source[node.end_byte :]
            )

        return modified_source.decode("utf-8")


class OperationFlipOperatorModifier(JavaScriptProceduralModifier):
    """Flip operators to their opposites (e.g., == to !=, < to >, etc.)"""

    explanation: str = "The operators in an expression are likely incorrect."
    name: str = "func_pm_op_flip"
    conditions: list = [CodeProperty.IS_FUNCTION, CodeProperty.HAS_BINARY_OP]

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Flip operators to their opposites."""
        if not self.flip():
            return None

        parser = Parser(JS_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        modified_code = self._flip_operators(code_entity.src_code, tree.root_node)

        if modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _flip_operators(self, source_code: str, node) -> str:
        """Find and flip binary operators to their opposites."""
        changes = []

        operator_flips = {
            "===": "!==",
            "!==": "===",
            "==": "!=",
            "!=": "==",
            "<=": ">",
            ">=": "<",
            "<": ">=",
            ">": "<=",
            "&&": "||",
            "||": "&&",
            "+": "-",
            "-": "+",
            "*": "/",
            "/": "*",
        }

        def collect_binary_ops(n):
            if n.type == "binary_expression":
                # Find the operator child
                for child in n.children:
                    if child.type in operator_flips:
                        if self.flip():
                            changes.append(
                                {"node": child, "new_op": operator_flips[child.type]}
                            )
                        break

            for child in n.children:
                collect_binary_ops(child)

        collect_binary_ops(node)

        if not changes:
            return source_code

        # Work with bytes for modifications
        modified_source = source_code.encode("utf-8")
        for change in reversed(changes):
            node = change["node"]
            new_op = change["new_op"]

            modified_source = (
                modified_source[: node.start_byte]
                + new_op.encode("utf-8")
                + modified_source[node.end_byte :]
            )

        return modified_source.decode("utf-8")


class OperationSwapOperandsModifier(JavaScriptProceduralModifier):
    """Swap operands in binary operations (e.g., a + b becomes b + a)"""

    explanation: str = CommonPMs.OPERATION_SWAP_OPERANDS.explanation
    name: str = CommonPMs.OPERATION_SWAP_OPERANDS.name
    conditions: list = CommonPMs.OPERATION_SWAP_OPERANDS.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Swap left and right operands."""
        if not self.flip():
            return None

        parser = Parser(JS_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        modified_code = self._swap_operands(code_entity.src_code, tree.root_node)

        if modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _swap_operands(self, source_code: str, node) -> str:
        """Find and swap operands in binary expressions."""
        changes = []
        source_bytes = source_code.encode("utf-8")

        def collect_binary_ops(n):
            if n.type == "binary_expression" and len(n.children) >= 3:
                # Binary expression has: left, operator, right
                left = n.children[0]
                operator_node = n.children[1]
                right = n.children[2]

                if self.flip():
                    # For comparison operators, we might need to flip them too
                    operator = operator_node.type
                    if operator in ["<", ">", "<=", ">="]:
                        op_flip = {"<": ">", ">": "<", "<=": ">=", ">=": "<="}
                        operator = op_flip.get(operator, operator)

                    changes.append(
                        {
                            "node": n,
                            "left": left,
                            "right": right,
                            "operator": operator,
                        }
                    )

            for child in n.children:
                collect_binary_ops(child)

        collect_binary_ops(node)

        if not changes:
            return source_code

        # Work with bytes for modifications
        modified_source = source_bytes
        for change in reversed(changes):
            node = change["node"]
            left = change["left"]
            right = change["right"]
            operator = change["operator"]

            left_text = source_bytes[left.start_byte : left.end_byte].decode("utf-8")
            right_text = source_bytes[right.start_byte : right.end_byte].decode("utf-8")

            # Swap: left op right -> right op left
            swapped = f"{right_text} {operator} {left_text}"

            modified_source = (
                modified_source[: node.start_byte]
                + swapped.encode("utf-8")
                + modified_source[node.end_byte :]
            )

        return modified_source.decode("utf-8")


class OperationChangeConstantsModifier(JavaScriptProceduralModifier):
    """Change numeric constants to introduce off-by-one errors"""

    explanation: str = CommonPMs.OPERATION_CHANGE_CONSTANTS.explanation
    name: str = CommonPMs.OPERATION_CHANGE_CONSTANTS.name
    conditions: list = CommonPMs.OPERATION_CHANGE_CONSTANTS.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Change constants by small amounts."""
        if not self.flip():
            return None

        parser = Parser(JS_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        modified_code = self._change_constants(code_entity.src_code, tree.root_node)

        if modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _change_constants(self, source_code: str, node) -> str:
        """Find and change numeric constants."""
        changes = []
        source_bytes = source_code.encode("utf-8")

        def collect_numbers(n):
            if n.type == "number":
                if self.flip():
                    try:
                        value_text = source_bytes[n.start_byte : n.end_byte].decode(
                            "utf-8"
                        )
                        value = int(value_text)
                        # Small off-by-one changes
                        new_value = value + self.rand.choice([-1, 1, -2, 2])
                        changes.append({"node": n, "new_value": str(new_value)})
                    except ValueError:
                        pass  # Skip floats and hex numbers

            for child in n.children:
                collect_numbers(child)

        collect_numbers(node)

        if not changes:
            return source_code

        # Work with bytes for modifications
        modified_source = source_bytes
        for change in reversed(changes):
            node = change["node"]
            new_value = change["new_value"]

            modified_source = (
                modified_source[: node.start_byte]
                + new_value.encode("utf-8")
                + modified_source[node.end_byte :]
            )

        return modified_source.decode("utf-8")


class OperationBreakChainsModifier(JavaScriptProceduralModifier):
    """Break chained operations by removing parts of the chain"""

    explanation: str = CommonPMs.OPERATION_BREAK_CHAINS.explanation
    name: str = CommonPMs.OPERATION_BREAK_CHAINS.name
    conditions: list = CommonPMs.OPERATION_BREAK_CHAINS.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Break chained binary operations."""
        if not self.flip():
            return None

        parser = Parser(JS_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        modified_code = self._break_chains(code_entity.src_code, tree.root_node)

        if modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _break_chains(self, source_code: str, node) -> str:
        """Find and break chained operations."""
        changes = []
        source_bytes = source_code.encode("utf-8")

        def collect_chains(n):
            if n.type == "binary_expression" and len(n.children) >= 3:
                left = n.children[0]
                operator = n.children[1]
                right = n.children[2]

                # Check if left or right is also a binary expression (chain)
                if left.type == "binary_expression" and self.flip():
                    # Break left chain: keep only the right part
                    # (a + b) + c -> b + c (take right of left chain)
                    if len(left.children) >= 3:
                        left_right = left.children[2]
                        left_right_text = source_bytes[
                            left_right.start_byte : left_right.end_byte
                        ].decode("utf-8")
                        operator_text = source_bytes[
                            operator.start_byte : operator.end_byte
                        ].decode("utf-8")
                        right_text = source_bytes[
                            right.start_byte : right.end_byte
                        ].decode("utf-8")
                        changes.append(
                            {
                                "node": n,
                                "replacement": f"{left_right_text} {operator_text} {right_text}",
                            }
                        )

                elif right.type == "binary_expression" and self.flip():
                    # Break right chain: keep only the left part
                    # a + (b + c) -> a + b (take left of right chain)
                    if len(right.children) >= 3:
                        right_left = right.children[0]
                        left_text = source_bytes[
                            left.start_byte : left.end_byte
                        ].decode("utf-8")
                        operator_text = source_bytes[
                            operator.start_byte : operator.end_byte
                        ].decode("utf-8")
                        right_left_text = source_bytes[
                            right_left.start_byte : right_left.end_byte
                        ].decode("utf-8")
                        changes.append(
                            {
                                "node": n,
                                "replacement": f"{left_text} {operator_text} {right_left_text}",
                            }
                        )

            for child in n.children:
                collect_chains(child)

        collect_chains(node)

        if not changes:
            return source_code

        # Work with bytes for modifications
        modified_source = source_bytes
        for change in reversed(changes):
            node = change["node"]
            replacement = change["replacement"]

            modified_source = (
                modified_source[: node.start_byte]
                + replacement.encode("utf-8")
                + modified_source[node.end_byte :]
            )

        return modified_source.decode("utf-8")
