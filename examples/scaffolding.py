"""Example of using the scaffolding CLI.

This example shows how to use the nanobrick CLI to create new projects.
"""

import subprocess
import sys
from pathlib import Path
import tempfile
import shutil


def run_command(cmd: list[str]) -> str:
    """Run a command and return output."""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout


def main():
    """Demonstrate scaffolding functionality."""
    print("Nanobrick Scaffolding Example")
    print("=" * 50)
    
    # Create a temporary directory for our example
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"\nWorking in temporary directory: {tmpdir}")
        
        # Create a new project
        project_name = "my-data-processor"
        print(f"\n1. Creating new project: {project_name}")
        
        # Since we're in development, run the CLI module directly
        cmd = [
            sys.executable, "-m", "nanobricks.cli.main",
            "new", "new", project_name,
            "--description", "A data processing nanobrick",
            "--author", "Example Author",
            "--email", "author@example.com",
            "--output", tmpdir,
            "--no-interactive"
        ]
        
        try:
            output = run_command(cmd)
            print(output)
        except subprocess.CalledProcessError as e:
            print(f"Error: {e.stderr}")
            return
        
        # Show project structure
        project_dir = Path(tmpdir) / project_name
        print(f"\n2. Project structure created at: {project_dir}")
        
        # List files recursively
        for path in sorted(project_dir.rglob("*")):
            if path.is_file():
                indent = "  " * (len(path.relative_to(project_dir).parts) - 1)
                print(f"{indent}├── {path.name}")
        
        # Show key file contents
        print("\n3. Key file contents:")
        
        # Show core.py
        core_file = project_dir / "src" / "my_data_processor" / "core.py"
        print(f"\n--- {core_file.relative_to(project_dir)} ---")
        print(core_file.read_text()[:500] + "...")
        
        # Show test file
        test_file = project_dir / "tests" / "test_my_data_processor.py"
        print(f"\n--- {test_file.relative_to(project_dir)} ---")
        print(test_file.read_text()[:400] + "...")
        
        # Show nanobrick.toml
        toml_file = project_dir / "nanobrick.toml"
        print(f"\n--- {toml_file.relative_to(project_dir)} ---")
        print(toml_file.read_text())
        
        print("\n4. Next steps:")
        print(f"   cd {project_name}")
        print("   pip install -e .")
        print("   pytest")
        print("   # Start developing your nanobrick!")


if __name__ == "__main__":
    main()