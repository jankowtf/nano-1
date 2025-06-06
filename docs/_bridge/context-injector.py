#!/usr/bin/env python3
"""
Context Injector for Nanobricks Documentation
Bridges human-readable and AI-optimized documentation.
"""

import yaml
import json
from pathlib import Path
from typing import Dict, Any, List
from jinja2 import Environment, FileSystemLoader
import re


class ContextInjector:
    """Injects AI-optimized context into Quarto documents."""
    
    def __init__(self, quarto_dir: Path, agentic_dir: Path):
        self.quarto_dir = Path(quarto_dir)
        self.agentic_dir = Path(agentic_dir)
        self.contexts = self._load_contexts()
        self.env = Environment(loader=FileSystemLoader(str(agentic_dir / "_templates")))
    
    def _load_contexts(self) -> Dict[str, Any]:
        """Load all context files."""
        contexts = {}
        context_dir = self.agentic_dir / "_contexts"
        for context_file in context_dir.glob("*.yaml"):
            with open(context_file) as f:
                contexts[context_file.stem] = yaml.safe_load(f)
        return contexts
    
    def inject_ai_blocks(self, qmd_content: str, context_name: str) -> str:
        """Inject AI-specific blocks into Quarto markdown."""
        if context_name not in self.contexts:
            return qmd_content
        
        context = self.contexts[context_name]
        
        # Create AI context block
        ai_context_block = self._create_ai_context_block(context)
        
        # Create AI instructions block
        ai_instructions_block = self._create_ai_instructions_block(context)
        
        # Inject after YAML frontmatter
        lines = qmd_content.split('\n')
        injection_point = self._find_injection_point(lines)
        
        # Insert AI blocks
        lines.insert(injection_point, ai_context_block)
        lines.insert(injection_point + 1, "")
        lines.insert(injection_point + 2, ai_instructions_block)
        lines.insert(injection_point + 3, "")
        
        return '\n'.join(lines)
    
    def _create_ai_context_block(self, context: Dict[str, Any]) -> str:
        """Create the AI context block."""
        return f""":::{.ai-context}
IMMEDIATE_CONTEXT: {context.get('immediate_context', 'Unknown')}
PREREQUISITES: {json.dumps(context.get('prerequisites', []))}
SUCCESS_CRITERIA: {json.dumps(context.get('success_criteria', []))}
COMMON_ERRORS: {json.dumps(context.get('common_errors', []))}
:::"""
    
    def _create_ai_instructions_block(self, context: Dict[str, Any]) -> str:
        """Create the AI instructions block with copy-paste code."""
        code_template = context.get('code_template', '')
        return f""":::{.ai-instructions}
```python
# COPY-PASTE-MODIFY:
{code_template}
```

**VALIDATION_COMMAND**: `{context.get('validation_command', 'pytest')}`
**EXPECTED_OUTPUT**: {context.get('expected_output', 'Tests pass')}
:::"""
    
    def _find_injection_point(self, lines: List[str]) -> int:
        """Find where to inject AI blocks (after frontmatter)."""
        in_frontmatter = False
        for i, line in enumerate(lines):
            if line.strip() == '---':
                if in_frontmatter:
                    return i + 1  # After closing ---
                in_frontmatter = True
        return 0
    
    def process_directory(self):
        """Process all Quarto files with AI context."""
        for qmd_file in self.quarto_dir.rglob("*.qmd"):
            # Check if file has ai-context in frontmatter
            content = qmd_file.read_text()
            if match := re.search(r'ai-context:\s*(\w+)\.context\.yaml', content):
                context_name = match.group(1)
                print(f"Injecting AI context '{context_name}' into {qmd_file.name}")
                
                # Skip if already has AI blocks
                if ":::{.ai-context}" not in content:
                    new_content = self.inject_ai_blocks(content, context_name)
                    qmd_file.write_text(new_content)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: context-injector.py <quarto_dir> <agentic_dir>")
        sys.exit(1)
    
    injector = ContextInjector(Path(sys.argv[1]), Path(sys.argv[2]))
    injector.process_directory()