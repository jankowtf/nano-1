"""
Atomic Commits Skill for Nanobricks

This module provides advanced atomic commit functionality with AI-powered analysis,
automated splitting, validation, and workflow guidance. Designed for seamless
integration with both human developers and AI agents.
"""

import asyncio
import json
import re
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from nanobricks.protocol import NanobrickBase, T_deps, T_in, T_out
from nanobricks.skill import NanobrickEnhanced, Skill, register_skill


class CommitType(Enum):
    """Conventional commit types with semantic meaning."""

    FEAT = "feat"  # New feature
    FIX = "fix"  # Bug fix
    DOCS = "docs"  # Documentation only
    REFACTOR = "refactor"  # Code change without fixing bug or adding feature
    TEST = "test"  # Adding or updating tests
    CHORE = "chore"  # Maintenance tasks
    PERF = "perf"  # Performance improvements
    STYLE = "style"  # Code style changes (formatting, etc)
    CI = "ci"  # CI/CD changes
    BUILD = "build"  # Build system changes


@dataclass
class CommitMessage:
    """Structured commit message following conventional format."""

    type: CommitType
    scope: str | None
    description: str
    body: str | None = None
    footer: str | None = None
    breaking: bool = False

    def __str__(self) -> str:
        """Format as conventional commit message."""
        base = f"{self.type.value}"
        if self.scope:
            base += f"({self.scope})"
        if self.breaking:
            base += "!"
        base += f": {self.description}"

        parts = [base]
        if self.body:
            parts.extend(["", self.body])
        if self.footer:
            parts.extend(["", self.footer])

        return "\n".join(parts)


@dataclass
class FileChange:
    """Represents a file change in git."""

    path: Path
    status: str  # Added, Modified, Deleted, Renamed
    additions: int = 0
    deletions: int = 0

    @property
    def is_test(self) -> bool:
        """Check if this is a test file."""
        return (
            "test" in self.path.name or self.path.parts and "tests" in self.path.parts
        )

    @property
    def is_docs(self) -> bool:
        """Check if this is a documentation file."""
        return self.path.suffix in {".md", ".qmd", ".rst", ".txt"} or (
            self.path.parts and "docs" in self.path.parts
        )

    @property
    def module(self) -> str | None:
        """Extract module/component from path."""
        if "src" in self.path.parts:
            idx = self.path.parts.index("src")
            if idx + 2 < len(self.path.parts):
                return self.path.parts[idx + 2]
        return None


