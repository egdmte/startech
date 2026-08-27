#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: deployment/deploy_cam.sh <full-master-commit>" >&2
    exit 2
fi

CAM_TARGET_COMMIT=$1
CAM_APP_DIR=${CAM_APP_DIR:-/srv/startech-cam/app}
CAM_PYTHON=${CAM_PYTHON:-/srv/startech-cam/venv/bin/python}
CAM_PIP=${CAM_PIP:-/srv/startech-cam/venv/bin/pip}
CAM_SERVICE=${CAM_SERVICE:-startech-cam.service}
KERIM_RELEASE_REFERENCE_FILE=${KERIM_RELEASE_REFERENCE_FILE:-/srv/startech-cam/shared/published-master.json}

case "$CAM_TARGET_COMMIT" in
    *[!0-9a-f]*|'')
        echo "target must be one full lowercase Git commit SHA" >&2
        exit 2
        ;;
esac
if [ "${#CAM_TARGET_COMMIT}" -ne 40 ]; then
    echo "target must be one full 40-character Git commit SHA" >&2
    exit 2
fi

cd "$CAM_APP_DIR"
if [ "$(git symbolic-ref --short HEAD)" != "master" ]; then
    echo "deployment checkout must be on master" >&2
    exit 1
fi
if [ -n "$(git status --porcelain)" ]; then
    echo "deployment checkout is dirty; refusing to overwrite it" >&2
    exit 1
fi

git fetch origin master
CAM_RESOLVED_COMMIT=$(git rev-parse --verify "$CAM_TARGET_COMMIT^{commit}")
if [ "$CAM_RESOLVED_COMMIT" != "$CAM_TARGET_COMMIT" ]; then
    echo "target did not resolve to the exact requested commit" >&2
    exit 1
fi
git merge-base --is-ancestor "$CAM_TARGET_COMMIT" origin/master || {
    echo "target is not present in origin/master" >&2
    exit 1
}
git merge-base --is-ancestor HEAD "$CAM_TARGET_COMMIT" || {
    echo "target is not a fast-forward from the deployed commit" >&2
    exit 1
}

CAM_BACKUP_LABEL=$(printf '%s' "$CAM_TARGET_COMMIT" | cut -c1-12)
CAM_BACKUP_PATH=$(
    "$CAM_PYTHON" deployment/backup_cam.py --label "$CAM_BACKUP_LABEL"
)
echo "database backup: $CAM_BACKUP_PATH"

git merge --ff-only "$CAM_TARGET_COMMIT"
"$CAM_PIP" install -r requirements.txt
"$CAM_PYTHON" -m unittest discover -s tests -p 'test_cam*.py'
# Keep this set runnable with KERİM's server dependencies.
"$CAM_PYTHON" -m unittest \
    tests.test_configuration \
    tests.test_configuration_v2 \
    tests.test_profiles \
    tests.test_tawnt

CAM_PUBLISHED_COMMIT=$(git rev-parse --verify 'origin/master^{commit}')
"$CAM_PYTHON" deployment/write_release_reference.py \
    --git-dir "$CAM_APP_DIR/.git" \
    --output "$KERIM_RELEASE_REFERENCE_FILE" \
    --commit "$CAM_PUBLISHED_COMMIT"

CAM_MAIN_PID=$(systemctl show --property MainPID --value "$CAM_SERVICE")
case "$CAM_MAIN_PID" in
    ''|*[!0-9]*|0)
        echo "CAM service has no live main process to reload" >&2
        exit 1
        ;;
esac
CAM_MAIN_USER=$(ps -o user= -p "$CAM_MAIN_PID" | awk '{$1=$1; print}')
if [ "$CAM_MAIN_USER" != "$(id -un)" ]; then
    echo "CAM service belongs to $CAM_MAIN_USER, not the deployment account" >&2
    exit 1
fi
kill -HUP "$CAM_MAIN_PID"

CAM_HEALTH_OK=0
CAM_ATTEMPT=0
while [ "$CAM_ATTEMPT" -lt 20 ]; do
    if "$CAM_PYTHON" - "$CAM_TARGET_COMMIT" <<'PY'
import json
import sys
from urllib.request import urlopen

with urlopen("http://127.0.0.1:8765/health", timeout=2) as response:
    health = json.load(response)
if health != {"status": "ok", "release": sys.argv[1]}:
    raise SystemExit(1)
PY
    then
        CAM_HEALTH_OK=1
        break
    fi
    CAM_ATTEMPT=$((CAM_ATTEMPT + 1))
    sleep 1
done

if [ "$CAM_HEALTH_OK" -ne 1 ]; then
    echo "CAM did not report the requested release; backup remains at $CAM_BACKUP_PATH" >&2
    exit 1
fi
echo "deployed CAM release $CAM_TARGET_COMMIT"
