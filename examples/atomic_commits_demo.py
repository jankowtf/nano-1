#!/usr/bin/env python
"""
Example demonstrating atomic commits as nanobricks.

This shows how the atomic commits feature is implemented using
the nanobricks framework itself - showcasing dogfooding and
the power of composition.
"""

import asyncio
from typing import Dict

from nanobricks.protocol import NanobrickBase
from nanobricks.skill import with_skill
from nanobricks.skills.atomic_commits import (
    AtomicCommitAnalyzer,
    AtomicCommitHelper,
    AtomicCommitSplitter,
    AtomicCommitValidator,
)


async def demo_atomic_commit_analyzer():
    """Demonstrate analyzing git changes for atomic commit opportunities."""
    print("=== Atomic Commit Analyzer Demo ===\n")
    
    analyzer = AtomicCommitAnalyzer()
    result = await analyzer.invoke({})
    
    print(f"Total files changed: {result['total_files']}")
    print(f"Logical changes identified: {result['logical_changes']}")
    
    for i, change in enumerate(result['changes'], 1):
        print(f"\n{i}. {change['suggested_commit']}")
        print(f"   Files: {', '.join(change['files'][:3])}")
        if len(change['files']) > 3:
            print(f"   ... and {len(change['files']) - 3} more")
        print(f"   Complexity: {change['complexity']}")
        print(f"   Reasoning: {change['reasoning']}")
    
    print("\nRecommendations:")
    for rec in result['recommendations']:
        print(f"- {rec}")


async def demo_commit_validation():
    """Demonstrate validating existing commits."""
    print("\n=== Commit Validation Demo ===\n")
    
    validator = AtomicCommitValidator()
    result = await validator.invoke({"range": "HEAD~5..HEAD"})
    
    print(f"Commits analyzed: {result['commit_count']}")
    print(f"Average score: {result['average_score']:.1f}/100")
    print(f"Passed: {'✅' if result['passed'] else '❌'}")
    
    print("\nIndividual commits:")
    for val in result['validations']:
        status = '✅' if val['passed'] else '❌'
        print(f"{status} {val['hash'][:8]} - {val['subject']}")
        print(f"   Score: {val['score']}/100")
        if val['issues']:
            print(f"   Issues: {', '.join(val['issues'])}")


async def demo_commit_pipeline():
    """Demonstrate composing atomic commit nanobricks into a pipeline."""
    print("\n=== Commit Pipeline Demo ===\n")
    
    # Create a pipeline that analyzes and validates
    class CommitQualityChecker(NanobrickBase[Dict, Dict, None]):
        """Checks commit quality by analyzing and validating."""
        
        def __init__(self):
            super().__init__()
            self.analyzer = AtomicCommitAnalyzer()
            self.validator = AtomicCommitValidator()
        
        async def invoke(self, input_data: Dict, *, deps=None) -> Dict:
            # Analyze current changes
            analysis = await self.analyzer.invoke({})
            
            # Validate recent commits
            validation = await self.validator.invoke({"range": "HEAD~3..HEAD"})
            
            return {
                "current_changes": analysis,
                "recent_commits": validation,
                "quality_score": (
                    validation['average_score'] * 0.7 +  # 70% weight on past commits
                    (100 if analysis['logical_changes'] <= 3 else 80) * 0.3  # 30% on current
                ),
                "ready_to_commit": analysis['logical_changes'] == 1
            }
    
    checker = CommitQualityChecker()
    result = await checker.invoke({})
    
    print(f"Quality Score: {result['quality_score']:.1f}/100")
    print(f"Ready to commit: {'✅' if result['ready_to_commit'] else '❌ (needs splitting)'}")
    print(f"Current logical changes: {result['current_changes']['logical_changes']}")
    print(f"Recent commit average: {result['recent_commits']['average_score']:.1f}/100")


async def demo_skill_enhancement():
    """Demonstrate enhancing a brick with atomic commit skills."""
    print("\n=== Skill Enhancement Demo ===\n")
    
    # Create a simple feature development brick
    class FeatureDeveloper(NanobrickBase[str, Dict, None]):
        """Develops features with atomic commit awareness."""
        
        async def invoke(self, feature_name: str, *, deps=None) -> Dict:
            return {
                "feature": feature_name,
                "status": "implemented",
                "files_created": ["src/feature.py", "tests/test_feature.py"]
            }
    
    # Enhance with atomic commits skill
    developer = FeatureDeveloper()
    enhanced_developer = with_skill(developer, "atomic_commits", auto_validate=True)
    
    # Now the developer has atomic commit methods!
    print("Enhanced developer capabilities:")
    print(f"- analyze_commits: {hasattr(enhanced_developer, 'analyze_commits')}")
    print(f"- validate_commits: {hasattr(enhanced_developer, 'validate_commits')}")
    print(f"- suggest_commit: {hasattr(enhanced_developer, 'suggest_commit')}")
    
    # Use the enhanced developer
    result = await enhanced_developer.invoke("authentication")
    print(f"\nFeature implemented: {result['feature']}")
    
    # Analyze what should be committed
    if hasattr(enhanced_developer, 'analyze_commits'):
        analysis = await enhanced_developer.analyze_commits({})
        print(f"Suggested commits: {analysis.get('logical_changes', 0)}")


async def demo_commit_helper():
    """Demonstrate the all-in-one commit helper."""
    print("\n=== Commit Helper Demo ===\n")
    
    helper = AtomicCommitHelper()
    
    # Learn from project history
    learning = await helper.invoke({"command": "learn"})
    print("Learned patterns from history:")
    for insight in learning.get('insights', [])[:3]:
        print(f"- {insight}")
    
    # Get commit suggestion (mock since we need staged files)
    print("\nTo get commit suggestions:")
    print("1. Stage your changes: git add <files>")
    print("2. Run: await helper.invoke({'command': 'suggest'})")
    print("3. Get AI-powered commit message suggestions!")


async def main():
    """Run all demos."""
    print("🧱 Nanobricks Atomic Commits Demo\n")
    print("This demonstrates how atomic commits are implemented")
    print("as composable nanobricks - eating our own dog food!\n")
    
    try:
        await demo_atomic_commit_analyzer()
    except Exception as e:
        print(f"Analyzer demo skipped: {e}")
    
    try:
        await demo_commit_validation()
    except Exception as e:
        print(f"Validation demo skipped: {e}")
    
    await demo_commit_pipeline()
    await demo_skill_enhancement()
    
    try:
        await demo_commit_helper()
    except Exception as e:
        print(f"Helper demo skipped: {e}")
    
    print("\n✨ Demo complete!")
    print("\nKey takeaways:")
    print("1. Atomic commits are implemented as nanobricks")
    print("2. They compose naturally with pipe operators")
    print("3. Any brick can gain atomic commit powers via skills")
    print("4. The implementation showcases nanobricks' flexibility")


if __name__ == "__main__":
    asyncio.run(main())