@dataclass
class LogicalChange:
    """A logical unit of changes that should be committed together."""

    files: list[FileChange]
    suggested_type: CommitType
    suggested_scope: str | None
    suggested_description: str
    reasoning: str
    complexity: str  # simple, medium, complex
    dependencies: list[int] = None  # Indices of dependent changes

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class AtomicCommitAnalyzer(NanobrickBase[dict[str, Any], dict[str, Any], None]):
    """Analyzes git changes to identify atomic commit opportunities."""

    async def invoke(
        self, input_data: dict[str, Any], *, deps: dict | None = None
    ) -> dict[str, Any]:
        """Analyze current git changes for atomic commit opportunities."""
        # Get git status and diff
        status = await self._get_git_status()
        diff_stat = await self._get_diff_stat()

        # Parse changes into FileChange objects
        changes = self._parse_changes(status, diff_stat)

        # Group changes into logical units
        logical_changes = self._identify_logical_changes(changes)

        # Generate recommendations
        recommendations = self._generate_recommendations(logical_changes)

        return {
            "total_files": len(changes),
            "logical_changes": len(logical_changes),
            "changes": [self._logical_change_to_dict(lc) for lc in logical_changes],
            "recommendations": recommendations,
            "workflow_suggestion": self._suggest_workflow(logical_changes),
        }

    async def _get_git_status(self) -> str:
        """Get git status output."""
        result = await asyncio.create_subprocess_exec(
            "git",
            "status",
            "--porcelain",
            "-u",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, _ = await result.communicate()
        return stdout.decode()

    async def _get_diff_stat(self) -> str:
        """Get git diff statistics."""
        result = await asyncio.create_subprocess_exec(
            "git",
            "diff",
            "--cached",
            "--stat",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, _ = await result.communicate()
        return stdout.decode()

    def _parse_changes(self, status: str, diff_stat: str) -> list[FileChange]:
        """Parse git output into FileChange objects."""
        changes = []

        for line in status.strip().split("\n"):
            if not line:
                continue

            status_code = line[:2].strip()
            file_path = line[3:]

            # Map git status codes to readable status
            status_map = {
                "M": "Modified",
                "A": "Added",
                "D": "Deleted",
                "R": "Renamed",
                "??": "Untracked",
            }

            changes.append(
                FileChange(
                    path=Path(file_path),
                    status=status_map.get(status_code, status_code),
                )
            )

        return changes

    def _identify_logical_changes(
        self, changes: list[FileChange]
    ) -> list[LogicalChange]:
        """Group file changes into logical units using AI-inspired heuristics."""
        logical_changes = []
        processed = set()

        # Strategy 1: Group by test/implementation pairs
        for i, change in enumerate(changes):
            if i in processed:
                continue

            if change.is_test:
                # Find corresponding implementation
                impl_files = []
                test_files = [change]

                for j, other in enumerate(changes):
                    if j != i and j not in processed:
                        if self._is_related_implementation(change, other):
                            impl_files.append(other)
                            processed.add(j)

                if impl_files:
                    processed.add(i)
                    logical_changes.append(
                        LogicalChange(
                            files=impl_files + test_files,
                            suggested_type=CommitType.TEST
                            if not impl_files
                            else CommitType.FEAT,
                            suggested_scope=self._extract_scope(
                                impl_files + test_files
                            ),
                            suggested_description=self._generate_description(
                                impl_files + test_files
                            ),
                            reasoning="Test files grouped with their implementation",
                            complexity=self._assess_complexity(impl_files + test_files),
                        )
                    )

        # Strategy 2: Group by module/component
        module_groups = {}
        for i, change in enumerate(changes):
            if i in processed:
                continue

            module = change.module
            if module:
                if module not in module_groups:
                    module_groups[module] = []
                module_groups[module].append((i, change))

        for module, module_changes in module_groups.items():
            indices, files = zip(*module_changes, strict=False)
            for idx in indices:
                processed.add(idx)

            logical_changes.append(
                LogicalChange(
                    files=list(files),
                    suggested_type=self._infer_commit_type(files),
                    suggested_scope=module,
                    suggested_description=self._generate_description(files),
                    reasoning=f"Changes in same module: {module}",
                    complexity=self._assess_complexity(files),
                )
            )

        # Strategy 3: Group documentation changes
        doc_changes = []
        for i, change in enumerate(changes):
            if i not in processed and change.is_docs:
                doc_changes.append(change)
                processed.add(i)

        if doc_changes:
            logical_changes.append(
                LogicalChange(
                    files=doc_changes,
                    suggested_type=CommitType.DOCS,
                    suggested_scope=None,
                    suggested_description="update documentation",
                    reasoning="Documentation files grouped together",
                    complexity="simple",
                )
            )

        # Strategy 4: Remaining ungrouped files
        for i, change in enumerate(changes):
            if i not in processed:
                logical_changes.append(
                    LogicalChange(
                        files=[change],
                        suggested_type=self._infer_commit_type([change]),
                        suggested_scope=self._extract_scope([change]),
                        suggested_description=self._generate_description([change]),
                        reasoning="Standalone change",
                        complexity="simple",
                    )
                )

        # Identify dependencies
        self._identify_dependencies(logical_changes)

        return logical_changes

    def _is_related_implementation(
        self, test_file: FileChange, impl_file: FileChange
    ) -> bool:
        """Check if a test file is related to an implementation file."""
        test_name = test_file.path.stem.replace("test_", "").replace("_test", "")
        impl_name = impl_file.path.stem

        return (
            test_name in impl_name or impl_name in test_name
        ) and not impl_file.is_test

    def _extract_scope(self, files: list[FileChange]) -> str | None:
        """Extract a common scope from file changes."""
        modules = {f.module for f in files if f.module}
        if len(modules) == 1:
            return modules.pop()

        # Check for common path components
        if files:
            common_parts = set(files[0].path.parts)
            for f in files[1:]:
                common_parts &= set(f.path.parts)

            # Remove generic parts
            common_parts -= {"src", "tests", "docs", "."}
            if common_parts:
                return sorted(common_parts)[0]

        return None

    def _infer_commit_type(self, files: list[FileChange]) -> CommitType:
        """Infer commit type from file changes."""
        # All test files -> test commit
        if all(f.is_test for f in files):
            return CommitType.TEST

        # All doc files -> docs commit
        if all(f.is_docs for f in files):
            return CommitType.DOCS

        # New files -> likely a feature
        if any(f.status == "Added" for f in files):
            return CommitType.FEAT

        # Modified files -> could be fix or refactor
        # This would benefit from actual diff analysis
        return CommitType.FIX

    def _generate_description(self, files: list[FileChange]) -> str:
        """Generate a description based on file changes."""
        if len(files) == 1:
            action = {"Added": "add", "Modified": "update", "Deleted": "remove"}.get(
                files[0].status, "change"
            )

            return f"{action} {files[0].path.stem}"

        # Multiple files - find common action
        actions = {f.status for f in files}
        if len(actions) == 1:
            action = {"Added": "add", "Modified": "update", "Deleted": "remove"}.get(
                actions.pop(), "change"
            )

            if all(f.is_test for f in files):
                return f"{action} tests"
            elif all(f.is_docs for f in files):
                return f"{action} documentation"
            else:
                return f"{action} {len(files)} files"

        return "implement changes"

    def _assess_complexity(self, files: list[FileChange]) -> str:
        """Assess the complexity of a logical change."""
        if len(files) <= 2:
            return "simple"
        elif len(files) <= 5:
            return "medium"
        else:
            return "complex"

    def _identify_dependencies(self, logical_changes: list[LogicalChange]) -> None:
        """Identify dependencies between logical changes."""
        for i, change in enumerate(logical_changes):
            for j, other in enumerate(logical_changes):
                if i != j and self._depends_on(change, other):
                    change.dependencies.append(j)

    def _depends_on(self, change: LogicalChange, other: LogicalChange) -> bool:
        """Check if one change depends on another."""
        # Test changes depend on implementation changes
        if change.suggested_type == CommitType.TEST and other.suggested_type in [
            CommitType.FEAT,
            CommitType.FIX,
        ]:
            # Check if they share scope or files
            if change.suggested_scope == other.suggested_scope:
                return True

        # Documentation might depend on feature changes
        if (
            change.suggested_type == CommitType.DOCS
            and other.suggested_type == CommitType.FEAT
        ):
            return True

        return False

    def _generate_recommendations(
        self, logical_changes: list[LogicalChange]
    ) -> list[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Check for overly complex commits
        complex_changes = [lc for lc in logical_changes if lc.complexity == "complex"]
        if complex_changes:
            recommendations.append(
                f"⚠️  {len(complex_changes)} complex changes detected. Consider splitting further."
            )

        # Check for missing tests
        has_features = any(
            lc.suggested_type == CommitType.FEAT for lc in logical_changes
        )
        has_tests = any(lc.suggested_type == CommitType.TEST for lc in logical_changes)
        if has_features and not has_tests:
            recommendations.append(
                "💡 Feature changes detected without tests. Consider adding tests."
            )

        # Suggest commit order based on dependencies
        if any(lc.dependencies for lc in logical_changes):
            recommendations.append(
                "📋 Commit order matters due to dependencies. Follow the suggested workflow."
            )

        # Check for documentation updates
        has_api_changes = any(
            lc.suggested_type in [CommitType.FEAT, CommitType.FIX]
            and any("api" in str(f.path).lower() for f in lc.files)
            for lc in logical_changes
        )
        has_docs = any(lc.suggested_type == CommitType.DOCS for lc in logical_changes)
        if has_api_changes and not has_docs:
            recommendations.append(
                "📚 API changes detected. Don't forget to update documentation."
            )

        return recommendations

    def _suggest_workflow(self, logical_changes: list[LogicalChange]) -> list[str]:
        """Suggest a workflow for committing changes."""
        # Sort by dependencies
        sorted_changes = self._topological_sort(logical_changes)

        workflow = []
        for i, change in enumerate(sorted_changes):
            commit_msg = CommitMessage(
                type=change.suggested_type,
                scope=change.suggested_scope,
                description=change.suggested_description,
            )

            workflow.append(
                f"{i + 1}. {str(commit_msg)} ({len(change.files)} files, {change.complexity})"
            )

        return workflow

    def _topological_sort(
        self, logical_changes: list[LogicalChange]
    ) -> list[LogicalChange]:
        """Sort changes by dependencies."""
        # Simple topological sort
        sorted_changes = []
        remaining = list(range(len(logical_changes)))

        while remaining:
            # Find changes with no dependencies in remaining set
            ready = []
            for i in remaining:
                deps_in_remaining = [
                    d for d in logical_changes[i].dependencies if d in remaining
                ]
                if not deps_in_remaining:
                    ready.append(i)

            if not ready:
                # Circular dependency or error - just take first
                ready = [remaining[0]]

            for i in ready:
                sorted_changes.append(logical_changes[i])
                remaining.remove(i)

        return sorted_changes

    def _logical_change_to_dict(self, lc: LogicalChange) -> dict[str, Any]:
        """Convert LogicalChange to dictionary for JSON serialization."""
        return {
            "files": [str(f.path) for f in lc.files],
            "suggested_commit": str(
                CommitMessage(
                    type=lc.suggested_type,
                    scope=lc.suggested_scope,
                    description=lc.suggested_description,
                )
            ),
            "type": lc.suggested_type.value,
            "scope": lc.suggested_scope,
            "description": lc.suggested_description,
            "reasoning": lc.reasoning,
            "complexity": lc.complexity,
            "dependencies": lc.dependencies,
        }


class AtomicCommitSplitter(NanobrickBase[dict[str, Any], dict[str, Any], None]):
    """Splits mixed changes into atomic commits with interactive guidance."""

    async def invoke(
        self, input_data: dict[str, Any], *, deps: dict | None = None
    ) -> dict[str, Any]:
        """Guide through splitting changes into atomic commits."""
        # First analyze the changes
        analyzer = AtomicCommitAnalyzer()
        analysis = await analyzer.invoke({})

        if analysis["logical_changes"] <= 1:
            return {
                "status": "no_split_needed",
                "message": "Changes are already atomic!",
                "analysis": analysis,
            }

        # Generate split instructions
        instructions = self._generate_split_instructions(analysis)

        # Create staging scripts
        scripts = self._create_staging_scripts(analysis)

        return {
            "status": "split_recommended",
            "total_commits": analysis["logical_changes"],
            "instructions": instructions,
            "scripts": scripts,
            "analysis": analysis,
        }

    def _generate_split_instructions(
        self, analysis: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Generate step-by-step instructions for splitting."""
        instructions = []

        for i, change in enumerate(analysis["changes"]):
            instruction = {
                "step": i + 1,
                "commit_message": change["suggested_commit"],
                "files_to_stage": change["files"],
                "git_commands": self._generate_git_commands(change["files"]),
                "reasoning": change["reasoning"],
                "complexity": change["complexity"],
            }

            if change["dependencies"]:
                instruction["note"] = (
                    f"Depends on commits: {', '.join(str(d + 1) for d in change['dependencies'])}"
                )

            instructions.append(instruction)

        return instructions

    def _generate_git_commands(self, files: list[str]) -> list[str]:
        """Generate git commands for staging specific files."""
        commands = []

        # Reset any staged changes first
        commands.append("git reset")

        # Stage the specific files
        for file in files:
            commands.append(f"git add {file}")

        # Show what will be committed
        commands.append("git status --short")

        return commands

    def _create_staging_scripts(self, analysis: dict[str, Any]) -> dict[str, str]:
        """Create executable scripts for each atomic commit."""
        scripts = {}

        for i, change in enumerate(analysis["changes"]):
            script_name = f"commit_{i + 1}_{change['type']}.sh"

            script_content = f"""#!/bin/bash
# Atomic Commit {i + 1}: {change["suggested_commit"]}
# Reasoning: {change["reasoning"]}

echo "🎯 Staging files for: {change["suggested_commit"]}"
echo ""

# Reset any existing staged changes
git reset > /dev/null 2>&1

# Stage specific files
"""

            for file in change["files"]:
                script_content += f"git add {file}\n"

            script_content += f"""
# Show staged changes
echo "📋 Staged changes:"
git diff --cached --stat
echo ""

# Commit with message
read -p "Proceed with commit? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git commit -m "{change["suggested_commit"]}"
    echo "✅ Commit created!"
else
    echo "❌ Commit cancelled. Changes remain staged."
fi
"""

            scripts[script_name] = script_content

        return scripts


class AtomicCommitValidator(NanobrickBase[dict[str, Any], dict[str, Any], None]):
    """Validates commits for atomic principles and conventional format."""

    CONVENTIONAL_PATTERN = re.compile(
        r"^(?P<type>feat|fix|docs|refactor|test|chore|perf|style|ci|build)"
        r"(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?:\s*(?P<description>.+)$"
    )

    async def invoke(
        self, input_data: dict[str, Any], *, deps: dict | None = None
    ) -> dict[str, Any]:
        """Validate commits for atomic principles."""
        commit_range = input_data.get("range", "HEAD~5..HEAD")

        # Get commit information
        commits = await self._get_commits(commit_range)

        # Validate each commit
        validations = []
        for commit in commits:
            validation = await self._validate_commit(commit)
            validations.append(validation)

        # Calculate overall score
        total_score = sum(v["score"] for v in validations)
        average_score = total_score / len(validations) if validations else 0

        return {
            "commit_count": len(commits),
            "average_score": average_score,
            "passed": average_score >= 90,
            "validations": validations,
            "summary": self._generate_summary(validations),
        }

    async def _get_commits(self, commit_range: str) -> list[dict[str, Any]]:
        """Get commit information for the specified range."""
        # Get commit hashes
        result = await asyncio.create_subprocess_exec(
            "git",
            "log",
            commit_range,
            "--format=%H",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, _ = await result.communicate()
        hashes = stdout.decode().strip().split("\n")

        commits = []
        for hash in hashes:
            if not hash:
                continue

            # Get commit details
            commit_info = await self._get_commit_info(hash)
            commits.append(commit_info)

        return commits

    async def _get_commit_info(self, commit_hash: str) -> dict[str, Any]:
        """Get detailed information about a commit."""
        # Get commit message
        result = await asyncio.create_subprocess_exec(
            "git",
            "show",
            "-s",
            "--format=%s%n%n%b",
            commit_hash,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, _ = await result.communicate()
        message = stdout.decode().strip()

        # Get file changes
        result = await asyncio.create_subprocess_exec(
            "git",
            "show",
            "--stat",
            "--format=",
            commit_hash,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, _ = await result.communicate()
        stats = stdout.decode().strip()

        # Parse file count and line changes
        file_count = 0
        insertions = 0
        deletions = 0

        for line in stats.split("\n"):
            if "|" in line:
                file_count += 1
            elif "insertion" in line or "deletion" in line:
                match = re.search(r"(\d+) insertion", line)
                if match:
                    insertions = int(match.group(1))
                match = re.search(r"(\d+) deletion", line)
                if match:
                    deletions = int(match.group(1))

        return {
            "hash": commit_hash,
            "message": message,
            "subject": message.split("\n")[0],
            "file_count": file_count,
            "insertions": insertions,
            "deletions": deletions,
        }

    async def _validate_commit(self, commit: dict[str, Any]) -> dict[str, Any]:
        """Validate a single commit."""
        issues = []
        score = 100

        # Check conventional format
        match = self.CONVENTIONAL_PATTERN.match(commit["subject"])
        if not match:
            issues.append("Does not follow conventional commit format")
            score -= 20
        else:
            commit_type = match.group("type")
            scope = match.group("scope")
            description = match.group("description")

            # Validate description length
            if len(description) > 72:
                issues.append(
                    f"Description too long ({len(description)} chars, max 72)"
                )
                score -= 10

            # Check for vague descriptions
            vague_words = ["update", "change", "modify", "fix stuff", "various"]
            if any(word in description.lower() for word in vague_words):
                issues.append("Description is too vague")
                score -= 15

        # Check atomicity - file count heuristic
        if commit["file_count"] > 10:
            issues.append(f"Too many files changed ({commit['file_count']})")
            score -= 20
        elif commit["file_count"] > 5:
            issues.append(f"Consider splitting: {commit['file_count']} files changed")
            score -= 10

        # Check atomicity - line count heuristic
        total_lines = commit["insertions"] + commit["deletions"]
        if total_lines > 500:
            issues.append(f"Too many line changes ({total_lines})")
            score -= 20
        elif total_lines > 200:
            issues.append(f"Large change: {total_lines} lines")
            score -= 10

        # Check for mixed concerns
        if commit["message"].count("\n\n") > 2:
            issues.append("Complex commit body suggests multiple concerns")
            score -= 10

        # Look for "and" in subject
        if " and " in commit["subject"].lower():
            issues.append("Subject contains 'and' - might be non-atomic")
            score -= 15

        return {
            "hash": commit["hash"],
            "subject": commit["subject"],
            "score": max(0, score),
            "passed": score >= 80,
            "issues": issues,
            "stats": {
                "files": commit["file_count"],
                "insertions": commit["insertions"],
                "deletions": commit["deletions"],
            },
        }

    def _generate_summary(self, validations: list[dict[str, Any]]) -> dict[str, Any]:
        """Generate a summary of validation results."""
        passed = sum(1 for v in validations if v["passed"])
        failed = len(validations) - passed

        # Collect all issues
        all_issues = []
        for v in validations:
            all_issues.extend(v["issues"])

        # Count issue frequencies
        issue_counts = {}
        for issue in all_issues:
            # Normalize similar issues
            normalized = issue.split("(")[0].strip()
            issue_counts[normalized] = issue_counts.get(normalized, 0) + 1

        # Sort by frequency
        common_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[
            :5
        ]

        return {
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{(passed / len(validations) * 100):.1f}%"
            if validations
            else "0%",
            "common_issues": [
                {"issue": issue, "count": count} for issue, count in common_issues
            ],
        }


class AtomicCommitHelper(NanobrickBase[dict[str, Any], dict[str, Any], None]):
    """Main atomic commit helper that orchestrates analysis, splitting, and validation."""

    def __init__(self):
        super().__init__()
        self.analyzer = AtomicCommitAnalyzer()
        self.splitter = AtomicCommitSplitter()
        self.validator = AtomicCommitValidator()

    async def invoke(
        self, input_data: dict[str, Any], *, deps: dict | None = None
    ) -> dict[str, Any]:
        """Main entry point for atomic commit operations."""
        command = input_data.get("command", "analyze")

        if command == "analyze":
            return await self.analyzer.invoke(input_data, deps=deps)
        elif command == "split":
            return await self.splitter.invoke(input_data, deps=deps)
        elif command == "validate":
            return await self.validator.invoke(input_data, deps=deps)
        elif command == "suggest":
            return await self._suggest_commit_message(input_data)
        elif command == "learn":
            return await self._learn_from_history(input_data)
        else:
            return {
                "error": f"Unknown command: {command}",
                "available_commands": [
                    "analyze",
                    "split",
                    "validate",
                    "suggest",
                    "learn",
                ],
            }

    async def _suggest_commit_message(
        self, input_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Suggest a commit message for staged changes."""
        # Get staged changes
        result = await asyncio.create_subprocess_exec(
            "git",
            "diff",
            "--cached",
            "--name-status",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, _ = await result.communicate()

        if not stdout:
            return {
                "error": "No staged changes found",
                "suggestion": "Stage changes with 'git add' first",
            }

        # Parse staged files
        staged_files = []
        for line in stdout.decode().strip().split("\n"):
            if line:
                parts = line.split("\t")
                if len(parts) >= 2:
                    status = parts[0]
                    path = parts[1]
                    staged_files.append(FileChange(path=Path(path), status=status))

        # Analyze the changes
        suggested_type = self._infer_commit_type_for_files(staged_files)
        suggested_scope = self._extract_scope_for_files(staged_files)
        suggested_description = self._generate_description_for_files(staged_files)

        # Build commit message
        commit_msg = CommitMessage(
            type=suggested_type,
            scope=suggested_scope,
            description=suggested_description,
        )

        # Add context-aware suggestions
        alternatives = self._generate_alternatives(staged_files, suggested_type)

        return {
            "suggested_message": str(commit_msg),
            "components": {
                "type": suggested_type.value,
                "scope": suggested_scope,
                "description": suggested_description,
            },
            "alternatives": alternatives,
            "tips": self._generate_commit_tips(staged_files),
        }

    def _infer_commit_type_for_files(self, files: list[FileChange]) -> CommitType:
        """Infer commit type from staged files."""
        # Check for specific patterns
        if all(f.path.suffix in {".md", ".qmd", ".rst", ".txt"} for f in files):
            return CommitType.DOCS

        if all("test" in str(f.path) for f in files):
            return CommitType.TEST

        if any(f.status == "A" for f in files):  # Added files
            return CommitType.FEAT

        if any(
            f.path.name in {"package.json", "pyproject.toml", "requirements.txt"}
            for f in files
        ):
            return CommitType.BUILD

        if any(
            f.path.name in {".github", ".gitlab-ci.yml", "Jenkinsfile"} for f in files
        ):
            return CommitType.CI

        # Default to fix for modifications
        return CommitType.FIX

    def _extract_scope_for_files(self, files: list[FileChange]) -> str | None:
        """Extract scope from staged files."""
        # Look for common directory
        if files:
            parts = set()
            for f in files:
                if len(f.path.parts) > 1:
                    # Skip common prefixes like src/, tests/
                    for part in f.path.parts[1:-1]:
                        if part not in {"src", "tests", "docs"}:
                            parts.add(part)

            if len(parts) == 1:
                return parts.pop()

        return None

    def _generate_description_for_files(self, files: list[FileChange]) -> str:
        """Generate description from staged files."""
        if len(files) == 1:
            file = files[0]
            action = {"A": "add", "M": "update", "D": "remove", "R": "rename"}.get(
                file.status, "change"
            )

            # Use filename without extension for description
            name = file.path.stem.replace("_", " ").replace("-", " ")
            return f"{action} {name}"

        # Multiple files - be more generic
        actions = {f.status for f in files}
        if len(actions) == 1:
            action = {"A": "add", "M": "update", "D": "remove"}.get(
                actions.pop(), "change"
            )

            # Find common theme
            if all("test" in str(f.path) for f in files):
                return f"{action} tests"
            elif all(f.path.suffix in {".md", ".qmd"} for f in files):
                return f"{action} documentation"
            else:
                return f"{action} {len(files)} files"

        return "update multiple files"

    def _generate_alternatives(
        self, files: list[FileChange], suggested_type: CommitType
    ) -> list[str]:
        """Generate alternative commit messages."""
        alternatives = []

        # If suggested fix, maybe it's a refactor
        if suggested_type == CommitType.FIX:
            scope = self._extract_scope_for_files(files)
            desc = "improve code structure"
            msg = f"refactor{f'({scope})' if scope else ''}: {desc}"
            alternatives.append(msg)

        # If suggested feat, maybe it's an enhancement
        if suggested_type == CommitType.FEAT:
            scope = self._extract_scope_for_files(files)
            desc = "enhance existing functionality"
            msg = f"feat{f'({scope})' if scope else ''}: {desc}"
            alternatives.append(msg)

        return alternatives

    def _generate_commit_tips(self, files: list[FileChange]) -> list[str]:
        """Generate contextual tips for the commit."""
        tips = []

        # Check file count
        if len(files) > 5:
            tips.append("Consider splitting this into multiple commits")

        # Check for test files
        has_tests = any("test" in str(f.path) for f in files)
        has_implementation = any("test" not in str(f.path) for f in files)

        if has_implementation and not has_tests:
            tips.append("Don't forget to add tests in a follow-up commit")

        if has_tests and has_implementation:
            tips.append("Good practice: tests and implementation together")

        # Check for documentation
        has_docs = any(f.path.suffix in {".md", ".qmd"} for f in files)
        if not has_docs and len(files) > 3:
            tips.append("Consider updating documentation if needed")

        return tips

    async def _learn_from_history(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Learn from project's commit history to improve suggestions."""
        # Get recent good commits
        result = await asyncio.create_subprocess_exec(
            "git",
            "log",
            "--grep",
            "^(feat|fix|docs|refactor|test|chore)",
            "-E",
            "--format=%s",
            "-20",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, _ = await result.communicate()

        good_examples = []
        patterns = {}

        for line in stdout.decode().strip().split("\n"):
            if line and AtomicCommitValidator.CONVENTIONAL_PATTERN.match(line):
                good_examples.append(line)

                # Extract patterns
                match = AtomicCommitValidator.CONVENTIONAL_PATTERN.match(line)
                if match:
                    commit_type = match.group("type")
                    scope = match.group("scope")

                    if commit_type not in patterns:
                        patterns[commit_type] = {"scopes": set(), "count": 0}

                    patterns[commit_type]["count"] += 1
                    if scope:
                        patterns[commit_type]["scopes"].add(scope)

        # Convert sets to lists for JSON serialization
        for commit_type in patterns:
            patterns[commit_type]["scopes"] = list(patterns[commit_type]["scopes"])

        return {
            "learned_patterns": patterns,
            "good_examples": good_examples[:10],
            "insights": self._generate_insights(patterns),
            "recommendations": self._generate_learning_recommendations(patterns),
        }

    def _generate_insights(self, patterns: dict[str, Any]) -> list[str]:
        """Generate insights from learned patterns."""
        insights = []

        # Most common commit type
        if patterns:
            most_common = max(patterns.items(), key=lambda x: x[1]["count"])
            insights.append(
                f"Most common commit type: {most_common[0]} ({most_common[1]['count']} commits)"
            )

        # Scope usage
        scoped_types = [t for t, p in patterns.items() if p["scopes"]]
        if scoped_types:
            insights.append(f"Commit types using scopes: {', '.join(scoped_types)}")

        # Find common scopes across types
        all_scopes = set()
        for pattern in patterns.values():
            all_scopes.update(pattern["scopes"])

        if all_scopes:
            insights.append(f"Common scopes: {', '.join(sorted(all_scopes)[:5])}")

        return insights

    def _generate_learning_recommendations(self, patterns: dict[str, Any]) -> list[str]:
        """Generate recommendations based on learned patterns."""
        recommendations = []

        # Check for underused commit types
        standard_types = {"feat", "fix", "docs", "refactor", "test", "chore"}
        used_types = set(patterns.keys())
        unused_types = standard_types - used_types

        if unused_types:
            recommendations.append(
                f"Consider using these commit types: {', '.join(unused_types)}"
            )

        # Recommend consistent scoping
        scoped_percentage = (
            sum(1 for p in patterns.values() if p["scopes"]) / len(patterns) * 100
            if patterns
            else 0
        )
        if scoped_percentage < 50:
            recommendations.append(
                "Consider using scopes more consistently for better organization"
            )

        return recommendations


# Skill implementation
@register_skill("atomic_commits")
class AtomicCommitsSkill(Skill[T_in, T_out, T_deps]):
    """Skill that provides atomic commit functionality to nanobricks.

    Config options:
        - auto_validate: Whether to validate commits automatically (default: False)
        - max_files_per_commit: Maximum files per atomic commit (default: 10)
        - mcp_enabled: Enable MCP tool integration (default: True)
    """

    def _create_enhanced_brick(self, brick):
        """Create an enhanced brick with atomic commit capabilities."""
        auto_validate = self.config.get("auto_validate", False)
        max_files = self.config.get("max_files_per_commit", 10)
        mcp_enabled = self.config.get("mcp_enabled", True)

        class AtomicCommitEnhanced(NanobrickEnhanced[T_in, T_out, T_deps]):
            """Enhanced brick with atomic commit capabilities."""

            def __init__(self):
                super().__init__(brick, self._skill)
                self.helper = AtomicCommitHelper()

                # Add atomic commit methods
                self.analyze_commits = self.helper.analyzer.invoke
                self.split_commits = self.helper.splitter.invoke
                self.validate_commits = self.helper.validator.invoke
                self.suggest_commit = lambda: self.helper.invoke({"command": "suggest"})
                self.learn_from_commits = lambda: self.helper.invoke(
                    {"command": "learn"}
                )

            async def invoke(self, input_data: T_in, *, deps: T_deps = None) -> T_out:
                """Invoke with optional commit validation."""
                # Run the original brick
                result = await self._wrapped.invoke(input_data, deps=deps)

                # Auto-validate if enabled
                if auto_validate:
                    validation = await self.helper.invoke(
                        {"command": "validate", "range": "HEAD~1..HEAD"}
                    )
                    if not validation.get("passed", True):
                        import warnings

                        warnings.warn(
                            f"Last commit failed validation: {validation.get('summary', 'Unknown error')}",
                            UserWarning,
                        )

                return result

            async def handle_mcp_request(
                self, tool_name: str, arguments: dict[str, Any]
            ) -> dict[str, Any]:
                """Handle MCP tool requests."""
                if mcp_enabled and tool_name == "atomic-commit-helper":
                    return await self.helper.invoke(arguments)
                else:
                    return {"error": f"Unknown tool: {tool_name}"}

        # Set skill reference
        AtomicCommitEnhanced._skill = self

        return AtomicCommitEnhanced()


# Example usage and integration
if __name__ == "__main__":
    import sys

    async def main():
        helper = AtomicCommitHelper()

        # Parse command line arguments
        if len(sys.argv) < 2:
            print(
                "Usage: python -m nanobricks.skills.atomic_commits <command> [options]"
            )
            print("Commands: analyze, validate, split, suggest, learn")
            return

        command = sys.argv[1]

        # Build request based on command
        request = {"command": command}

        # Handle command-specific options
        if command == "validate" and len(sys.argv) > 2:
            # Look for --range option
            for i, arg in enumerate(sys.argv[2:], 2):
                if arg == "--range" and i < len(sys.argv) - 1:
                    request["range"] = sys.argv[i + 1]

        try:
            result = await helper.invoke(request)

            # Format output based on command
            if command == "analyze":
                print(f"📊 Found {result.get('logical_changes', 0)} logical changes")
                print(f"📁 Total files: {result.get('total_files', 0)}")
                print("\n🔍 Logical Changes:")
                for i, change in enumerate(result.get("changes", []), 1):
                    print(f"\n{i}. {change.get('suggested_commit', 'No message')}")
                    print(f"   Files: {', '.join(change.get('files', []))}")
                    if change.get("complexity"):
                        print(f"   Complexity: {change['complexity']}")
                print("\n💡 Recommendations:")
                for rec in result.get("recommendations", []):
                    print(f"   - {rec}")

            elif command == "validate":
                # Check for different possible field names
                score = result.get("average_score", result.get("score", 0))
                total = result.get("commit_count", result.get("total_commits", 0))

                print(f"✅ Validation {'passed' if result.get('passed') else 'failed'}")
                print(f"📊 Score: {score:.1f}%")
                print(f"📈 Total commits: {total}")

                # Check for validations array
                if result.get("validations"):
                    issues = []
                    good = []
                    for v in result["validations"]:
                        if v.get("issues"):
                            issues.extend(
                                [
                                    f"{v['commit_hash'][:7]}: {issue}"
                                    for issue in v["issues"]
                                ]
                            )
                        if v.get("score", 0) >= 90:
                            good.append(f"{v['commit_hash'][:7]}: {v['message']}")

                    if issues:
                        print(f"\n❌ Issues found ({len(issues)}):")
                        for issue in issues[:5]:
                            print(f"   - {issue}")
                        if len(issues) > 5:
                            print(f"   ... and {len(issues) - 5} more")

                    if good:
                        print(f"\n✅ Good commits ({len(good)}):")
                        for commit in good[:3]:
                            print(f"   - {commit}")

                # Also check for summary
                if result.get("summary"):
                    print(f"\n📝 Summary: {result['summary']}")

            elif command == "suggest":
                if result.get("suggestion"):
                    print(f"💡 Suggested commit message:\n   {result['suggestion']}")
                else:
                    print("❌ No staged changes found")

            else:
                # For other commands, output as JSON
                print(json.dumps(result, indent=2))

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            sys.exit(1)

    asyncio.run(main())
