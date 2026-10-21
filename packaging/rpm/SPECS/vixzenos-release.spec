Name:           vixzenos-release
Version:        0.3
Release:        1%{?dist}
Summary:        VixzenOS release identity, branding and update channel
License:        GPL-3.0-or-later
URL:            https://github.com/vixzen/vixzenos
BuildArch:      noarch

Requires:       vixzenos-apps
Requires:       vixzenos-theme
Requires:       vixzenos-cli
Requires:       vixzenos-cursor

%description
Release identity for VixzenOS: /etc/vixzen-release, the branded login
screen, the VixzenOS update channel configuration, and the de-branding
scrub that removes upstream branding from the running system.

%prep
%setup -q -c -T

%build

%install
rm -rf %{buildroot}
install -d -m 0755 %{buildroot}/etc
install -d -m 0755 %{buildroot}/usr/share/vixzen
install -d -m 0755 %{buildroot}%{_datadir}/vixzen

install -m 0644 %{_sourcedir}/vixzen-tree/packaging/rpm/vixzen-release \
  %{buildroot}/etc/vixzen-release
install -m 0644 %{_sourcedir}/vixzen-tree/packaging/rpm/vixzenos.repo \
  %{buildroot}%{_datadir}/vixzen/vixzenos.repo
install -m 0755 %{_sourcedir}/vixzen-tree/scripts/vixzen-repo-setup.sh \
  %{buildroot}%{_datadir}/vixzen/vixzen-repo-setup.sh
install -m 0755 %{_sourcedir}/vixzen-tree/scripts/de-fedora.sh \
  %{buildroot}%{_datadir}/vixzen/de-fedora.sh
install -m 0644 %{_sourcedir}/vixzen-tree/packaging/rpm/vixzen-motd \
  %{buildroot}%{_datadir}/vixzen/motd

%post
# Point dnf at the VixzenOS channel and scrub upstream branding.
if [ -f %{_datadir}/vixzen/vixzenos.repo ]; then
  if [ -d /etc/yum.repos.d ]; then
    cp %{_datadir}/vixzen/vixzenos.repo /etc/yum.repos.d/vixzenos.repo 2>/dev/null || :
  fi
fi
if [ -x %{_datadir}/vixzen/de-fedora.sh ]; then
  VIXZEN_ALLOW_HOST=1 bash %{_datadir}/vixzen/de-fedora.sh >/dev/null 2>&1 || :
fi
exit 0

%files
/etc/vixzen-release
%{_datadir}/vixzen/vixzenos.repo
%{_datadir}/vixzen/vixzen-repo-setup.sh
%{_datadir}/vixzen/de-fedora.sh
%{_datadir}/vixzen/motd

%changelog
* Wed Oct 21 2026 VixzenOS Team <dev@vixzen.os> - 0.3-1
- Initial VixzenOS release identity + update channel package.
