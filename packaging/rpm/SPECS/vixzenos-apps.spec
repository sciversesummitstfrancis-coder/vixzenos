Name:           vixzenos-apps
Version:        0.3
Release:        1%{?dist}
Summary:        VixzenOS applications — Files, Settings, Power menu, Browser
License:        GPL-3.0-or-later
URL:            https://github.com/vixzen/vixzenos
BuildArch:      noarch

Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
Requires:       vixzenos-theme = %{version}-%{release}
Recommends:     nautilus
Recommends:     gnome-shell-extension-dash-to-dock

%description
Original VixzenOS applications built with GTK4 and Libadwaita:
Vixzen Files (file manager with previews, trash and clipboard actions),
Vixzen Settings (appearance, performance, school-admin controls) and the
Vixzen Start/Power menu.

%prep
%setup -q -c -T

%build
# no compilation: pure python + data

%install
rm -rf %{buildroot}
install -d -m 0755 %{buildroot}/usr/share/vixzen/apps
install -d -m 0755 %{buildroot}/usr/share/applications
install -d -m 0755 %{buildroot}/usr/share/vixzen/preview

install -m 0644 %{_sourcedir}/vixzen-tree/apps/file-manager/vixzen_files.py \
  %{buildroot}/usr/share/vixzen/apps/vixzen_files.py
install -m 0644 %{_sourcedir}/vixzen-tree/apps/system-settings/vixzen_settings.py \
  %{buildroot}/usr/share/vixzen/apps/vixzen_settings.py
install -m 0644 %{_sourcedir}/vixzen-tree/apps/power-menu/vixzen_power.py \
  %{buildroot}/usr/share/vixzen/apps/vixzen_power.py
install -d -m 0755 %{buildroot}/usr/share/vixzen/apps/web-browser
install -m 0644 %{_sourcedir}/vixzen-tree/apps/web-browser/vixzen_web.py \
  %{buildroot}/usr/share/vixzen/apps/vixzen_web.py 2>/dev/null || true
install -m 0644 %{_sourcedir}/vixzen-tree/preview/src/vixzen_preview.py \
  %{buildroot}/usr/share/vixzen/preview/vixzen_preview.py
install -m 0644 %{_sourcedir}/vixzen-tree/preview/src/design.py \
  %{buildroot}/usr/share/vixzen/preview/design.py
# desktop entries
install -m 0644 %{_sourcedir}/vixzen-tree/packaging/vixzen-menu.desktop \
  %{buildroot}/usr/share/applications/vixzen-menu.desktop
install -m 0644 %{_sourcedir}/vixzen-tree/packaging/vixzen-search.desktop \
  %{buildroot}/usr/share/applications/vixzen-search.desktop
install -d -m 0755 %{buildroot}/usr/lib/python3.14/site-packages/vixzen_core
install -m 0644 %{_sourcedir}/vixzen-tree/shared/vixzen_core/*.py \
  %{buildroot}/usr/lib/python3.14/site-packages/vixzen_core/ 2>/dev/null || true

%files
/usr/share/vixzen/apps
/usr/share/vixzen/preview
/usr/share/applications/vixzen-menu.desktop
/usr/share/applications/vixzen-search.desktop
/usr/lib/python3.14/site-packages/vixzen_core

%changelog
* Wed Oct 21 2026 VixzenOS Team <dev@vixzen.os> - 0.3-1
- Initial VixzenOS application package.
