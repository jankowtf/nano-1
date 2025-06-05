# Pipe Operator Migration Summary

## Overview
Updated all occurrences of the old pipe operator `|` to the new `>>` operator in Quarto documentation files.

## Files Updated

### 1. quickstart.qmd
- Line 147-148: `TypeValidator() | EmailValidator()` → `TypeValidator() >> EmailValidator()`
- Line 188: `CSVParser() | SchemaValidator()` → `CSVParser() >> SchemaValidator()`

### 2. tutorial.qmd
- Line 131: `TextCleaner() | TextLowercaser() | TextTokenizer()` → `TextCleaner() >> TextLowercaser() >> TextTokenizer()`
- Line 149-150: `ProcessAdult() | SendWelcomeEmail()` → `ProcessAdult() >> SendWelcomeEmail()`
- Line 237: `ValidateRequest() | UserLoader()` → `ValidateRequest() >> UserLoader()`
- Line 437: `Loader() | Validator() | Transformer()` → `Loader() >> Validator() >> Transformer()`
- Line 533: `A() | B() | C()` → `A() >> B() >> C()`

### 3. human.qmd (11 instances)
- Updated all pipeline compositions to use `>>` operator
- Including examples like `greet | shout` → `greet >> shout`
- And complex pipelines like `loader | processor | validator | saver`

### 4. patterns.qmd
- Line 23: `validator | transformer | storage` → `validator >> transformer >> storage`
- Line 299: `StringValidator() | EmailPattern()` → `StringValidator() >> EmailPattern()`

### 5. Other Files
- roadmap.qmd: Line 123
- comparison.qmd: Line 123
- principles.qmd: Line 76
- architecture.qmd: Lines 66, 148, 149, 251
- type-utilities.qmd: Line 167
- design-philosophy.qmd: Updated description of pipe operator
- type-safety.qmd: Two instances
- sdk-guide.qmd: Two instances
- human-overview.qmd: Two pipeline examples
- index.qmd: One instance

## Total Changes
Approximately 35 instances of the pipe operator were updated across 13 Quarto documentation files.

## Notes
- All changes maintain the same functionality
- The `>>` operator is consistent with the v0.2.0 release
- Table formatting with `|` characters was preserved (not code-related)