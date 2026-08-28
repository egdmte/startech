#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: deployment/encrypt_cam_backup.sh <age-recipient>" >&2
    exit 2
fi
if ! command -v age >/dev/null 2>&1; then
    echo "age is required for encrypted at-rest export" >&2
    exit 1
fi

CAM_AGE_RECIPIENT=$1
CAM_APP_DIR=${CAM_APP_DIR:-/srv/startech-cam/app}
CAM_PYTHON=${CAM_PYTHON:-/srv/startech-cam/venv/bin/python}

cd "$CAM_APP_DIR"
CAM_BACKUP_PATH=$("$CAM_PYTHON" deployment/backup_cam.py --label offsite)
CAM_ENCRYPTED_PATH="$CAM_BACKUP_PATH.age"
if [ -e "$CAM_ENCRYPTED_PATH" ]; then
    echo "encrypted destination already exists: $CAM_ENCRYPTED_PATH" >&2
    exit 1
fi
age --encrypt --recipient "$CAM_AGE_RECIPIENT" --output "$CAM_ENCRYPTED_PATH" "$CAM_BACKUP_PATH"
chmod 600 "$CAM_ENCRYPTED_PATH"
sha256sum "$CAM_ENCRYPTED_PATH" > "$CAM_ENCRYPTED_PATH.sha256"
chmod 600 "$CAM_ENCRYPTED_PATH.sha256"
printf '%s\n' "$CAM_ENCRYPTED_PATH"
