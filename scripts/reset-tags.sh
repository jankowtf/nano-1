#!/bin/bash
# Script to clean up git tags for version reset to v0.1.0

echo "Git Tag Cleanup Script for Version Reset"
echo "========================================"
echo ""
echo "This script will:"
echo "1. Archive existing tags (v0.1.1 through v0.2.5)"
echo "2. Delete them from local and remote"
echo "3. Create a new v0.1.0 tag at the current commit"
echo ""
echo "WARNING: This is a destructive operation!"
echo "Make sure you have discussed this with your team."
echo ""

# Safety check
read -p "Are you sure you want to proceed? (yes/no): " confirmation
if [ "$confirmation" != "yes" ]; then
    echo "Operation cancelled."
    exit 0
fi

# Archive tags first
echo ""
echo "Step 1: Archiving existing tags..."
mkdir -p .git-archive
git tag -l | grep -E "^v0\.[12]\.[1-9]" > .git-archive/archived-tags.txt
echo "Archived tag list to .git-archive/archived-tags.txt"

# List tags that will be deleted
echo ""
echo "The following tags will be deleted:"
cat .git-archive/archived-tags.txt

# Final confirmation
echo ""
read -p "Proceed with deletion? (yes/no): " final_confirm
if [ "$final_confirm" != "yes" ]; then
    echo "Operation cancelled."
    exit 0
fi

# Delete local tags
echo ""
echo "Step 2: Deleting local tags..."
while IFS= read -r tag; do
    echo "Deleting local tag: $tag"
    git tag -d "$tag"
done < .git-archive/archived-tags.txt

# Delete remote tags
echo ""
echo "Step 3: Deleting remote tags..."
while IFS= read -r tag; do
    echo "Deleting remote tag: $tag"
    git push origin --delete "$tag" || echo "Failed to delete remote tag $tag (may not exist)"
done < .git-archive/archived-tags.txt

# Create new v0.1.0 tag
echo ""
echo "Step 4: Creating new v0.1.0 tag..."
git tag -a v0.1.0 -m "Reset to initial version

This tag represents the consolidation of all work from v0.1.1 through v0.2.5.
We are resetting to v0.1.0 to better reflect the project's maturity level
and to adopt an atomic commit-based development approach.

All previous functionality remains intact."

echo ""
echo "Step 5: Pushing new tag..."
git push origin v0.1.0

echo ""
echo "✅ Version reset complete!"
echo ""
echo "Next steps:"
echo "1. Update the CHANGELOG.md to reflect this reset"
echo "2. Notify all team members and users"
echo "3. Update any CI/CD pipelines that might reference specific versions"