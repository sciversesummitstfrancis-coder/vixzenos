Name:           vixzenos-theme
Version:        0.3
Release:        1%{?dist}
Summary:        VixzenOS visual identity — icons, GTK theme, shell theme
License:        GPL-3.0-or-later
URL:            https://github.com/vixzen/vixzenos
BuildArch:      noarch

%description
The VixzenOS visual identity: the Vixzen icon theme (original neon artwork),
the GTK4 theme for native applications, the GNOME Shell theme and the
wallpaper set.

%prep
%setup -q -c -T

%build

%install
rm -rf %{buildroot}
install -d -m 0755 %{buildroot}/usr/share/icons
install -d -m 0755 %{buildroot}/usr/share/themes
install -d -m 0755 %{buildroot}/usr/share/backgrounds/vixzen
install -d -m 0755 %{buildroot}/usr/share/gtk-4.0
install -d -m 0755 %{buildroot}/usr/share/vixzen/gtk

cp -a %{_sourcedir}/vixzen-tree/assets/icons/theme/Vixzen \
  %{buildroot}/usr/share/icons/Vixzen
install -m 0644 %{_sourcedir}/vixzen-tree/assets/gtk-theme/vixzen-gtk-dark.css \
  %{buildroot}/usr/share/gtk-4.0/gtk.css
install -m 0644 %{_sourcedir}/vixzen-tree/assets/gtk-theme/vixzen-gtk-dark.css \
  %{buildroot}/usr/share/gtk-4.0/gtk-dark.css
install -m 0644 %{_sourcedir}/vixzen-tree/assets/gtk-theme/vixzen-gtk.css \
  %{buildroot}/usr/share/vixzen/gtk/vixzen-gtk.css
install -m 0644 %{_sourcedir}/vixzen-tree/assets/shell-theme/gnome-shell.css \
  %{buildroot}/usr/share/themes/Vixzen-gnome-shell.css
install -m 0644 %{_sourcedir}/vixzen-tree/assets/wallpapers/*.png \
  %{buildroot}/usr/share/backgrounds/vixzen/ 2>/dev/null || true
install -m 0644 %{_sourcedir}/vixzen-tree/assets/wallpapers/indigo-dusk.svg \
  %{buildroot}/usr/share/backgrounds/vixzen/ 2>/dev/null || true
install -m 0644 %{_sourcedir}/vixzen-tree/assets/branding/logo.svg \
  %{buildroot}/usr/share/vixzen-branding-logo.svg 2>/dev/null || true

%post
if command -v gtk-update-icon-cache >/dev/null; then
  gtk-update-icon-cache -f %{_prefix}/share/icons/Vixzen >/dev/null 2>&1 || :
fi
if command -v dconf >/dev/null; then
  dconf update >/dev/null 2>&1 || :
fi
exit 0

%postun
if command -v gtk-update-icon-cache >/dev/null; then
  gtk-update-icon-cache -f %{_prefix}/share/icons/Vixzen >/dev/null 2>&1 || :
fi
exit 0

%files
/usr/share/icons/Vixzen
/usr/share/themes/Vixzen-gnome-shell.css
/usr/share/backgrounds/vixzen
/usr/share/gtk-4.0
/usr/share/vixzen/gtk
/usr/share/vixzen-branding-logo.svg

%changelog
* Wed Oct 21 2026 VixzenOS Team <dev@vixzen.os> - 0.3-1
- Initial VixzenOS visual identity package.
