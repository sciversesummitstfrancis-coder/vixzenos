# VixzenOS Release & Update Channel (M7)

VixzenOS ships as **real RPM packages in its own repository**. Users update
with the tools they already know (`dnf upgrade`), and the channel is a
first-class VixzenOS thing — not "whatever the base distro had".

## Package set

| Package | Contents |
|---|---|
| `vixzenos-apps` | Vixzen Files, Settings, Power menu, Preview + `vixzen_core` |
| `vixzenos-theme` | Icons, GTK theme, shell theme, wallpapers |
| `vixzenos-cursor` | Pointer theme (ships as `WhiteSur-cursors` to avoid a name clash) |
| `vixzenos-cli` | `vix` command center + `vixzen-update` + de-brand scrub |
| `vixzenos-release` | `/etc/vixzen-release`, motd, channel config, branding scrub |

## Maintainer flow

```bash
# 1. bump the version
echo 0.4 > packaging/rpm/VERSION

# 2. build RPMs + local repo (no network needed)
./scripts/vixzen-rpm-build.sh

# 3. publish to the VixzenOS COPR project (needs copr-cli + login)
sudo dnf install copr-cli
copr-cli login
./scripts/vixzen-rpm-build.sh --publish
```

`--publish` uploads every built RPM to the COPR project `vixzen/vixzenos`.
COPR builds them for all Fedora versions and signs the repo.

## Client flow

```bash
# one-time: add the channel
sudo vixzen-repo-setup.sh

# then, like any distro
dnf upgrade                 # or: vix update check
vix update history          # what VixzenOS version is installed
```

To point at a private/alternative channel:
```bash
sudo vixzen-repo-setup.sh --url https://example.com/your-repo/epr
```

## Private channel (no public COPR)

The same packages work from any HTTP repo:

```bash
createrepo_c --update /var/www/vixzenos
rsync -av packaging/rpm/out/ /var/www/vixzenos/
```

and the client points at it with `--url`.

## What the channel does NOT do

- It does not replace the base distribution's security updates — those still
  come from the base channel. VixzenOS adds its own packages on top.
- It is not a snapshot/rollback system. Rollback belongs to the base
  distribution's tooling (Btrfs snapshots), not to a custom mechanism.

## Verified locally

```
$ ./scripts/vixzen-rpm-build.sh
built vixzenos-apps / -cli / -cursor / -release / -theme

$ dnf --repofrompath=vixzen-local,file:///tmp/vixzen-repo list --available 'vixzenos*'
vixzenos-apps.noarch     0.3-1.fc44  vixzen-local
vixzenos-cli.noarch      0.3-1.fc44  vixzen-local
vixzenos-cursor.noarch   0.3-1.fc44  vixzen-local
vixzenos-release.noarch  0.3-1.fc44  vixzen-local
vixzenos-theme.noarch    0.3-1.fc44  vixzen-local
```
