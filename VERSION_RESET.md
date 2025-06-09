# Version Reset to v0.1.0

## Rationale

We are resetting the version numbering from v0.2.5 back to v0.1.0 for the following reasons:

1. **Premature Version Bumps**: Previous versions (v0.1.1 - v0.2.5) were released too eagerly before the framework reached appropriate maturity milestones
2. **New Development Philosophy**: Moving from version-based development milestones to atomic commit-based development
3. **Semantic Versioning Alignment**: Starting fresh with v0.1.0 better reflects the current state as initial development phase
4. **Clear Communication**: This reset allows us to properly communicate the framework's maturity level to users

## Migration Guide for Existing Users

If you are currently using Nanobricks v0.2.x, please note:

1. **API Compatibility**: The core API remains unchanged - your code will continue to work
2. **Import Statements**: No changes needed to import statements
3. **Version Pinning**: Update your dependency specifications:
   ```toml
   # Old
   nanobricks = "^0.2.5"
   
   # New
   nanobricks = "^0.1.0"
   ```

## What This Means

- **v0.1.0**: Represents the current stable state with all features developed through v0.2.5
- **Future Versions**: Will follow semantic versioning more conservatively
- **Development Approach**: Focus shifts from version milestones to atomic commits and feature branches

## Technical Changes

This reset includes:
- Updating version numbers in `pyproject.toml` and `src/nanobricks/__init__.py`
- Cleaning up git tags (archiving old tags before deletion)
- Updating all documentation references
- Adding safeguards against future premature version bumps

## Questions?

If you have questions about this version reset, please:
- Check the updated roadmap in `docs/quarto/roadmap.qmd`
- Open an issue on GitHub
- Refer to the atomic development workflow documentation