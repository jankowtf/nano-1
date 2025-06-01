"""Pipeline visualizer for nanobricks compositions."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.tree import Tree

from nanobricks import NanobrickProtocol


@dataclass
class BrickNode:
    """Node representing a brick in the pipeline."""

    name: str
    type: str
    input_type: str
    output_type: str
    children: list["BrickNode"]
    metadata: dict[str, Any]


class PipelineVisualizer:
    """Visualizer for nanobrick pipelines."""

    def __init__(
        self,
        console: Console | None = None,
        show_types: bool = True,
        show_metadata: bool = False,
        export_format: str = "text",  # text, mermaid, graphviz
    ):
        """Initialize pipeline visualizer.

        Args:
            console: Rich console for output
            show_types: Whether to show input/output types
            show_metadata: Whether to show brick metadata
            export_format: Export format for diagrams
        """
        self.console = console or Console()
        self.show_types = show_types
        self.show_metadata = show_metadata
        self.export_format = export_format

    def analyze_pipeline(self, pipeline: NanobrickProtocol) -> BrickNode:
        """Analyze a pipeline structure.

        Args:
            pipeline: Pipeline to analyze

        Returns:
            Root node of the pipeline tree
        """
        return self._analyze_brick(pipeline)

    def _analyze_brick(self, brick: NanobrickProtocol) -> BrickNode:
        """Recursively analyze a brick."""
        name = getattr(brick, "name", brick.__class__.__name__)
        brick_type = brick.__class__.__name__

        # Extract type information
        input_type = "Any"
        output_type = "Any"

        if hasattr(brick, "__orig_bases__"):
            for base in brick.__orig_bases__:
                if hasattr(base, "__args__") and len(base.__args__) >= 2:
                    input_type = self._format_type(base.__args__[0])
                    output_type = self._format_type(base.__args__[1])
                    break

        # Check for composite structure
        children = []
        if hasattr(brick, "bricks") and isinstance(brick.bricks, list):
            # It's a composite brick
            for child in brick.bricks:
                children.append(self._analyze_brick(child))
        elif hasattr(brick, "branches") and isinstance(brick.branches, dict):
            # It's a branching brick
            for condition, branch in brick.branches.items():
                child_node = self._analyze_brick(branch)
                child_node.metadata["condition"] = str(condition)
                children.append(child_node)

        # Collect metadata
        metadata = {
            "version": getattr(brick, "version", "1.0.0"),
            "skills": getattr(brick, "__skills__", []),
        }

        return BrickNode(
            name=name,
            type=brick_type,
            input_type=input_type,
            output_type=output_type,
            children=children,
            metadata=metadata,
        )

    def _format_type(self, type_obj: Any) -> str:
        """Format type object to string."""
        if type_obj is None:
            return "None"
        if hasattr(type_obj, "__name__"):
            return type_obj.__name__
        return str(type_obj).replace("typing.", "")

    def visualize(self, pipeline: NanobrickProtocol, output_file: Path | None = None):
        """Visualize a pipeline.

        Args:
            pipeline: Pipeline to visualize
            output_file: Optional file to save output
        """
        root = self.analyze_pipeline(pipeline)

        if self.export_format == "text":
            output = self._render_text(root)
        elif self.export_format == "mermaid":
            output = self._render_mermaid(root)
        elif self.export_format == "graphviz":
            output = self._render_graphviz(root)
        else:
            raise ValueError(f"Unknown export format: {self.export_format}")

        if output_file:
            output_file.write_text(output)
        else:
            if self.export_format == "text":
                # For text, use Rich console
                tree = self._build_rich_tree(root)
                self.console.print(tree)
            else:
                # For other formats, just print
                self.console.print(output)

    def _render_text(self, root: BrickNode) -> str:
        """Render as text representation."""
        lines = []
        self._render_text_node(root, lines, "", True)
        return "\n".join(lines)

    def _render_text_node(
        self, node: BrickNode, lines: list[str], prefix: str, is_last: bool
    ):
        """Recursively render a node as text."""
        # Node line
        connector = "└── " if is_last else "├── "
        line = f"{prefix}{connector}{node.name}"

        if self.show_types:
            line += f" [{node.input_type} → {node.output_type}]"

        lines.append(line)

        # Metadata
        if self.show_metadata and node.metadata:
            meta_prefix = prefix + ("    " if is_last else "│   ")
            for key, value in node.metadata.items():
                if value:  # Only show non-empty values
                    lines.append(f"{meta_prefix}  {key}: {value}")

        # Children
        child_prefix = prefix + ("    " if is_last else "│   ")
        for i, child in enumerate(node.children):
            is_last_child = i == len(node.children) - 1
            self._render_text_node(child, lines, child_prefix, is_last_child)

    def _build_rich_tree(self, root: BrickNode) -> Tree:
        """Build a Rich tree for display."""
        # Root
        label = f"[bold blue]{root.name}[/bold blue]"
        if self.show_types:
            label += f" [dim]({root.input_type} → {root.output_type})[/dim]"

        tree = Tree(label)

        # Add children
        for child in root.children:
            self._add_rich_node(tree, child)

        return tree

    def _add_rich_node(self, parent: Tree, node: BrickNode):
        """Add a node to Rich tree."""
        label = f"[green]{node.name}[/green]"
        if self.show_types:
            label += f" [dim]({node.input_type} → {node.output_type})[/dim]"

        child_tree = parent.add(label)

        # Add metadata
        if self.show_metadata:
            for key, value in node.metadata.items():
                if value:
                    child_tree.add(f"[yellow]{key}[/yellow]: {value}")

        # Add children
        for child in node.children:
            self._add_rich_node(child_tree, child)

    def _render_mermaid(self, root: BrickNode) -> str:
        """Render as Mermaid diagram."""
        lines = ["graph TD"]
        node_id = 0

        def get_node_id():
            nonlocal node_id
            node_id += 1
            return f"node{node_id}"

        def render_node(node: BrickNode, parent_id: str | None = None) -> str:
            current_id = get_node_id()

            # Node definition
            label = node.name
            if self.show_types:
                label += f"\\n{node.input_type} → {node.output_type}"

            lines.append(f'    {current_id}["{label}"]')

            # Connection from parent
            if parent_id:
                connector = "-->"
                if "condition" in node.metadata:
                    connector = f"-->|{node.metadata['condition']}|"
                lines.append(f"    {parent_id} {connector} {current_id}")

            # Render children
            for child in node.children:
                render_node(child, current_id)

            return current_id

        render_node(root)
        return "\n".join(lines)

    def _render_graphviz(self, root: BrickNode) -> str:
        """Render as Graphviz DOT format."""
        lines = ["digraph Pipeline {", "    rankdir=LR;", "    node [shape=box];"]
        node_id = 0

        def get_node_id():
            nonlocal node_id
            node_id += 1
            return f"node{node_id}"

        def render_node(node: BrickNode, parent_id: str | None = None) -> str:
            current_id = get_node_id()

            # Node definition
            label = node.name
            if self.show_types:
                label += f"\\n{node.input_type} → {node.output_type}"

            lines.append(f'    {current_id} [label="{label}"];')

            # Connection from parent
            if parent_id:
                edge_label = ""
                if "condition" in node.metadata:
                    edge_label = f' [label="{node.metadata["condition"]}"]'
                lines.append(f"    {parent_id} -> {current_id}{edge_label};")

            # Render children
            for child in node.children:
                render_node(child, current_id)

            return current_id

        render_node(root)
        lines.append("}")
        return "\n".join(lines)

    def compare_pipelines(
        self, pipeline1: NanobrickProtocol, pipeline2: NanobrickProtocol
    ) -> dict[str, Any]:
        """Compare two pipeline structures.

        Args:
            pipeline1: First pipeline
            pipeline2: Second pipeline

        Returns:
            Comparison results
        """
        tree1 = self.analyze_pipeline(pipeline1)
        tree2 = self.analyze_pipeline(pipeline2)

        comparison = {
            "identical": self._trees_equal(tree1, tree2),
            "depth1": self._tree_depth(tree1),
            "depth2": self._tree_depth(tree2),
            "brick_count1": self._count_bricks(tree1),
            "brick_count2": self._count_bricks(tree2),
            "differences": self._find_differences(tree1, tree2),
        }

        return comparison

    def _trees_equal(self, tree1: BrickNode, tree2: BrickNode) -> bool:
        """Check if two trees are structurally equal."""
        if tree1.name != tree2.name or tree1.type != tree2.type:
            return False

        if len(tree1.children) != len(tree2.children):
            return False

        for child1, child2 in zip(tree1.children, tree2.children, strict=False):
            if not self._trees_equal(child1, child2):
                return False

        return True

    def _tree_depth(self, node: BrickNode) -> int:
        """Calculate tree depth."""
        if not node.children:
            return 1
        return 1 + max(self._tree_depth(child) for child in node.children)

    def _count_bricks(self, node: BrickNode) -> int:
        """Count total bricks in tree."""
        return 1 + sum(self._count_bricks(child) for child in node.children)

    def _find_differences(
        self, tree1: BrickNode, tree2: BrickNode, path: str = ""
    ) -> list[str]:
        """Find structural differences between trees."""
        differences = []
        current_path = f"{path}/{tree1.name}" if path else tree1.name

        if tree1.name != tree2.name:
            differences.append(
                f"Name mismatch at {current_path}: {tree1.name} vs {tree2.name}"
            )

        if tree1.type != tree2.type:
            differences.append(
                f"Type mismatch at {current_path}: {tree1.type} vs {tree2.type}"
            )

        if tree1.input_type != tree2.input_type:
            differences.append(
                f"Input type mismatch at {current_path}: {tree1.input_type} vs {tree2.input_type}"
            )

        if tree1.output_type != tree2.output_type:
            differences.append(
                f"Output type mismatch at {current_path}: {tree1.output_type} vs {tree2.output_type}"
            )

        # Compare children
        for i, (child1, child2) in enumerate(
            zip(tree1.children, tree2.children, strict=False)
        ):
            differences.extend(self._find_differences(child1, child2, current_path))

        # Check for different number of children
        if len(tree1.children) != len(tree2.children):
            differences.append(
                f"Child count mismatch at {current_path}: "
                f"{len(tree1.children)} vs {len(tree2.children)}"
            )

        return differences


def visualize_pipeline(
    pipeline: NanobrickProtocol,
    format: str = "text",
    output_file: Path | None = None,
    **kwargs,
):
    """Convenience function to visualize a pipeline.

    Args:
        pipeline: Pipeline to visualize
        format: Output format (text, mermaid, graphviz)
        output_file: Optional file to save output
        **kwargs: Additional arguments for PipelineVisualizer
    """
    visualizer = PipelineVisualizer(export_format=format, **kwargs)
    visualizer.visualize(pipeline, output_file)
