"""
Unit tests for the atomic commits skill.
"""

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nanobricks.skills.atomic_commits import (
    AtomicCommitAnalyzer,
    AtomicCommitHelper,
    AtomicCommitSplitter,
    AtomicCommitValidator,
    CommitMessage,
    CommitType,
    FileChange,
    LogicalChange,
)


class TestCommitMessage:
    """Test CommitMessage class."""
    
    def test_simple_message(self):
        """Test simple commit message formatting."""
        msg = CommitMessage(
            type=CommitType.FEAT,
            scope="auth",
            description="add JWT validation"
        )
        assert str(msg) == "feat(auth): add JWT validation"
    
    def test_message_without_scope(self):
        """Test commit message without scope."""
        msg = CommitMessage(
            type=CommitType.FIX,
            scope=None,
            description="handle null values"
        )
        assert str(msg) == "fix: handle null values"
    
    def test_message_with_body(self):
        """Test commit message with body."""
        msg = CommitMessage(
            type=CommitType.FEAT,
            scope="api",
            description="add rate limiting",
            body="Implements token bucket algorithm for API endpoints"
        )
        expected = "feat(api): add rate limiting\n\nImplements token bucket algorithm for API endpoints"
        assert str(msg) == expected
    
    def test_breaking_change(self):
        """Test breaking change notation."""
        msg = CommitMessage(
            type=CommitType.FEAT,
            scope="api",
            description="change auth method",
            breaking=True
        )
        assert str(msg) == "feat(api)!: change auth method"


class TestFileChange:
    """Test FileChange class."""
    
    def test_is_test(self):
        """Test identifying test files."""
        assert FileChange(Path("test_module.py"), "Modified").is_test
        assert FileChange(Path("tests/unit/test_api.py"), "Added").is_test
        assert not FileChange(Path("src/module.py"), "Modified").is_test
    
    def test_is_docs(self):
        """Test identifying documentation files."""
        assert FileChange(Path("README.md"), "Modified").is_docs
        assert FileChange(Path("docs/guide.qmd"), "Added").is_docs
        assert not FileChange(Path("src/module.py"), "Modified").is_docs
    
    def test_module_extraction(self):
        """Test module extraction from path."""
        fc = FileChange(Path("src/nanobricks/auth/validator.py"), "Modified")
        assert fc.module == "auth"
        
        fc = FileChange(Path("auth/validator.py"), "Modified")
        assert fc.module is None


class TestAtomicCommitAnalyzer:
    """Test AtomicCommitAnalyzer class."""
    
    @pytest.mark.asyncio
    async def test_analyze_no_changes(self):
        """Test analyzing when no changes exist."""
        analyzer = AtomicCommitAnalyzer()
        
        with patch.object(analyzer, '_get_git_status', return_value=""):
            with patch.object(analyzer, '_get_diff_stat', return_value=""):
                result = await analyzer.invoke({})
                
                assert result["total_files"] == 0
                assert result["logical_changes"] == 0
                assert result["changes"] == []
    
    @pytest.mark.asyncio
    async def test_analyze_single_file(self):
        """Test analyzing single file change."""
        analyzer = AtomicCommitAnalyzer()
        
        git_status = "M  src/module.py"
        diff_stat = " src/module.py | 10 +++++++---"
        
        with patch.object(analyzer, '_get_git_status', return_value=git_status):
            with patch.object(analyzer, '_get_diff_stat', return_value=diff_stat):
                result = await analyzer.invoke({})
                
                assert result["total_files"] == 1
                assert result["logical_changes"] == 1
                assert len(result["changes"]) == 1
                
                change = result["changes"][0]
                assert change["files"] == ["src/module.py"]
                assert change["type"] == "fix"
    
    @pytest.mark.asyncio
    async def test_analyze_test_implementation_pair(self):
        """Test analyzing test and implementation files together."""
        analyzer = AtomicCommitAnalyzer()
        
        git_status = """M  src/auth/validator.py
A  tests/test_validator.py"""
        
        with patch.object(analyzer, '_get_git_status', return_value=git_status):
            with patch.object(analyzer, '_get_diff_stat', return_value=""):
                result = await analyzer.invoke({})
                
                # Should group test with implementation
                assert result["logical_changes"] == 1
                change = result["changes"][0]
                assert len(change["files"]) == 2
                assert change["reasoning"] == "Test files grouped with their implementation"
    
    def test_identify_logical_changes_by_module(self):
        """Test grouping changes by module."""
        analyzer = AtomicCommitAnalyzer()
        
        changes = [
            FileChange(Path("src/nanobricks/auth/models.py"), "Modified"),
            FileChange(Path("src/nanobricks/auth/validator.py"), "Added"),
            FileChange(Path("src/nanobricks/api/endpoints.py"), "Modified"),
        ]
        
        logical_changes = analyzer._identify_logical_changes(changes)
        
        # Should create 2 groups: auth and api
        assert len(logical_changes) == 2
        
        # Find auth group
        auth_group = next(lc for lc in logical_changes if lc.suggested_scope == "auth")
        assert len(auth_group.files) == 2
        
        # Find api group
        api_group = next(lc for lc in logical_changes if lc.suggested_scope == "api")
        assert len(api_group.files) == 1
    
    def test_infer_commit_type(self):
        """Test commit type inference."""
        analyzer = AtomicCommitAnalyzer()
        
        # All test files
        test_files = [
            FileChange(Path("tests/test_module.py"), "Added"),
            FileChange(Path("tests/test_api.py"), "Modified"),
        ]
        assert analyzer._infer_commit_type(test_files) == CommitType.TEST
        
        # All doc files
        doc_files = [
            FileChange(Path("README.md"), "Modified"),
            FileChange(Path("docs/guide.md"), "Added"),
        ]
        assert analyzer._infer_commit_type(doc_files) == CommitType.DOCS
        
        # New files indicate feature
        new_files = [
            FileChange(Path("src/feature.py"), "Added"),
        ]
        assert analyzer._infer_commit_type(new_files) == CommitType.FEAT
        
        # Modified files default to fix
        modified_files = [
            FileChange(Path("src/module.py"), "Modified"),
        ]
        assert analyzer._infer_commit_type(modified_files) == CommitType.FIX


