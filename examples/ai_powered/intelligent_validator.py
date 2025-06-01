"""Example of an AI-powered intelligent validator."""

import asyncio
from typing import Any, Dict, Optional

from nanobricks import NanobrickBase, skill
from nanobricks.skills import SkillAI, create_ai_skill


class IntelligentValidator(NanobrickBase[Dict[str, Any], Dict[str, Any], None]):
    """
    A validator that uses AI to intelligently validate complex data.
    
    Instead of rigid rules, it understands context and can make
    smart decisions about data validity.
    """
    
    def __init__(
        self,
        context: Optional[str] = None,
        strict: bool = False,
        name: str = "intelligent_validator",
        version: str = "1.0.0",
    ):
        """Initialize intelligent validator.
        
        Args:
            context: Context about what kind of data to expect
            strict: Whether to be strict or lenient
            name: Validator name
            version: Validator version
        """
        super().__init__(name=name, version=version)
        self.context = context or "general data validation"
        self.strict = strict
    
    async def invoke(
        self, input: Dict[str, Any], *, deps: None = None
    ) -> Dict[str, Any]:
        """Validate data intelligently.
        
        Args:
            input: Data to validate
            deps: No dependencies required
            
        Returns:
            Validation result with explanations
        """
        # Basic structural validation
        if not isinstance(input, dict):
            return {
                "valid": False,
                "errors": ["Input must be a dictionary"],
                "suggestions": ["Wrap your input in a dictionary structure"],
            }
        
        # Intelligent validation would happen here with AI
        # For demo, we'll do some heuristic checks
        errors = []
        warnings = []
        suggestions = []
        
        # Check for common issues
        for key, value in input.items():
            if value is None:
                warnings.append(f"Field '{key}' is null")
            elif isinstance(value, str) and not value.strip():
                warnings.append(f"Field '{key}' is empty")
            elif isinstance(value, (list, dict)) and not value:
                warnings.append(f"Field '{key}' is an empty collection")
        
        # Context-aware validation
        if "email" in self.context.lower():
            for key, value in input.items():
                if isinstance(value, str) and "@" in value:
                    if not self._is_valid_email(value):
                        errors.append(f"Field '{key}' contains invalid email: {value}")
                        suggestions.append(f"Check the email format for '{key}'")
        
        if "phone" in self.context.lower():
            for key, value in input.items():
                if isinstance(value, str) and any(c.isdigit() for c in value):
                    if not self._is_valid_phone(value):
                        warnings.append(f"Field '{key}' might contain invalid phone: {value}")
        
        # Determine overall validity
        valid = len(errors) == 0
        if self.strict:
            valid = valid and len(warnings) == 0
        
        return {
            "valid": valid,
            "errors": errors,
            "warnings": warnings,
            "suggestions": suggestions,
            "data": input if valid else None,
            "confidence": 0.9 if valid else 0.3,
        }
    
    def _is_valid_email(self, email: str) -> bool:
        """Simple email validation."""
        parts = email.split("@")
        if len(parts) != 2:
            return False
        local, domain = parts
        return len(local) > 0 and "." in domain
    
    def _is_valid_phone(self, phone: str) -> bool:
        """Simple phone validation."""
        digits = "".join(c for c in phone if c.isdigit())
        return 7 <= len(digits) <= 15


# Example with AI enhancement
async def main():
    """Demonstrate intelligent validation with AI."""
    
    # Create validator
    validator = IntelligentValidator(
        context="user registration data with email and phone",
        strict=False
    )
    
    # Add AI skill for more intelligent validation
    ai_skill = create_ai_skill(
        enable_reasoning_trace=True,
        enable_memory=True,
    )
    
    # Enhance with AI
    ai_validator = validator.with_skill(ai_skill)
    
    # Test data
    test_cases = [
        {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "+1-555-123-4567",
            "age": 25,
        },
        {
            "name": "",
            "email": "invalid-email",
            "phone": "12345",
        },
        {
            "username": "alice",
            "contact": "alice@wonderland",
            "preferences": {},
        },
    ]
    
    print("Intelligent Validator Demo")
    print("=" * 50)
    
    for i, data in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"Input: {data}")
        
        result = await ai_validator.invoke(data)
        
        print(f"Valid: {result['valid']}")
        if result.get('errors'):
            print(f"Errors: {result['errors']}")
        if result.get('warnings'):
            print(f"Warnings: {result['warnings']}")
        if result.get('suggestions'):
            print(f"Suggestions: {result['suggestions']}")
        print(f"Confidence: {result.get('confidence', 0):.2f}")
        
        # Show AI reasoning if available
        if hasattr(ai_validator, 'get_reasoning_trace'):
            trace = ai_validator.get_reasoning_trace()
            if trace:
                print(f"AI Reasoning: {len(trace)} steps")
    
    # Show AI memory stats
    if hasattr(ai_validator, 'get_memory_stats'):
        stats = ai_validator.get_memory_stats()
        print(f"\nAI Memory Stats: {stats}")
    
    # Show cost report
    print(f"\nAI Cost Report: {ai_skill.get_cost_report()}")


if __name__ == "__main__":
    asyncio.run(main())