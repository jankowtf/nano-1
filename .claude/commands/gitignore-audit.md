# Audit and Clean .gitignore

This command audits the repository for files that are tracked by Git but should be ignored according to `.gitignore` patterns, and optionally removes them from version control.

## Step 1: Audit for Ignored Files

RUN `git ls-files -i -c --exclude-standard`

If any files are listed, these are currently tracked by Git but match patterns in `.gitignore`.

## Step 2: Show Statistics

RUN the following to get a count and size information:
```bash
echo "📊 Statistics:"
echo "Total ignored files in tracking: $(git ls-files -i -c --exclude-standard | wc -l)"
echo "Repository size: $(du -sh .git | cut -f1)"
```

## Step 3: Review Before Cleanup

If files were found, review the list carefully. These files will be removed from Git tracking but will remain in your working directory.

## Step 4: Remove from Tracking (if confirmed)

If you want to proceed with removing these files from Git tracking:

RUN `git rm -r --cached . && git add .`

This will:
1. Remove all files from Git's index
2. Re-add only files that aren't ignored
3. Keep all files in your working directory

## Step 5: Commit Changes

If changes were made, commit them:

RUN `git commit -m "chore: remove ignored files from tracking"`

## Step 6: (Optional) Clean History

⚠️ **WARNING**: This rewrites history and requires force pushing. Only do this if absolutely necessary and after coordinating with your team.

To remove ignored files from entire Git history, see the Git Cheat Sheet at `docs/quarto/git-cheat-sheet.qmd` for detailed instructions using BFG Repo-Cleaner or git-filter-repo.

## Notes

- This command only removes files from Git tracking, not from your filesystem
- Always review the list of files before proceeding
- For removing files from history, backup your repository first
- After cleaning history, all team members need to re-clone the repository