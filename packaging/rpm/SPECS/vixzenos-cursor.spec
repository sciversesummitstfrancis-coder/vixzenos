Name:           vixzenos-cursor
Version:        0.3
Release:        1%{?dist}
Summary:        VixzenOS pointer theme
License:        GPL-3.0-or-later
URL:            https://github.com/vixzen/vixzenos
BuildArch:      noarch

%description
Pointer theme for VixzenOS. Ships the vendored WhiteSur cursor set (GPL,
attribution included) under its own name so it can never collide with the
upstream icon theme of the same name.

%prep
%setup -q -c -T

%build

%install
rm -rf %{buildroot}
install -d -m 0755 %{buildroot}/usr/share/icons
cp -a %{_sourcedir}/vixzen-tree/assets/cursors/WhiteSur \
  %{buildroot}/usr/share/icons/WhiteSur-cursors
install -m 0644 %{_sourcedir}/vixzen-tree/assets/cursors/WhiteSur.COPYING \
  %{buildroot}/usr/share/icons/WhiteSur-cursors/LICENSE 2>/dev/null || true

%post
if command -v gtk-update-icon-cache >/dev/null; then
  gtk-update-icon-cache -f %{_prefix}/share/icons/WhiteSur-cursors >/dev/null 2>&1 || :
fi
exit 0

%files
/usr/share/icons/WhiteSur-cursors

%changelog
* Wed Oct 21 2026 VixzenOS Team <dev@vixzen.os> - 0.3-1
- Initial VixzenOS cursor package.