class TestAtomicCommitSplitter:
    """Test AtomicCommitSplitter class."""
    
    @pytest.mark.asyncio
    async def test_no_split_needed(self):
        """Test when changes are already atomic."""
        splitter = AtomicCommitSplitter()
        
        # Mock analyzer to return single logical change
        with patch('nanobricks.skills.atomic_commits.AtomicCommitAnalyzer.invoke') as mock_analyze:
            mock_analyze.return_value = {
                "logical_changes": 1,
                "changes": [{"files": ["src/module.py"]}]
            }
            
            result = await splitter.invoke({})
            
            assert result["status"] == "no_split_needed"
            assert "already atomic" in result["message"]
    
    @pytest.mark.asyncio
    async def test_split_recommended(self):
        """Test when splitting is recommended."""
        splitter = AtomicCommitSplitter()
        
        # Mock analyzer to return multiple logical changes
        with patch('nanobricks.skills.atomic_commits.AtomicCommitAnalyzer.invoke') as mock_analyze:
            mock_analyze.return_value = {
                "logical_changes": 3,
                "changes": [
                    {
                        "files": ["src/auth.py"],
                        "suggested_commit": "feat(auth): add validation",
                        "type": "feat",
                        "reasoning": "New feature",
                        "complexity": "simple",
                        "dependencies": []
                    },
                    {
                        "files": ["tests/test_auth.py"],
                        "suggested_commit": "test(auth): add tests",
                        "type": "test",
                        "reasoning": "Test files",
                        "complexity": "simple",
                        "dependencies": [0]
                    },
                    {
                        "files": ["docs/auth.md"],
                        "suggested_commit": "docs(auth): update guide",
                        "type": "docs",
                        "reasoning": "Documentation",
                        "complexity": "simple",
                        "dependencies": []
                    }
                ]
            }
            
            result = await splitter.invoke({})
            
            assert result["status"] == "split_recommended"
            assert result["total_commits"] == 3
            assert len(result["instructions"]) == 3
            assert len(result["scripts"]) == 3
    
    def test_generate_git_commands(self):
        """Test git command generation."""
        splitter = AtomicCommitSplitter()
        
        commands = splitter._generate_git_commands(["src/module.py", "tests/test_module.py"])
        
        assert "git reset" in commands
        assert "git add src/module.py" in commands
        assert "git add tests/test_module.py" in commands
        assert "git status --short" in commands


class TestAtomicCommitValidator:
    """Test AtomicCommitValidator class."""
    
    @pytest.mark.asyncio
    async def test_validate_conventional_format(self):
        """Test validation of conventional commit format."""
        validator = AtomicCommitValidator()
        
        # Mock commit data
        with patch.object(validator, '_get_commits') as mock_commits:
            mock_commits.return_value = [
                {
                    "hash": "abc123",
                    "message": "feat(auth): add JWT validation",
                    "subject": "feat(auth): add JWT validation",
                    "file_count": 2,
                    "insertions": 50,
                    "deletions": 10
                },
                {
                    "hash": "def456",
                    "message": "update stuff",
                    "subject": "update stuff",
                    "file_count": 15,
                    "insertions": 500,
                    "deletions": 200
                }
            ]
            
            result = await validator.invoke({"range": "HEAD~2..HEAD"})
            
            assert result["commit_count"] == 2
            assert result["passed"] is False
            
            validations = result["validations"]
            assert validations[0]["passed"] is True
            assert validations[0]["score"] >= 80
            
            assert validations[1]["passed"] is False
            assert "conventional commit format" in str(validations[1]["issues"])
    
    def test_conventional_pattern(self):
        """Test conventional commit pattern matching."""
        validator = AtomicCommitValidator()
        
        # Valid patterns
        assert validator.CONVENTIONAL_PATTERN.match("feat: add feature")
        assert validator.CONVENTIONAL_PATTERN.match("fix(auth): resolve bug")
        assert validator.CONVENTIONAL_PATTERN.match("docs(api): update guide")
        assert validator.CONVENTIONAL_PATTERN.match("feat!: breaking change")
        
        # Invalid patterns
        assert not validator.CONVENTIONAL_PATTERN.match("update stuff")
        assert not validator.CONVENTIONAL_PATTERN.match("Fix: wrong case")
        assert not validator.CONVENTIONAL_PATTERN.match("feat add feature")


