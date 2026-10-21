Name:           vixzen-blink
Version:        0.4
Release:        1%{?dist}
Summary:        Experimental Chromium-engine browser for VixzenOS (fallback)
License:        MIT
# Fedora equivalents of the pip packages used in development:
# (python3-pyqt6 + qt6-qtwebengine) or (python3-pyside6 + qt6-qtwebengine)
Requires:       python3-pyqt6 qt6-qtwebengine
Requires:       vixzen-web
Source0:        vixzen-blink-0.4.tar.gz

%description
Vixzen Blink — EXPERIMENTAL fallback browser on real Chromium/Blink
(QtWebEngine) for Chrome-only sites. Shares bookmarks, history, settings
and Vixzen Search with Vixzen Web (the lightweight default).

%prep
%setup -q -n vixzen-blink-0.4

%install
mkdir -p %{buildroot}/usr/share/vixzen/blink %{buildroot}/usr/bin
mkdir -p %{buildroot}/usr/share/applications
install -m755 apps/web-browser-blink/vixzen_blink.py %{buildroot}/usr/share/vixzen/blink/
install -m755 apps/web-browser-blink/vixzen-blink %{buildroot}/usr/bin/vixzen-blink
cat > %{buildroot}/usr/share/applications/os.vixzen.blink.desktop <<'EOF'
[Desktop Entry]
Name=Vixzen Blink (Experimental)
Exec=/usr/bin/vixzen-blink %U
Icon=vixzen-web
Type=Application
Categories=Network;WebBrowser;
MimeType=text/html;x-scheme-handler/http;x-scheme-handler/https;
EOF

%files
/usr/share/vixzen/blink/vixzen_blink.py
/usr/bin/vixzen-blink
/usr/share/applications/os.vixzen.blink.desktop
