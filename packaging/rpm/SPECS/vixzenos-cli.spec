Name:           vixzenos-cli
Version:        0.3
Release:        1%{?dist}
Summary:        VixzenOS Command Center — the vix command line interface
License:        GPL-3.0-or-later
URL:            https://github.com/vixzen/vixzenos
BuildArch:      noarch

Requires:       python3
Recommends:     dnf
Recommends:     polkit

%description
vix is the VixzenOS command line: system info and status, a read-only
doctor with health checks, theme and Glass tier reporting, and the
vixzen-update helper that refreshes VixzenOS payload files.

%prep
%setup -q -c -T

%build

%install
rm -rf %{buildroot}
install -d -m 0755 %{buildroot}%{_bindir}
install -d -m 0755 %{buildroot}%{_datadir}/vixzen/cmd
install -d -m 0755 %{buildroot}%{_datadir}/vixzen/cmd/vixcmd
install -m 0755 %{_sourcedir}/vixzen-tree/apps/command-center/vix \
  %{buildroot}%{_bindir}/vix
install -m 0644 %{_sourcedir}/vixzen-tree/apps/command-center/vixcmd/*.py \
  %{buildroot}%{_datadir}/vixzen/cmd/vixcmd/
install -m 0755 %{_sourcedir}/vixzen-tree/scripts/vixzen-update.sh \
  %{buildroot}%{_bindir}/vixzen-update
install -m 0755 %{_sourcedir}/vixzen-tree/scripts/de-fedora.sh \
  %{buildroot}%{_datadir}/vixzen/de-fedora.sh

%files
%{_bindir}/vix
%{_bindir}/vixzen-update
%{_datadir}/vixzen/cmd
%{_datadir}/vixzen/de-fedora.sh

%changelog
* Wed Oct 21 2026 VixzenOS Team <dev@vixzen.os> - 0.3-1
- Initial VixzenOS Command Center package.