class TestAtomicCommitHelper:
    """Test AtomicCommitHelper class."""
    
    @pytest.mark.asyncio
    async def test_analyze_command(self):
        """Test analyze command."""
        helper = AtomicCommitHelper()
        
        with patch.object(helper.analyzer, 'invoke') as mock_analyze:
            mock_analyze.return_value = {"result": "analysis"}
            
            result = await helper.invoke({"command": "analyze"})
            
            assert result == {"result": "analysis"}
            mock_analyze.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_unknown_command(self):
        """Test unknown command handling."""
        helper = AtomicCommitHelper()
        
        result = await helper.invoke({"command": "unknown"})
        
        assert "error" in result
        assert "Unknown command" in result["error"]
        assert "available_commands" in result
    
    @pytest.mark.asyncio
    async def test_suggest_commit_message(self):
        """Test commit message suggestion."""
        helper = AtomicCommitHelper()
        
        # Mock git command output
        with patch('asyncio.create_subprocess_exec') as mock_exec:
            # Mock process
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (
                b"A\tsrc/feature.py\nM\ttests/test_feature.py",
                b""
            )
            mock_exec.return_value = mock_process
            
            result = await helper.invoke({"command": "suggest"})
            
            assert "suggested_message" in result
            assert "components" in result
            assert "alternatives" in result
            assert "tips" in result
    
    @pytest.mark.asyncio
    async def test_learn_from_history(self):
        """Test learning from commit history."""
        helper = AtomicCommitHelper()
        
        # Mock git log output
        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (
                b"feat(auth): add validation\nfix(api): handle errors\nfeat(auth): add JWT support",
                b""
            )
            mock_exec.return_value = mock_process
            
            result = await helper.invoke({"command": "learn"})
            
            assert "learned_patterns" in result
            assert "good_examples" in result
            assert "insights" in result
            assert "recommendations" in result


class TestAtomicCommitsSkillIntegration:
    """Test atomic commits skill integration."""
    
    @pytest.mark.asyncio
    async def test_skill_enhancement(self):
        """Test enhancing a brick with atomic commits skill."""
        from nanobricks.skill import with_skill
        from nanobricks.protocol import NanobrickBase
        
        # Create a simple brick
        class SimpleBrick(NanobrickBase[Dict, Dict, None]):
            async def invoke(self, input_data: Dict, *, deps=None) -> Dict:
                return {"processed": input_data}
        
        # Enhance with atomic commits skill
        brick = SimpleBrick()
        enhanced = with_skill(brick, "atomic_commits", auto_validate=False)
        
        # Check that methods were added
        assert hasattr(enhanced, 'analyze_commits')
        assert hasattr(enhanced, 'split_commits')
        assert hasattr(enhanced, 'validate_commits')
        assert hasattr(enhanced, 'suggest_commit')
        assert hasattr(enhanced, 'learn_from_commits')
        
        # Test basic invocation still works
        result = await enhanced.invoke({"test": "data"})
        assert result == {"processed": {"test": "data"}}


@pytest.mark.integration
class TestAtomicCommitsIntegration:
    """Integration tests with actual git repository."""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self, tmp_path):
        """Test full atomic commit workflow."""
        # Create temporary git repository
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        
        # Initialize git repo
        import subprocess
        subprocess.run(["git", "init"], cwd=repo_path, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path)
        
        # Create some files
        (repo_path / "feature.py").write_text("def feature(): pass")
        (repo_path / "test_feature.py").write_text("def test_feature(): pass")
        
        # Stage files
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
        
        # Use atomic commit helper
        with patch('os.getcwd', return_value=str(repo_path)):
            helper = AtomicCommitHelper()
            
            # Analyze changes
            analysis = await helper.invoke({"command": "analyze"})
            assert analysis["total_files"] == 2
            
            # Get commit suggestion
            suggestion = await helper.invoke({"command": "suggest"})
            assert "suggested_message" in suggestion
            
            # Make commit
            subprocess.run(
                ["git", "commit", "-m", "feat: add feature with tests"],
                cwd=repo_path,
                check=True
            )
            
            # Validate commit
            validation = await helper.invoke({
                "command": "validate",
                "range": "HEAD~1..HEAD"
            })
            assert validation["passed"] is True