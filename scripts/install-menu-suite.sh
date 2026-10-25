#!/bin/bash
# Bake the FULL Vixzen app suite (button/menu/search/web/blink) into the
# ISO tree, with system paths. Fixes: ISO installed extensions but not the
# apps they pinned (logo-menu pointed at missing .desktop files).
#
# Run: sudo ./scripts/install-menu-suite.sh
set -u
REPO="/home/shonshyjo/Documents/Default Project/vixzenos"
TREE="/home/shonshyjo/Documents/vixzen-surgery/vixroot"
SPEC=/etc/selinux/targeted/contexts/files/file_contexts
# sudo resets $HOME to /root — always use the real user's home
REALHOME="/home/shonshyjo"

[ "$(id -u)" -eq 0 ] || { echo "Run with sudo."; exit 1; }
[ -d "$TREE/usr/share" ] || { echo "Missing ISO tree."; exit 1; }

say(){ echo -e " - $*"; }

say "copying app suite (apps/, web, blink wrappers)"
install -d "$TREE/usr/share/vixzen/apps" "$TREE/usr/share/vixzen/web" \
          "$TREE/usr/share/vixzen/blink" "$TREE/usr/share/vixzen/branding" \
          "$TREE/usr/share/vixzen/icons" "$TREE/usr/local/bin" \
          "$TREE/usr/share/applications"
cp -r "$REPO/apps/." "$TREE/usr/share/vixzen/apps/"
rm -rf "$TREE/usr/share/vixzen/apps/"__pycache__
cp "$REPO/apps/web-browser/vixzen_web.py" "$TREE/usr/share/vixzen/web/" 2>/dev/null || say "   (no vixzen_web.py found)"
ls "$REPO/apps/web-browser-blink/"*.py >/dev/null 2>&1 && \
    cp "$REPO/apps/web-browser-blink/"*.py "$TREE/usr/share/vixzen/blink/"
install -m 755 "$REALHOME/.local/bin/vixzen-web" "$REALHOME/.local/bin/vixzen-blink" "$TREE/usr/local/bin/"

say "copying branding (button logo + search icons)"
cp "$REPO/assets/branding/logo.svg" "$TREE/usr/share/vixzen-branding/logo.svg" 2>/dev/null || say "   (repo logo.svg missing)"
cp "$REPO/assets/icons/"*.svg "$TREE/usr/share/vixzen/icons/" 2>/dev/null
cp -r "$REPO/assets/"*.svg "$TREE/usr/share/vixzen/icons/" 2>/dev/null

say "writing desktop entries (system-wide, pinned apps)"
write_desktop(){
 install -m 644 /dev/null "$TREE/usr/share/applications/$1"
 [ -n "$5" ] && sed "s|@@EXEC@@|$2|g; s|@@ICON@@|$3|g" "$5" > "$TREE/usr/share/applications/$1" || true
}
# power-menu family
cat > "$TREE/usr/share/applications/vixzen-search.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Vixzen Search
GenericName=Vixzen Search
Exec=python3 /usr/share/vixzen/apps/power-menu/vixzen_power.py --search
Icon=/usr/share/vixzen/icons/vixzen-search.svg
Terminal=false
Categories=System;
NoDisplay=false
EOF
cat > "$TREE/usr/share/applications/vixzen-menu.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Vixzen
GenericName=Vixzen Menu
Exec=python3 /usr/share/vixzen/apps/power-menu/vixzen_power.py
Icon=/usr/share/vixzen-branding/logo.svg
Terminal=false
Categories=System;
NoDisplay=false
EOF
# web + blink (Exec points at the local wrapper, which resolves the system copy)
cp "$REALHOME/.local/share/applications/os.vixzen.web.desktop" "$TREE/usr/share/applications/os.vixzen.web.desktop"
sed -i "s|^Exec=.*|Exec=/usr/local/bin/vixzen-web %U|" "$TREE/usr/share/applications/os.vixzen.web.desktop"
cp "$REALHOME/.local/share/applications/os.vixzen.blink.desktop" "$TREE/usr/share/applications/os.vixzen.blink.desktop"
sed -i "s|^Exec=.*|Exec=/usr/local/bin/vixzen-blink %U|" "$TREE/usr/share/applications/os.vixzen.blink.desktop"

say "fixing ownership + SELinux labels on the new files"
chown -R root:root "$TREE/usr/share/vixzen" "$TREE/usr/local/bin" "$TREE/usr/share/applications"
restorecon -R "$TREE/usr/share/vixzen" "$TREE/usr/local/bin" "$TREE/usr/share/applications" || \
  setfiles -F -r "$TREE" "$SPEC" /usr/share/vixzen /usr/local/bin /usr/share/applications

say "smoke test: entry file references resolve?"
for ref in "/usr/share/vixzen/apps/power-menu/vixzen_power.py" \
           "/usr/share/vixzen-branding/logo.svg" \
           "/usr/share/vixzen/icons/vixzen-search.svg"; do
  [ -f "$TREE$ref" ] && echo "   OK   $ref" || echo "   MISS $ref"
done
say "BAKED-OK"
