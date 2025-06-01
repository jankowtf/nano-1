"""Pipeline visualizer for nanobricks."""

from nanobricks import NanobrickProtocol


class PipelineVisualizer:
    """Visualize nanobrick pipelines."""

    def __init__(self, style: str = "ascii"):
        """Initialize visualizer.

        Args:
            style: Visualization style (ascii, mermaid, graphviz)
        """
        self.style = style

    def visualize(self, pipeline: NanobrickProtocol | list[NanobrickProtocol]) -> str:
        """Visualize a pipeline.

        Args:
            pipeline: Pipeline or list of bricks to visualize

        Returns:
            Visualization string
        """
        if self.style == "ascii":
            return self._ascii_visualization(pipeline)
        elif self.style == "mermaid":
            return self._mermaid_visualization(pipeline)
        elif self.style == "graphviz":
            return self._graphviz_visualization(pipeline)
        else:
            raise ValueError(f"Unknown style: {self.style}")

    def _get_bricks(
        self, pipeline: NanobrickProtocol | list[NanobrickProtocol]
    ) -> list[NanobrickProtocol]:
        """Extract bricks from pipeline."""
        if isinstance(pipeline, list):
            return pipeline
        elif hasattr(pipeline, "bricks"):
            return pipeline.bricks
        else:
            return [pipeline]

    def _get_brick_info(self, brick: NanobrickProtocol) -> dict[str, str]:
        """Get brick information."""
        return {
            "name": getattr(brick, "name", brick.__class__.__name__),
            "class": brick.__class__.__name__,
            "version": getattr(brick, "version", "0.0.0"),
        }

    def _ascii_visualization(
        self, pipeline: NanobrickProtocol | list[NanobrickProtocol]
    ) -> str:
        """Create ASCII visualization."""
        bricks = self._get_bricks(pipeline)

        if not bricks:
            return "Empty pipeline"

        lines = []
        lines.append("Pipeline Flow:")
        lines.append("=" * 50)
        lines.append("")

        for i, brick in enumerate(bricks):
            info = self._get_brick_info(brick)

            # Box for brick
            name_line = f"│ {info['name']:^20} │"
            class_line = f"│ {info['class']:^20} │"
            version_line = f"│ v{info['version']:^19} │"

            box_width = len(name_line)
            top_line = "┌" + "─" * (box_width - 2) + "┐"
            bottom_line = "└" + "─" * (box_width - 2) + "┘"

            if i == 0:
                lines.append("     INPUT")
                lines.append("       │")
                lines.append("       ▼")

            lines.append(top_line)
            lines.append(name_line)
            lines.append(class_line)
            lines.append(version_line)
            lines.append(bottom_line)

            if i < len(bricks) - 1:
                lines.append("       │")
                lines.append("       ▼")
            else:
                lines.append("       │")
                lines.append("       ▼")
                lines.append("     OUTPUT")

        return "\n".join(lines)

    def _mermaid_visualization(
        self, pipeline: NanobrickProtocol | list[NanobrickProtocol]
    ) -> str:
        """Create Mermaid diagram."""
        bricks = self._get_bricks(pipeline)

        if not bricks:
            return "graph LR\n    Empty[Empty Pipeline]"

        lines = []
        lines.append("graph LR")
        lines.append("    Input[Input]")

        # Add bricks
        for i, brick in enumerate(bricks):
            info = self._get_brick_info(brick)
            node_id = f"B{i}"
            label = f"{info['name']}\\n{info['class']}\\nv{info['version']}"
            lines.append(f"    {node_id}[{label}]")

        lines.append("    Output[Output]")

        # Add connections
        lines.append("    Input --> B0")
        for i in range(len(bricks) - 1):
            lines.append(f"    B{i} --> B{i + 1}")
        lines.append(f"    B{len(bricks) - 1} --> Output")

        # Add styling
        lines.append("    classDef brick fill:#f9f,stroke:#333,stroke-width:2px")
        for i in range(len(bricks)):
            lines.append(f"    class B{i} brick")

        return "\n".join(lines)

    def _graphviz_visualization(
        self, pipeline: NanobrickProtocol | list[NanobrickProtocol]
    ) -> str:
        """Create Graphviz DOT diagram."""
        bricks = self._get_bricks(pipeline)

        if not bricks:
            return 'digraph G {\n    "Empty Pipeline";\n}'

        lines = []
        lines.append("digraph Pipeline {")
        lines.append("    rankdir=TB;")
        lines.append("    node [shape=box, style=rounded];")
        lines.append("")

        # Add nodes
        lines.append('    "Input" [shape=ellipse, style=filled, fillcolor=lightblue];')

        for i, brick in enumerate(bricks):
            info = self._get_brick_info(brick)
            label = f"{info['name']}\\n{info['class']}\\nv{info['version']}"
            lines.append(
                f'    "B{i}" [label="{label}", style=filled, fillcolor=lightgreen];'
            )

        lines.append(
            '    "Output" [shape=ellipse, style=filled, fillcolor=lightcoral];'
        )
        lines.append("")

        # Add edges
        lines.append('    "Input" -> "B0";')
        for i in range(len(bricks) - 1):
            lines.append(f'    "B{i}" -> "B{i + 1}";')
        lines.append(f'    "B{len(bricks) - 1}" -> "Output";')

        lines.append("}")

        return "\n".join(lines)

    def save_visualization(
        self,
        pipeline: NanobrickProtocol | list[NanobrickProtocol],
        filename: str,
    ):
        """Save visualization to file.

        Args:
            pipeline: Pipeline to visualize
            filename: Output filename
        """
        viz = self.visualize(pipeline)

        with open(filename, "w") as f:
            f.write(viz)

        print(f"💾 Visualization saved to: {filename}")


def visualize_pipeline(
    pipeline: NanobrickProtocol | list[NanobrickProtocol],
    style: str = "ascii",
    save_to: str | None = None,
) -> str:
    """Quick function to visualize a pipeline.

    Args:
        pipeline: Pipeline to visualize
        style: Visualization style
        save_to: Optional filename to save to

    Returns:
        Visualization string
    """
    visualizer = PipelineVisualizer(style=style)
    viz = visualizer.visualize(pipeline)

    if save_to:
        visualizer.save_visualization(pipeline, save_to)

    return viz
