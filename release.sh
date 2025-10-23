#!/usr/bin/env bash
set -euo pipefail

# Version uses date-time: vYYYY.MM.DD.HHMM
VERSION="v$(date +'%Y.%m.%d.%H%M')"
ZIP_FILE="tplink_mr200.zip"
COMPONENT_DIR="custom_components/tplink_router"

echo "==> Release script starting"
echo "Version: $VERSION"

# Ensure required commands exist
for cmd in git gh zip; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: required command '$cmd' not found in PATH" >&2
    exit 1
  fi
done

# 1) Commit any changes (if present)
if [ -n "$(git status --porcelain)" ]; then
  echo "==> Staging all changes..."
  git add -A

  echo "==> Committing..."
  git commit -m "Release $VERSION"

  echo "==> Pushing commits to remote..."
  git push
else
  echo "==> No changes to commit."
fi

# 2) Create annotated tag (if not exists) and push it
if git rev-parse "$VERSION" >/dev/null 2>&1; then
  echo "==> Tag $VERSION already exists locally."
else
  echo "==> Creating tag $VERSION"
  git tag -a "$VERSION" -m "Release $VERSION"
fi

echo "==> Pushing tag $VERSION to origin"
git push origin "$VERSION" || echo "Warning: failed to push tag (maybe remote already has it)"

# 3) Zip the component directory
if [ ! -d "$COMPONENT_DIR" ]; then
  echo "ERROR: component directory '$COMPONENT_DIR' not found." >&2
  exit 1
fi

echo "==> Creating zip $ZIP_FILE from $COMPONENT_DIR"
(cd "$COMPONENT_DIR" && zip -r ../../"$ZIP_FILE" .)

# 4) Create GitHub release with gh
echo "==> Creating GitHub release $VERSION"
gh release create "$VERSION" "$ZIP_FILE" --generate-notes

# 5) Clean up zip
echo "==> Removing $ZIP_FILE"
rm -f "$ZIP_FILE"

echo "==> Done. Release $VERSION created."

