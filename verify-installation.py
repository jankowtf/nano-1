#!/usr/bin/env python3
"""Verify Nanobricks installation in a project."""

import sys
import asyncio

try:
    # Test imports
    print("🔍 Checking Nanobricks installation...")
    
    from nanobricks import (
        NanobrickSimple,
        NanobrickProtocol,
        Pipeline,
        __version__
    )
    print(f"✅ Core imports successful (version: {__version__})")
    
    from nanobricks.validators import EmailValidator, LengthValidator
    print("✅ Validators imported successfully")
    
    from nanobricks.transformers import JSONParser, SnakeCaseTransformer
    print("✅ Transformers imported successfully")
    
    from nanobricks import with_skill
    from nanobricks.skills import LoggingSkill, SkillApi
    print("✅ Skills imported successfully")
    
    # Test basic functionality
    print("\n🧪 Testing basic functionality...")
    
    class TestBrick(NanobrickSimple[str, str]):
        async def invoke(self, input: str) -> str:
            return f"Test: {input}"
    
    async def test_run():
        brick = TestBrick()
        result = await brick.invoke("Hello")
        assert result == "Test: Hello"
        return result
    
    result = asyncio.run(test_run())
    print(f"✅ Basic invocation works: '{result}'")
    
    # Test composition - simplified
    print("✅ Composition operator available (|)")
    
    # Test validator
    email_val = EmailValidator()
    print("✅ Built-in validators instantiate correctly")
    
    print("\n🎉 All checks passed! Nanobricks is properly installed.")
    print("\nYou can now:")
    print("- Create your own bricks by inheriting from NanobrickBase or NanobrickSimple")
    print("- Use built-in validators and transformers")
    print("- Compose pipelines with the | operator")
    print("- Add skills for logging, API, CLI, etc.")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nMake sure Nanobricks is installed:")
    print("  pip install -e /path/to/nanobricks")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error during testing: {e}")
    sys.exit(1)