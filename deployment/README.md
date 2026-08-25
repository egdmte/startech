# CAM VPS operations

This directory describes the production service at `dymtal.avartech.net`. CAM
creates and stores real configuration documents. A temporary authenticated YAREN
link can report the active profile, run bounded capability checks, capture one
live calibration frame, install an inactive profile, and execute one explicitly
requested SAC workshop motor command. CAM cannot select a profile, start the
autonomous runtime, or turn a software receipt into physical evidence.

The public wiki at `wiki.avartech.net` is a separate service. Do not mix its files,
database, proxy rules, or deployment lifecycle with CAM.

## Initial directories and environment

Run these commands as `egemen`; enter sudo passwords only in the terminal.

```bash
sudo install -d -o egemen -g egemen -m 0750 /srv/startech-cam
sudo install -d -o egemen -g egemen -m 0700 /srv/startech-cam/shared
git clone <repository> /srv/startech-cam/app
python3 -m venv /srv/startech-cam/venv
/srv/startech-cam/venv/bin/pip install -r /srv/startech-cam/app/requirements.txt
```

Generate the session secret and password hash locally on the VPS:

```bash
/srv/startech-cam/venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(48))'
/srv/startech-cam/venv/bin/python -c 'import getpass; from werkzeug.security import generate_password_hash; print(generate_password_hash(getpass.getpass("CAM password: ")))'
```

Install `deployment/startech-cam.env.example` as `/etc/startech-cam.env`, fill
the two secret values with `sudoedit`, and keep the file `root:root 0600`.

```bash
sudo install -o root -g root -m 0600 deployment/startech-cam.env.example /etc/startech-cam.env
sudoedit /etc/startech-cam.env
sudo stat -c '%U:%G %a %n' /etc/startech-cam.env
```

Install the service and verify the local endpoint:

```bash
sudo install -o root -g root -m 0644 deployment/startech-cam.service /etc/systemd/system/startech-cam.service
sudo systemctl daemon-reload
sudo systemctl enable --now startech-cam.service
curl --fail --silent http://127.0.0.1:8765/health
```

`/health` returns `status` and the exact 40-character Git `release` loaded by the
running workers. A healthy process at the wrong revision is a failed deployment.

## Caddy and Cloudflare

Do not overwrite the VPS Caddyfile: it also serves unrelated sites. Merge the
single global block from `Caddyfile.startech-cam` into the existing top-level
global block, then merge only the `dymtal.avartech.net` site block. The trusted
proxy list accepts `CF-Connecting-IP` only when the direct peer belongs to a
published Cloudflare range. This lets Flask rate-limit the visitor instead of a
Cloudflare edge without trusting a header sent directly to the origin.

The committed ranges were checked on 2026-08-25. Re-check Cloudflare's official
IPv4 and IPv6 lists whenever CDN routing changes. Validate before reload:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
curl --fail --silent https://dymtal.avartech.net/health
```

Keep `CAM_TRUST_PROXY=1` only while Gunicorn remains reachable exclusively through
the local Caddy hop at `127.0.0.1:8765`. After proxy changes, perform one failed
login from a known external address and confirm the corresponding database audit
address is that client—not `127.0.0.1`, the VPS address, or a Cloudflare edge.
Never paste the address into a public issue or diagnostic bundle.

## Register YAREN

Create the private identity on the vehicle computer or Raspberry Pi:

```bash
python3 -m arac.ayar_cli web-key --device school-car
```

`~/.startech/yaren-device.json` is private and remains on the car.
`~/.startech/yaren-device.pub.json` may be copied to the VPS and registered:

```bash
scp ~/.startech/yaren-device.pub.json startech-vps:/tmp/school-car.pub.json
ssh startech-vps
cd /srv/startech-cam/app
sudo systemd-run --pipe --wait --collect --quiet \
  --uid=egemen --gid=egemen \
  --working-directory=/srv/startech-cam/app \
  --property=EnvironmentFile=/etc/startech-cam.env \
  /srv/startech-cam/venv/bin/flask --app wsgi:app \
  register-yaren-device --identity /tmp/school-car.pub.json --actor Egemen
rm /tmp/school-car.pub.json
```

Rotate or disable a registered device with the corresponding Flask CLI command;
never copy the private key to CAM. YAREN starts a 15-minute link with:

```bash
python3 -m arac.ayar_cli web-code --server https://dymtal.avartech.net --usb-index 0
```

Ctrl+C asks CAM to revoke the link. A live camera-frame request opens KASIM's
configured camera chain, captures one current frame, closes the device, and fails
if no physical camera responds. It has no generated-image fallback.

## One-command deployment

The target must be the exact full commit already present in `origin/master`. The
script refuses a dirty checkout, another branch, a non-master target, or a
non-fast-forward update. It creates an online SQLite backup, fast-forwards,
installs dependencies, runs the CAM/YAREN/configuration/workshop checks, reloads
Gunicorn, and waits until `/health` reports the requested revision. The complete
repository suite, including OpenCV vehicle perception, is run before the release is
merged; those vehicle-only dependencies are not installed into CAM's VPS environment.

```bash
cd /srv/startech-cam/app
deployment/deploy_cam.sh <full-40-character-master-commit>
```

For the first deployment that introduces the script, fetch the target and inspect
it before running its committed copy. Do not pipe an unreviewed remote script into
a privileged shell.

If a test or health check fails, the script prints the online-backup path and exits
non-zero. It does not rewrite Git history or silently restore an older schema.

## Backups and recovery

Create a consistent snapshot while CAM is running:

```bash
cd /srv/startech-cam/app
/srv/startech-cam/venv/bin/python deployment/backup_cam.py --label manual
```

The command uses SQLite's online backup API, verifies source and destination
integrity, writes mode `0600`, and creates a SHA-256 sidecar. A backup that exists
only on this VPS is not an off-site backup.

For encrypted at-rest export, install `age`, use a recipient whose private key is
not on the VPS, and copy both encrypted output and checksum elsewhere:

```bash
# Run on the VPS and copy the printed absolute path.
deployment/encrypt_cam_backup.sh '<age-recipient>'

# Then run on the off-site workstation.
scp startech-vps:/srv/startech-cam/shared/backups/<printed-name>.age* <encrypted-offsite-directory>/
```

SSH encrypts transport; the `.age` file preserves encryption at rest. Test a
restore periodically on a separate database path. For a real recovery, stop CAM,
preserve the failed database, verify the selected backup and checksum, install it
with owner `egemen`, group `egemen`, mode `0600`, and start CAM. Never open a new
schema using an older checkout. Put rollback code in a separate reviewed worktree
and decide database compatibility before switching the service.

## Diagnostics

Authenticated CAM users can download `startech-cam-diagnostic.json` from the
dashboard. It contains the running release, SQLite integrity/counts, recent
calibration metadata, and current-link configuration/capability/job records. It
excludes credentials, access codes, remote addresses, session data, and captured
JPEG bytes. KADER vehicle logs are explicitly not uploaded by the current link.

For service failures, inspect only what is needed:

```bash
systemctl status startech-cam.service --no-pager
journalctl -u startech-cam.service -n 100 --no-pager
```
