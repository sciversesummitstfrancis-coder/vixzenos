# Publishing VixzenOS (maintainer runbook)

Everything you need to cut a VixzenOS release, in order. Total time after
the first setup: ~5 minutes (the RPMs are already built and tested).

## 0. One-time setup (30 min)

### a. COPR account + token
1. Sign in at <https://copr.fedorainfracloud.org> (Fedora Account; a GitHub
   sign-in works via FAS). Your COPR username is the "owner" namespace.
2. Open <https://copr.fedorainfracloud.org/api/> → "Request API token" → copy it.
3. Store it:
```bash
mkdir -p ~/.config
cat > ~/.config/copr <<EOF
[copr-cli]
copr_url = https://copr.fedorainfracloud.org
login = YOUR_COPR_USERNAME
token = YOUR_COPR_TOKEN
EOF
chmod 600 ~/.config/copr
copr-cli whoami     # must print your username
```

### b. Create the project (once)
```bash
copr-cli create vixzen/vixzenos
copr-cli get vixzen/vixzenos
```
Keep the owner name in sync with your COPR username if you prefer
`$USER/vixzenos` — the script reads `VIXZEN_COPR_PROJECT`.

## 1. Cut a release

```bash
cd /path/to/vixzenos

# 1. bump the version (one file drives the RPM versions)
echo 0.4 > packaging/rpm/VERSION

# 2. build + upload to COPR (builds, creates the project if missing,
#    picks a working chroot, uploads all 5 RPMs)
./scripts/vixzen-publish.sh
```
Expected tail:
```
Channel URL (add to client systems):
  https://copr.fedorainfracloud.org/groups/vixzen/vixzenos/fedora-44-x86_64/epr
```

## 2. Publish the ISO (do this on a fast connection)

```bash
export VIXZEN_GH_TOKEN=ghp_your_github_token
./scripts/vixzen-upload-iso.sh \
  /path/to/VixzenOS-0.4-x86_64.iso v0.4
```
The script auto-splits anything over GitHub's 2 GiB limit into `.part`
files, resumes interrupted uploads, and rate-limits the connection.

## 3. Tag + release notes

```bash
git tag -a v0.4 -m "VixzenOS 0.4"
git push origin main --tags
```
Then paste the release notes into the GitHub release body (the 0.3 one is a
good template — see `docs/RELEASES.md`).

## 4. Announce

- Update `website/index.html` version strings
- Update `packaging/rpm/VERSION` (done in step 1)
- Update `docs/MILESTONES.md`
- The website's download buttons probe for a local build; point them at the
  release URL for public downloads

## 5. Verify like a stranger would

```bash
# on a clean machine
sudo vixzen-repo-setup.sh
dnf list --available 'vixzenos-*'
sudo dnf install vixzenos-release
vix version
vix doctor
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `copr-cli whoami` errors | `~/.config/copr` missing or token expired → re-request |
| `build-package: --name required` | copr-cli 2.7 requires `--name` (script handles it) |
| "no usable chroot" | the project has no fedora-44 chroot: `copr-cli edit-chroot` or add one |
| ISO upload rejected | over 2 GiB → the script splits automatically |
| `vix update check` says channel disabled | run `sudo vixzen-repo-setup.sh` on that machine |
