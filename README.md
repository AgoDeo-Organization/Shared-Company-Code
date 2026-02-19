# JulienPythonToolkit-V001

Important code that I reuse through multiple projects. Please see license for allowed use.

## 🚀 Release & Publishing Guide (GitHub → PyPI)

This repository uses GitHub Actions to automatically build and publish the package to PyPI when a new version tag is created.

---

### How GitHub Actions Works in This Repository

The publishing workflow is defined in:

.github/workflows/publish.yml

The workflow is triggered **only when a new tag starting with `v` is pushed**.

Trigger condition:

on:
  push:
    tags:
      - "v*"

This means:

- Normal commits to `main` do NOT publish.
- Editing a GitHub release does NOT publish.
- Reusing an existing tag does NOT publish.
- Only a brand-new tag push triggers the workflow.

When triggered, the workflow:

1. Verifies the tag points to a commit on `main`
2. Builds the package using `python -m build`
3. Publishes to PyPI using Trusted Publishing

---

### PyPI Trusted Publishing

This project uses **PyPI Trusted Publishing (OIDC)**.

This means:

- No PyPI API token is stored in GitHub secrets.
- GitHub securely authenticates directly with PyPI.
- The workflow requires `id-token: write` permission.

If Trusted Publishing is not configured in the PyPI project settings, publishing will fail.

---

### Correct Release Workflow

Follow this process exactly.

1. Create a feature branch  
2. Make your changes  
3. Bump the version in `setup.py`  
   Example:  
   version='0.2.4'

4. Commit and push the branch  
5. Merge the branch into `main`  
6. On GitHub:
   - Go to **Releases**
   - Click **Draft a new release**
   - Create a new tag (e.g. `v0.2.4`)
   - Target branch must be `main`
   - Publish release

Creating the release creates and pushes the tag.

This triggers the GitHub Action.

To monitor progress:

Repository → Actions

Green check = success  
Red X = failure  

After success, the new version appears on PyPI.

---

### Important Rules

1. The tag must be new  
   Reusing the same tag will NOT trigger the workflow again.

2. The package version must be new  
   PyPI does not allow re-uploading the same version number, even if the previous upload failed.

3. The version inside the package must match the tag  
   Tag: v0.2.4  
   setup.py version: 0.2.4  

4. Always bump the version before merging to `main`.

5. Always tag after the change is merged to `main`.  
   Do not tag on feature branches.

6. Test the build locally before releasing:

   python -m pip install build  
   python -m build  

   If it fails locally, CI will fail.

---

### If Publishing Does Not Trigger

Check:

- Is the workflow file merged into `main`?
- Does the tag start with `v`?
- Is it a new tag?
- Does the tag target `main`?
- Is Trusted Publishing configured in PyPI?

---

### Release Summary

Branch → Implement changes → Bump version → Merge to main → Create GitHub release (new tag) → Workflow runs → Check Actions → Version appears on PyPI.

This ensures secure, reproducible, and clean releases.
