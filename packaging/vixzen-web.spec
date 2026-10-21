Name:           vixzen-web
Version:        1.0
Release:        1%{?dist}
Summary:        Native lightweight web browser for VixzenOS
License:        MIT
Requires:       python3-gobject gtk4 libadwaita webkitgtk6.0
Source0:        vixzen-web-1.0.tar.gz

%description
Vixzen Web — Chrome-style tabs, Opera-style sidebar + speed dial,
WebKitGTK engine. Private by default, DuckDuckGo search.

%prep
%setup -q -n vixzen-web-1.0

%install
mkdir -p %{buildroot}/usr/share/vixzen/web %{buildroot}/usr/bin
mkdir -p %{buildroot}/usr/share/applications %{buildroot}/usr/share/icons/hicolor/scalable/apps
install -m755 apps/web-browser/vixzen_web.py %{buildroot}/usr/share/vixzen/web/
install -m755 apps/web-browser/vixzen-web %{buildroot}/usr/bin/vixzen-web
install -m644 assets/branding/vixzen-web.svg %{buildroot}/usr/share/icons/hicolor/scalable/apps/
cat > %{buildroot}/usr/share/applications/os.vixzen.web.desktop <<'EOF'
[Desktop Entry]
Name=Vixzen Web
Exec=/usr/bin/vixzen-web %U
Icon=vixzen-web
Type=Application
Categories=Network;WebBrowser;
MimeType=text/html;x-scheme-handler/http;x-scheme-handler/https;
EOF

%files
/usr/share/vixzen/web/vixzen_web.py
/usr/bin/vixzen-web
/usr/share/applications/os.vixzen.web.desktop
/usr/share/icons/hicolor/scalable/apps/vixzen-web.svg
