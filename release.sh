#!/usr/bin/env bash
set -euo pipefail

# Config
VERSION="v$(date +'%Y.%m.%d.%H%M')"
ZIP_FILE="tplink_mr200.zip"
COMPONENT_DIR="custom_components/tplink_router"
REMOTE="origin"

echo "==> Release script starting"
echo "Version: $VERSION"

# Ensure required commands exist
for cmd in git gh zip; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: required command '$cmd' not found in PATH" >&2
    exit 1
  fi
done

# Ensure we're in a git repo
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "ERROR: not a git repository (run from the repo root)." >&2
  exit 1
fi

# Determine current branch
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ -z "$BRANCH" ]; then
  echo "ERROR: could not determine current branch." >&2
  exit 1
fi
echo "==> Current branch: $BRANCH"

# Fetch remote refs
echo "==> Fetching from $REMOTE..."
git fetch "$REMOTE"

# 1) Stage & commit local changes if any
if [ -n "$(git status --porcelain)" ]; then
  echo "==> Local changes detected. Staging all changes..."
  git add -A

  echo "==> Committing changes..."
  git commit -m "Release $VERSION"
else
  echo "==> No local changes to commit."
fi

# 2) Sync with remote (pull --rebase)
echo "==> Rebasing local branch onto $REMOTE/$BRANCH to sync changes..."
# If the branch does not have an upstream, set it when pushing later; but we still try to rebase from remote/$BRANCH if it exists.
if git show-ref --verify --quiet "refs/remotes/$REMOTE/$BRANCH"; then
  if ! git pull --rebase "$REMOTE" "$BRANCH"; then
    echo "ERROR: rebase failed. Attempting to abort rebase..." >&2
    # try to abort rebase (if in one)
    if git rebase --abort >/dev/null 2>&1; then
      echo "Rebase aborted."
    fi
    echo "Please resolve conflicts manually and re-run the script." >&2
    exit 1
  fi
else
  echo "==> No upstream branch '$REMOTE/$BRANCH' found. Skipping pull --rebase."
fi

# 3) Push commits to remote
echo "==> Pushing commits to $REMOTE/$BRANCH"
# If branch has no upstream, set it.
if git rev-parse --abbrev-ref --symbolic-full-name "@{u}" >/dev/null 2>&1; then
  git push "$REMOTE" "$BRANCH"
else
  git push -u "$REMOTE" "$BRANCH"
fi

# 4) Create annotated tag (if not exists) and push it
if git rev-parse "$VERSION" >/dev/null 2>&1; then
  echo "==> Tag $VERSION already exists locally."
else
  echo "==> Creating annotated tag $VERSION"
  git tag -a "$VERSION" -m "Release $VERSION"
fi

echo "==> Pushing tag $VERSION to $REMOTE"
git push "$REMOTE" "$VERSION" || echo "Warning: failed to push tag (maybe remote already has it)"

# 5) Zip the component directory
if [ ! -d "$COMPONENT_DIR" ]; then
  echo "ERROR: component directory '$COMPONENT_DIR' not found." >&2
  exit 1
fi

echo "==> Creating zip $ZIP_FILE from $COMPONENT_DIR"
# Remove any prior zip to avoid including stale file
rm -f "$ZIP_FILE"
(cd "$COMPONENT_DIR" && zip -r ../../"$ZIP_FILE" .)

# 6) Create GitHub release with gh
echo "==> Creating GitHub release $VERSION"
gh release create "$VERSION" "$ZIP_FILE" --generate-notes

# 7) Clean up zip
echo "==> Removing $ZIP_FILE"
rm -f "$ZIP_FILE"

echo "==> Done. Release $VERSION created."
#!/usr/bin/env bash
set -euo pipefail

# Config
VERSION="v$(date +'%Y.%m.%d.%H%M')"
ZIP_FILE="tplink_mr200.zip"
COMPONENT_DIR="custom_components/tplink_router"
REMOTE="origin"

echo "==> Release script starting"
echo "Version: $VERSION"

# Ensure required commands exist
for cmd in git gh zip; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: required command '$cmd' not found in PATH" >&2
    exit 1
  fi
done

# Ensure we're in a git repo
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "ERROR: not a git repository (run from the repo root)." >&2
  exit 1
fi

# Determine current branch
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ -z "$BRANCH" ]; then
  echo "ERROR: could not determine current branch." >&2
  exit 1
fi
echo "==> Current branch: $BRANCH"

# Fetch remote refs
echo "==> Fetching from $REMOTE..."
git fetch "$REMOTE"

# 1) Stage & commit local changes if any
if [ -n "$(git status --porcelain)" ]; then
  echo "==> Local changes detected. Staging all changes..."
  git add -A

  echo "==> Committing changes..."
  git commit -m "Release $VERSION"
else
  echo "==> No local changes to commit."
fi

# 2) Sync with remote (pull --rebase)
echo "==> Rebasing local branch onto $REMOTE/$BRANCH to sync changes..."
# If the branch does not have an upstream, set it when pushing later; but we still try to rebase from remote/$BRANCH if it exists.
if git show-ref --verify --quiet "refs/remotes/$REMOTE/$BRANCH"; then
  if ! git pull --rebase "$REMOTE" "$BRANCH"; then
    echo "ERROR: rebase failed. Attempting to abort rebase..." >&2
    # try to abort rebase (if in one)
    if git rebase --abort >/dev/null 2>&1; then
      echo "Rebase aborted."
    fi
    echo "Please resolve conflicts manually and re-run the script." >&2
    exit 1
  fi
else
  echo "==> No upstream branch '$REMOTE/$BRANCH' found. Skipping pull --rebase."
fi

# 3) Push commits to remote
echo "==> Pushing commits to $REMOTE/$BRANCH"
# If branch has no upstream, set it.
if git rev-parse --abbrev-ref --symbolic-full-name "@{u}" >/dev/null 2>&1; then
  git push "$REMOTE" "$BRANCH"
else
  git push -u "$REMOTE" "$BRANCH"
fi

# 4) Create annotated tag (if not exists) and push it
if git rev-parse "$VERSION" >/dev/null 2>&1; then
  echo "==> Tag $VERSION already exists locally."
else
  echo "==> Creating annotated tag $VERSION"
  git tag -a "$VERSION" -m "Release $VERSION"
fi

echo "==> Pushing tag $VERSION to $REMOTE"
git push "$REMOTE" "$VERSION" || echo "Warning: failed to push tag (maybe remote already has it)"

# 5) Zip the component directory
if [ ! -d "$COMPONENT_DIR" ]; then
  echo "ERROR: component directory '$COMPONENT_DIR' not found." >&2
  exit 1
fi

echo "==> Creating zip $ZIP_FILE from $COMPONENT_DIR"
# Remove any prior zip to avoid including stale file
rm -f "$ZIP_FILE"
(cd "$COMPONENT_DIR" && zip -r ../../"$ZIP_FILE" .)

# 6) Create GitHub release with gh
echo "==> Creating GitHub release $VERSION"
gh release create "$VERSION" "$ZIP_FILE" --generate-notes

# 7) Clean up zip
echo "==> Removing $ZIP_FILE"
rm -f "$ZIP_FILE"

echo "==> Done. Release $VERSION created."
