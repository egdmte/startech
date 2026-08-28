# Pushing STARTECH changes

This repository has two Git remotes:

- `origin`: the VPS-hosted repository used by production deployment;
- `github`: the GitHub mirror and pull-request repository.

Never force-push either remote. Commit history is the recovery system.

## Ordinary changes on `master`

Check exactly what will be committed:

```powershell
git status --short
git diff
git add -- path/to/file1 path/to/file2
git diff --cached
```

Run the relevant checks, then commit and publish to both remotes:

```powershell
git commit -m "Describe the completed change"
git pull --ff-only origin master
git push origin master
git push github master
```

Use explicit file paths with `git add`. Avoid `git add .` when unrelated work is present.

## Larger changes on a branch

```powershell
git switch master
git pull --ff-only origin master
git switch -c codex/short-change-name
```

Make and verify the change, then commit it:

```powershell
git add -- path/to/changed/files
git diff --cached
git commit -m "Describe the completed change"
git push -u github codex/short-change-name
```

After review, merge without rewriting history:

```powershell
git switch master
git pull --ff-only origin master
git merge --no-ff codex/short-change-name
git push origin master
git push github master
```

If Git reports a conflict or non-fast-forward update, stop and inspect the remote history.
Do not solve it with `--force`.

## Deploying KERİM to production

Production accepts only an exact full commit already published to `origin/master`:

```powershell
$kerimCommit = git rev-parse HEAD
ssh startech-vps "cd /srv/startech-cam/app && deployment/deploy_cam.sh $kerimCommit"
```

Verify that the service reports the deployed revision:

```powershell
Invoke-RestMethod https://dymtal.avartech.net/health | ConvertTo-Json
```

The reported commit must equal `$kerimCommit`. Deploying KERİM does not physically test
the car and does not change the car's active profile by itself.

## Undoing a bad published change

Keep the history and create a new reversal commit:

```powershell
git log --oneline --decorate -20
git revert <bad-commit>
git push origin master
git push github master
```

Then deploy the new revert commit using the production steps above. A merge commit may
require `git revert -m 1 <merge-commit>`; inspect the history before running it.
