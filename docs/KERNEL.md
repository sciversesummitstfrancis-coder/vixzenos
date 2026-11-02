# VixzenOS Kernel Identity

VixzenOS builds its own kernel release tag so nothing on a running system
advertises another distribution.

## What changes

| Surface | Upstream build | VixzenOS build |
|---|---|---|
| `uname -r` | `7.2.13-200.fc44.x86_64` | `7.2.13-200.vixzen.x86_64` |
| `/lib/modules/<ver>` | `...fc44...` | `...vixzen...` |
| RPM NEVRA | `kernel-7.2.13-200.fc44.x86_64` | `kernel-7.2.13-200.vixzen.x86_64` |
| Secure Boot SBAT | `fedora` | `vixzen` |

The kernel source, configs, patches and signing machinery stay upstream. Only
the identity is VixzenOS. That is deliberate: forking the kernel would trade
hardware compatibility for a cosmetic win.

## The lever: `%dist`

RPM derives the release tag from `%{?dist}`, which on a Fedora-compatible host
expands to `.fc44`. The kernel spec's own `-vixzen` suffix hack is gone, because
it made `/lib/modules` disagree with `uname -r`.

The identity lives in one idempotent patcher:

```bash
./scripts/vixzen-kernel-identity.sh                 # patch ~/rpmbuild/SPECS/kernel.spec
./scripts/vixzen-kernel-identity.sh --check         # report only
./scripts/vixzen-kernel-identity.sh path/to/kernel.spec
```

It adds this block to the spec:

```spec
%define dist .vixzen
%define dist_vendor VixzenOS
%define dist_name VixzenOS
%define dist_purl_namespace vixzenos
```

and sets `%global sbat_suffix vixzen`.

Verify without building:

```bash
rpmspec -q --qf '%{name}-%{version}-%{release}.%{arch}\n' ~/rpmbuild/SPECS/kernel.spec | head -n 1
# kernel-7.2.13-200.vixzen.x86_64
```

## Building

```bash
bash ~/rpmbuild/build-vixzen-kernel.sh
```

The launcher runs the identity patcher first, then does a full `rpmbuild -bb`
for the standard x86_64 kernel only (`--with baseonly`, no debug flavour, docs
or debuginfo). Output lands in `~/rpmbuild/RPMS/x86_64/`.

Build notes for the target laptop (i5-6200U, 8 GB RAM):

- One compile job is intentional (`--define '_smp_mflags -j1'`); more jobs
  thrash 8 GB.
- `TMPDIR` is redirected to `$HOME/tmp-kernel-build` because `/tmp` is a small
  RAM-backed tmpfs and runs out of space at peak.
- `systemd-inhibit` keeps the machine awake. The timer pair
  `vixzen-park.timer` / `vixzen-resume.timer` parks and resumes the build tree
  so an overnight run does not cook the laptop.
- A terminated build leaves `~/rpmbuild/BUILD/kernel-7.2.13-build` stale. Start
  from a clean tree before trusting the identity: the old tree still carries the
  pre-change release tag.

## Shipping it in the ISO

`build-vixzenos.sh` looks for a built kernel in two places:

```bash
packaging/rpm/out/kernel-*.vixzen*.rpm
~/rpmbuild/RPMS/x86_64/kernel-*.vixzen*.rpm
```

When one exists it:

1. copies the RPMs into `~/.cache/vixzen-publish/kernel-repo/`,
2. builds repo metadata with `createrepo_c`,
3. serves that repo on `http://10.0.2.2:8009/` (the same user-net HTTP path the
   branding tarball already uses),
4. hands `livemedia-creator` a generated kickstart with
   `repo --name=vixzenos-kernel --baseurl=http://10.0.2.2:8009/ --cost=1`.

The VixzenOS release tag sorts higher than the upstream tag, so the installer
picks the VixzenOS kernel. When no kernel is built, the log says so and the ISO
boots with the upstream kernel instead — the build never fails for a missing
optional artifact.

## Installed identity

The kickstarts write the identity at image build time:

- `/etc/vixzen-release` — canonical VixzenOS fields
- `/etc/os-release` and `/usr/lib/os-release` — replaced copies (not symlinks to
  upstream), so `ID_LIKE`, `CPE_NAME` and upstream `VARIANT_ID` cannot survive
- `/etc/system-release` — `VixzenOS release 0.3 (Preview)`
- `/etc/dnf/vars/releasever` — pinned repository release number

`scripts/de-fedora.sh` performs the same rewrite on an existing tree when
`/etc/vixzen-release` is present.

## Honest boundary

The kernel tag and OS identity are VixzenOS. The package base underneath is
still Fedora-compatible, and the update channel is a COPR repository. Full
package independence needs VixzenOS-owned repositories; until then, public copy
says "independent Linux distribution" without claiming a from-scratch package
base.
