# Copilot Agent Instructions

## Pull Request Base Branch Policy

When creating a new Pull Request:

- **Always use `dev` as the base branch by default**
- Do **not** use `main`, `master`, or any other branch unless explicitly instructed
- If the user mentions a different base branch, follow that instruction exactly

### Summary Rule

> **Default base branch = `dev`**  
> **Override only when explicitly requested**

This rule applies to:
- New feature branches
- Bug fixes
- Refactors
- Documentation changes
- Any automated or suggested pull request creation
