#!/usr/bin/env bash
# Prepare a release: set the version and date in package.xml, commit, and tag.
# Usage: scripts/release.sh X.Y.Z[-suffix]
# Nothing is pushed. Review the commit and tag, then push the tag to start the release workflow.
set -euo pipefail

VERSION="${1:?usage: scripts/release.sh X.Y.Z[-suffix]}"
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$ ]]; then
    echo "error: '$VERSION' is not a version like 1.2.3 or 1.2.3-rc.1" >&2
    exit 1
fi

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ "$(git branch --show-current)" != "main" ]; then
    echo "error: releases are made from main" >&2
    exit 1
fi
if [ -n "$(git status --porcelain)" ]; then
    echo "error: the working tree is not clean" >&2
    exit 1
fi
if git rev-parse -q --verify "refs/tags/v$VERSION" >/dev/null; then
    echo "error: tag v$VERSION already exists" >&2
    exit 1
fi

TODAY="$(date +%F)"
perl -pi -e "s#<version>.*</version>#<version>$VERSION</version>#; s#<date>.*</date>#<date>$TODAY</date>#" \
    Construct/package.xml

# The version and date may already match, for example for the first release.
if ! git diff --quiet; then
    git commit -q -a -m "chore: Prepare release v$VERSION" \
        -m "Set the package.xml version to $VERSION and the release date to $TODAY."
fi
git tag -a "v$VERSION" -m "v$VERSION"

echo "Prepared v$VERSION. Review with 'git show v$VERSION', then push with:"
echo "  git push origin main v$VERSION"
