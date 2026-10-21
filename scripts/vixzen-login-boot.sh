#!/bin/bash
# Vixzen login + boot + tweaks — makes the host visibly non-stock.
# Usage: ./scripts/vixzen-login-boot.sh --apply | --revert
# Tweaks (user, no sudo, instant) always run.
# Login (GDM) + boot (Plymouth) need sudo and a logout/reboot to see.
HERE="$(cd "$(dirname "$0")/.." && pwd)"
MODE="${1:---apply}"

tweaks_apply() {
  # Windows-familiar window buttons (minimize added), centered windows.
  gsettings set org.gnome.desktop.wm.preferences button-layout 'appmenu:minimize,close' 2>/dev/null || true
  gsettings set org.gnome.mutter center-new-windows true 2>/dev/null || true
  # Vixzen pins already present; ensure wallpaper is our signature.
  WP="$HERE/assets/wallpapers/vixzen-signature-1920x1080.png"
  [ -f "$WP" ] && {
    gsettings set org.gnome.desktop.background picture-uri "file://$WP" 2>/dev/null || true
    gsettings set org.gnome.desktop.background picture-uri-dark "file://$WP" 2>/dev/null || true
  }
  echo "Tweaks applied (live, no logout)."
}

tweaks_revert() {
  gsettings set org.gnome.desktop.wm.preferences button-layout 'appmenu:close' 2>/dev/null || true
  echo "Tweaks reverted (wallpaper left as-is; change it in Settings)."
}

