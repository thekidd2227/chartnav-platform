#!/usr/bin/env bash
# Build a releasable bundle locally.
#
# Produces, under dist/release/<version>/:
#   - chartnav-api-<version>.tar       (docker save of chartnav-api:<version>)
#   - chartnav-web-<version>.tar.gz    (apps/web/dist built with vite)
#   - MANIFEST.txt                     (git ref, sha, dates, sizes, sha256s)
#
# Version resolution:
#   $1 if given; else the exact git tag if HEAD is tagged; else "dev-<short-sha>".

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

resolve_version() {
    if [ "${1:-}" != "" ]; then echo "$1"; return; fi
    local tag
    tag=$(git describe --tags --exact-match 2>/dev/null || true)
    if [ -n "$tag" ]; then echo "$tag"; return; fi
    echo "dev-$(git rev-parse --short HEAD)"
}

VERSION="$(resolve_version "${1:-}")"
GIT_SHA="$(git rev-parse HEAD)"
GIT_REF="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo detached)"
OUT_DIR="$REPO_ROOT/dist/release/$VERSION"
mkdir -p "$OUT_DIR"

echo "==> release $VERSION  (sha=$GIT_SHA  ref=$GIT_REF)"

# ---------- API image ----------------------------------------------------
API_TAG="chartnav-api:$VERSION"
echo "==> building $API_TAG"
docker build -t "$API_TAG" apps/api
API_TAR="$OUT_DIR/chartnav-api-$VERSION.tar"
docker save "$API_TAG" -o "$API_TAR"

# ---------- Web bundle ---------------------------------------------------
echo "==> building apps/web"
( cd apps/web && { npm ci --prefer-offline --no-audit --fund=false >/dev/null 2>&1 || npm ci; } )
( cd apps/web && npm run build )
WEB_TGZ="$OUT_DIR/chartnav-web-$VERSION.tar.gz"
tar -C apps/web/dist -czf "$WEB_TGZ" .

# ---------- Staging bundle ----------------------------------------------
# A tarball of everything an operator needs to stand up staging against
# this release: the compose file, env template, and runbook scripts.
# Explicitly does NOT include real secrets.
STAGE_TGZ="$OUT_DIR/chartnav-staging-$VERSION.tar.gz"
tar -czf "$STAGE_TGZ" \
    -C "$REPO_ROOT" \
    infra/docker/docker-compose.staging.yml \
    infra/docker/.env.staging.example \
    scripts/staging_up.sh \
    scripts/staging_verify.sh \
    scripts/staging_rollback.sh \
    docs/build/19-staging-deployment.md \
    docs/build/20-observability.md \
    docs/build/21-staging-runbook.md

# ---------- Manifest -----------------------------------------------------
{
    echo "chartnav release manifest"
    echo "version: $VERSION"
    echo "git_sha: $GIT_SHA"
    echo "git_ref: $GIT_REF"
    echo "built_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo ""
    echo "artifacts:"
    for f in "$API_TAR" "$WEB_TGZ" "$STAGE_TGZ"; do
        size=$(du -h "$f" | awk '{print $1}')
        sha=$(shasum -a 256 "$f" | awk '{print $1}')
        echo "  $(basename "$f")  ${size}  sha256=${sha}"
    done
} > "$OUT_DIR/MANIFEST.txt"

echo "==> done"
echo "    artifacts: $OUT_DIR"
ls -1 "$OUT_DIR"