login_apply() {
  # GDM login screen: signature wallpaper behind the password prompt.
  # Backup first; recompile gresource. Needs logout to see.
  [ "$(id -u)" -ne 0 ] && { echo "[NEED SUDO] login theme: sudo $0 --apply"; return 1; }
  G=/usr/share/gnome-shell/gnome-shell-theme.gresource
  [ -f "$G.stock" ] || cp "$G" "$G.stock"
  T=$(mktemp -d)
  for f in $(gresource list "$G"); do
    d="$T/theme/$(dirname "$f")"; mkdir -p "$d"
    gresource extract "$G" "$f" > "$T/theme/$f"
  done
  cp "$HERE/assets/wallpapers/vixzen-burst-1920x1080.png" "$T/theme/org/gnome/shell/theme/vixzen-login.png"
  cp "$HERE/assets/branding/logo.svg" "$T/theme/org/gnome/shell/theme/vixzen-logo.svg" 2>/dev/null || true
  cat >> "$T/theme/org/gnome/shell/theme/gnome-shell-dark.css" <<'CSSEOF'
/* --- Vixzen login identity (selectors verified against GNOME 50 theme) --- */
#lockDialogGroup { background-image: url("vixzen-login.png"); background-size: cover; background-color: #02040E; }
.login-dialog { background-color: rgba(10,12,20,0.35); border-radius: 24px; }
.login-dialog .user-icon { border: 3px solid #7C7CFF; box-shadow: 0 0 22px rgba(124,124,255,0.6); }
.login-dialog-prompt-entry { border-radius: 14px; border: 1px solid #2E3448; background-color: rgba(27,30,42,0.92); color: #E8EAF2; padding: 10px 16px; font-size: 15px; }
.login-dialog-prompt-entry:focus { border: 1px solid #7C7CFF; box-shadow: 0 0 18px rgba(124,124,255,0.55); }
.login-dialog-button { border-radius: 12px; padding: 8px 26px; font-weight: bold; background-color: #4F46E5; color: #FFFFFF; }
.login-dialog-message-warning { color: #FB923C; }
CSSEOF
  cat >> "$T/theme/org/gnome/shell/theme/gnome-shell-light.css" <<'CSSEOF'
/* --- Vixzen login identity (selectors verified against GNOME 50 theme) --- */
#lockDialogGroup { background-image: url("vixzen-login.png"); background-size: cover; background-color: #02040E; }
.login-dialog { background-color: rgba(10,12,20,0.35); border-radius: 24px; }
.login-dialog .user-icon { border: 3px solid #7C7CFF; box-shadow: 0 0 22px rgba(124,124,255,0.6); }
.login-dialog-prompt-entry { border-radius: 14px; border: 1px solid #2E3448; background-color: rgba(27,30,42,0.92); color: #E8EAF2; padding: 10px 16px; font-size: 15px; }
.login-dialog-prompt-entry:focus { border: 1px solid #7C7CFF; box-shadow: 0 0 18px rgba(124,124,255,0.55); }
.login-dialog-button { border-radius: 12px; padding: 8px 26px; font-weight: bold; background-color: #4F46E5; color: #FFFFFF; }
.login-dialog-message-warning { color: #FB923C; }
CSSEOF
  cat > "$T/vixzen-theme.gresource.xml" <<'XMLEOF'
<?xml version="1.0" encoding="UTF-8"?>
<gresources><gresource prefix="/org/gnome/shell/theme">
<file>calendar-today-light.svg</file><file>calendar-today.svg</file>
<file>gnome-shell-dark.css</file><file>gnome-shell-high-contrast.css</file>
<file>gnome-shell-light.css</file><file>gnome-shell-start.svg</file>
<file>pad-osd.css</file><file>workspace-placeholder.svg</file>
<file>vixzen-login.png</file><file>vixzen-logo.svg</file>
</gresource></gresources>
XMLEOF
  if glib-compile-resources --sourcedir="$T/theme/org/gnome/shell/theme" "$T/vixzen-theme.gresource.xml" --target="$T/vixzen-shell-theme.gresource"; then
    cp "$T/vixzen-shell-theme.gresource" "$G"
    echo "Login theme applied (log out to see). Backup: $G.stock"
  else
    echo "[FAIL] gresource compile failed, original untouched."
    rm -rf "$T"; return 1
  fi
  rm -rf "$T"
}

login_revert() {
  [ "$(id -u)" -ne 0 ] && { echo "[NEED SUDO] login revert: sudo $0 --revert"; return 1; }
  G=/usr/share/gnome-shell/gnome-shell-theme.gresource
  [ -f "$G.stock" ] && cp "$G.stock" "$G" && echo "Login theme reverted (log out to see)." \
    || echo "No backup found, nothing to revert."
}

boot_apply() {
  # Plymouth boot splash: Vixzen spinner + logo watermark. Needs reboot to see.
  [ "$(id -u)" -ne 0 ] && { echo "[NEED SUDO] boot splash: sudo $0 --apply"; return 1; }
  rm -rf /usr/share/plymouth/themes/vixzen
  cp -r /usr/share/plymouth/themes/spinner /usr/share/plymouth/themes/vixzen
  mv /usr/share/plymouth/themes/vixzen/spinner.plymouth /usr/share/plymouth/themes/vixzen/vixzen.plymouth
  cp "$HERE/assets/boot/logo.png" /usr/share/plymouth/themes/vixzen/watermark.png 2>/dev/null || true
  cp "$HERE"/assets/boot/frames/animation-*.png "$HERE"/assets/boot/frames/throbber-*.png \
     /usr/share/plymouth/themes/vixzen/ 2>/dev/null || echo "[WARN] boot frames missing, spinner animation kept"
  sed -i 's|^ImageDir=.*|ImageDir=/usr/share/plymouth/themes/vixzen|; s/^BackgroundStartColor=.*/BackgroundStartColor=0x1E1B4B/; s/^BackgroundEndColor=.*/BackgroundEndColor=0x02040E/; s/^ProgressBarBackgroundColor=.*/ProgressBarBackgroundColor=0x2E3448/; s/^ProgressBarForegroundColor=.*/ProgressBarForegroundColor=0x7C7CFF/' \
    /usr/share/plymouth/themes/vixzen/vixzen.plymouth
  grep -q '^Title=' /usr/share/plymouth/themes/vixzen/vixzen.plymouth \
    || echo 'Title=VixzenOS' >> /usr/share/plymouth/themes/vixzen/vixzen.plymouth
  sed -i 's/^Name=.*/Name=Vixzen/; s/^Description=.*/Description=VixzenOS boot splash/' /usr/share/plymouth/themes/vixzen/vixzen.plymouth
  plymouth-set-default-theme -R vixzen && echo "Boot splash applied (reboot to see)."
}

boot_revert() {
  [ "$(id -u)" -ne 0 ] && { echo "[NEED SUDO] boot revert: sudo $0 --revert"; return 1; }
  plymouth-set-default-theme -R spinner && rm -rf /usr/share/plymouth/themes/vixzen \
    && echo "Boot splash reverted to spinner."
}

case "$MODE" in
  --apply) tweaks_apply; login_apply; boot_apply ;;
  --revert) tweaks_revert; login_revert; boot_revert ;;
  --tweaks) tweaks_apply ;;
  *) echo "Usage: $0 --apply | --revert | --tweaks"; exit 2 ;;
esac
