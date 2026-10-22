# VixzenOS Edu kickstart — classroom edition (internet kill-switch + locked
# Software store for non-admins). Same desktop as personal; adds student
# account (no admin rights) + Edu lockdown payload. Admin password is set at
# deploy time (passwd student / passwd <admin>); live demo uses liveuser.
# Build: VXZ_KS=packaging/vixzenos-edu.ks sudo -E ./build-vixzenos.sh ./build/boot.iso
# (Needs the same build/boot.iso alongside)
#version=F44
# --- Installer plumbing (live image skeleton; branding lives in %post) ---
bootloader --timeout=5
zerombr
clearpart --all --initlabel
part biosboot --fstype="biosboot" --size=1
part / --fstype="ext4" --size=12288 --grow
keyboard --xlayouts='us'
lang en_US.UTF-8
timezone UTC
xconfig --startxonboot
network --bootproto=dhcp --device=link --activate
rootpw --lock
user --name=liveuser --groups=wheel --homedir=/home/liveuser
# Student: deliberately NOT in wheel, so Edu polkit rules (network +
# PackageKit admin-only) apply. Password locked until the school sets it.
user --name=student --homedir=/home/student
firewall --enabled --service=mdns
selinux --enforcing
services --enabled=NetworkManager
shutdown
%packages
@workstation-product-environment
kernel
kernel-modules
dracut-live
livesys-scripts
plymouth
plymouth-system-theme
grub2-pc
grub2-pc-modules
grub2-efi-x64
grub2-efi-x64-modules
grub2-efi-x64-cdboot
shim-x64
curl
unzip
gtk4
libadwaita
python3-gobject
glib2-devel
gnome-shell-extension-dash-to-dock
gnome-shell-extension-user-theme
gnome-shell-extension-blur-my-shell
qemu-guest-agent
cool-retro-term
fastfetch
cava
cmatrix
%end

%post --nochroot
# Legacy host-side delivery (works with --no-virt; with VM install the
# chroot %post below fetches via HTTP instead — see build-vixzenos.sh).
cp -a /tmp/vixzen-stage "$INSTALL_ROOT/tmp/vixzen-stage" 2>/dev/null \
  || echo "VIXZEN: no host stage payload (HTTP fetch expected in chroot %post)"
%end

%post
# --- Stage fetch: VM install cannot see host /tmp, so build-vixzenos.sh
# serves /tmp/vixzen-stage.tar.gz on host port 8008 (10.0.2.2 from guest).
# --nochroot above may already have placed it; try HTTP only if missing. ---
if [ ! -f /tmp/vixzen-stage/preview/vixzen_preview.py ]; then
  mkdir -p /tmp/vixzen-stage
  ( curl -s --max-time 30 http://10.0.2.2:8008/vixzen-stage.tar.gz -o /tmp/vs.tgz \
    || wget -q -T 30 -O /tmp/vs.tgz http://10.0.2.2:8008/vixzen-stage.tar.gz \
    || python3 -c "import urllib.request; urllib.request.urlretrieve('http://10.0.2.2:8008/vixzen-stage.tar.gz','/tmp/vs.tgz')" ) 2>/dev/null
  [ -f /tmp/vs.tgz ] && tar -xzf /tmp/vs.tgz -C /tmp/ 2>/dev/null && echo "VIXZEN: stage fetched via HTTP" \
    || echo "VIXZEN WARN: stage fetch failed (ISO will be vanilla Fedora live, still bootable)"
fi
# --- Vixzen apps + branding (all inside the ISO image, never touches the host) ---
mkdir -p /usr/share/vixzen/{preview,files,settings,power} /usr/share/vixzen-branding
cp /tmp/vixzen-stage/preview/* /usr/share/vixzen/preview/ 2>/dev/null || true
cp /tmp/vixzen-stage/files/* /usr/share/vixzen/files/ 2>/dev/null || true
cp /tmp/vixzen-stage/settings/* /usr/share/vixzen/settings/ 2>/dev/null || true
cp /tmp/vixzen-stage/power/* /usr/share/vixzen/power/ 2>/dev/null || true
cp /tmp/vixzen-stage/*.svg /usr/share/vixzen-branding/ 2>/dev/null || true
mkdir -p /boot/vixzen /boot/vixzen/frames
cp /tmp/vixzen-stage/boot/* /boot/vixzen/ 2>/dev/null || true
cp /tmp/vixzen-stage/boot/frames/*.png /boot/vixzen/frames/ 2>/dev/null || true
mkdir -p /usr/share/backgrounds/vixzen
cp /tmp/vixzen-stage/wallpapers/* /usr/share/backgrounds/vixzen/ 2>/dev/null || true
# --- UEFI boot files (lorax needs boot/efi/EFI/*/gcdx64.efi or it skips
# EFI/BOOT + efiboot.img entirely, then xorrisofs fails. The cdboot RPM
# above provides gcdx64.efi natively; this block is belt-and-braces for
# the BIOS install VM where /boot/efi may start empty) ---
mkdir -p /boot/efi/EFI/fedora /boot/efi/EFI/vixzen
for f in shimx64.efi mmx64.efi; do
  [ -f "/boot/efi/EFI/fedora/$f" ] || cp /usr/lib/efi/shim/*/EFI/fedora/$f /boot/efi/EFI/fedora/$f 2>/dev/null || true
done
[ -f /boot/efi/EFI/fedora/gcdx64.efi ] || cp /usr/lib/efi/grub2/*/EFI/fedora/gcdx64.efi /boot/efi/EFI/fedora/gcdx64.efi 2>/dev/null || true
[ -f /boot/efi/EFI/fedora/grubx64.efi ] || cp /usr/lib/efi/grub2/*/EFI/fedora/grubx64.efi /boot/efi/EFI/fedora/grubx64.efi 2>/dev/null || true
for f in shimx64.efi mmx64.efi gcdx64.efi grubx64.efi; do
  cp /boot/efi/EFI/fedora/$f /boot/efi/EFI/vixzen/$f 2>/dev/null || true
done
echo "VIXZEN EFI seed:"; ls -l /boot/efi/EFI/fedora/ /boot/efi/EFI/vixzen/ 2>&1 || true
# Lorax sees ONLY the root partition (any EFI partition is never mounted on
# host), so duplicate the same files onto the root fs. With no separate EFI
# partition /boot/efi is already a root-fs dir; with one, umount briefly,
# write to the underlying dir, remount. Either way inroot ends up with
# boot/efi/EFI/fedora/gcdx64.efi -> efi.tmpl runs -> EFI/BOOT + efiboot.img.
if mountpoint -q /boot/efi && umount /boot/efi 2>/dev/null; then
  HAVE_EFI_PART=1
else
  HAVE_EFI_PART=0
fi
if [ "$HAVE_EFI_PART" = 1 ]; then
  mkdir -p /boot/efi/EFI/fedora /boot/efi/EFI/vixzen
  for f in shimx64.efi mmx64.efi; do
    cp /usr/lib/efi/shim/*/EFI/fedora/$f /boot/efi/EFI/fedora/$f 2>/dev/null || true
  done
  cp /usr/lib/efi/grub2/*/EFI/fedora/gcdx64.efi /boot/efi/EFI/fedora/gcdx64.efi 2>/dev/null || true
  cp /usr/lib/efi/grub2/*/EFI/fedora/grubx64.efi /boot/efi/EFI/fedora/grubx64.efi 2>/dev/null || true
  for f in shimx64.efi mmx64.efi gcdx64.efi grubx64.efi; do
    cp /boot/efi/EFI/fedora/$f /boot/efi/EFI/vixzen/$f 2>/dev/null || true
  done
  echo "VIXZEN EFI rootfs copy:"; ls -l /boot/efi/EFI/fedora/ 2>&1 || true
  mount /boot/efi 2>/dev/null || mount -a 2>/dev/null || true
else
  echo "VIXZEN EFI rootfs: no separate EFI partition, files already on root fs" || true
  ls -l /boot/efi/EFI/fedora/ 2>&1 || true
fi
# --- Live-boot fstab: build-VM disk UUIDs are dead at live boot (the ISO
# boots on other machines/USBs). Dead entries cost 45s device waits each,
# then boot-efi.mount + local-fs.target fail -> emergency mode with a locked
# root. Target installs regenerate fstab, so neutralizing here is safe. ---
sed -i 's|^UUID=|#LIVE-OFF UUID=|' /etc/fstab 2>/dev/null || true
grep -q 'vixzen-live' /etc/fstab 2>/dev/null \
  || echo '# vixzen-live: build-VM UUID entries disabled for live boot' >> /etc/fstab
# --- Live autologin (else the greeter strands you: liveuser has no password
# and root is locked). Target installs set their own users; this is live-only.
mkdir -p /etc/gdm
cat >> /etc/gdm/custom.conf <<'EOF'
[daemon]
AutomaticLoginEnable=True
AutomaticLogin=liveuser
EOF
# --- Vixzen Command Center: real `vix` CLI on PATH ---
mkdir -p /usr/share/vixzen/cmd
cp /tmp/vixzen-stage/cmd/vix /usr/share/vixzen/cmd/vix 2>/dev/null || true
cp -a /tmp/vixzen-stage/cmd/vixcmd /usr/share/vixzen/cmd/vixcmd 2>/dev/null || true
chmod 755 /usr/share/vixzen/cmd/vix 2>/dev/null || true
ln -sf /usr/share/vixzen/cmd/vix /usr/local/bin/vix 2>/dev/null || true
# --- shared core (vixzen_core) for the Vixzen apps ---
mkdir -p /usr/lib/python3.14/site-packages/vixzen_core
cp /tmp/vixzen-stage/core/*.py /usr/lib/python3.14/site-packages/vixzen_core/ 2>/dev/null || true
# --- vixzen-update (M7): refresh payload from bundles, with backup ---
cp /tmp/vixzen-stage/update/vixzen-update.sh /usr/local/bin/vixzen-update 2>/dev/null || true
chmod 755 /usr/local/bin/vixzen-update 2>/dev/null || true
# --- Vixzen Shell: the one-piece bar + attached menu, in-built ---
mkdir -p /usr/share/gnome-shell/extensions/vixzen-shell@vixzen.os
cp /tmp/vixzen-stage/shell/extension.js /tmp/vixzen-stage/shell/metadata.json \
   /usr/share/gnome-shell/extensions/vixzen-shell@vixzen.os/ 2>/dev/null || true
chmod 644 /usr/share/gnome-shell/extensions/vixzen-shell@vixzen.os/* 2>/dev/null || true
# --- Vixzen Widgets (top-bar weather + headlines) ---
if [ -d /tmp/vixzen-stage/widgets ]; then
  mkdir -p /usr/share/gnome-shell/extensions/vixzen-widgets@vixzen.os
  cp /tmp/vixzen-stage/widgets/* /usr/share/gnome-shell/extensions/vixzen-widgets@vixzen.os/ 2>/dev/null || true
  chmod 644 /usr/share/gnome-shell/extensions/vixzen-widgets@vixzen.os/* 2>/dev/null || true
  echo "VIXZEN: vixzen-widgets installed"
fi
# --- Vendored shell extensions: Hide Top Bar + Desktop Cube + Compiz
# windows effect + Magic Lamp (all GNOME 50 builds, licenses in zips) ---
for spec in "hidetopbar-126-gnome50.zip|hidetopbar@mathieu.bidon.ca" "desktop-cube-35-gnome50.zip|desktop-cube@schneegans.github.com" "compiz-windows-effect-33-gnome50.zip|compiz-windows-effect@hermes83.github.com" "compiz-magic-lamp-25-gnome50.zip|compiz-alike-magic-lamp-effect@hermes83.github.com" "magnific-launcher-2-gnome50.zip|magnific-launcher@gilsonf" "burn-my-windows-49-gnome50.zip|burn-my-windows@schneegans.github.com" "flypie-33-gnome50.zip|flypie@schneegans.github.com" "paperwm-148-gnome50.zip|paperwm@paperwm.github.com" "rounded-corners-25-gnome50.zip|rounded-window-corners@fxgn" "logomenu-45-gnome50.zip|logomenu@aryan_k" "clipboard-71-gnome50.zip|clipboard-indicator@tudmotu.com" "caffeine-61-gnome50.zip|caffeine@patapon.info" "astra-monitor-62-gnome50.zip|monitor@astraext.github.io" "ding-100-gnome50.zip|ding@rastersoft.com" "wallpaper-engine-9-gnome50.zip|gnome-wallpaper-engine@gjs.com" "gsconnect-74-gnome50.zip|gsconnect@andyholmes.github.io"; do
  zip="/tmp/vixzen-stage/shell/${spec%%|*}"
  uuid="${spec##*|}"
  [ -f "$zip" ] || { echo "VIXZEN WARN: missing $zip"; continue; }
  rm -rf "/usr/share/gnome-shell/extensions/$uuid"
  mkdir -p "/usr/share/gnome-shell/extensions/$uuid"
  ( unzip -q -o "$zip" -d "/usr/share/gnome-shell/extensions/$uuid" \
    && { [ -d "/usr/share/gnome-shell/extensions/$uuid/schemas" ] \
      && glib-compile-schemas "/usr/share/gnome-shell/extensions/$uuid/schemas/"; } \
    && chmod -R a+r "/usr/share/gnome-shell/extensions/$uuid" \
    && echo "VIXZEN: $uuid installed" ) 2>/dev/null \
    || echo "VIXZEN WARN: $uuid install failed (session still boots)"
done
# Default session: Vixzen bar ON (our icons/theme/wallpaper follow)
mkdir -p /etc/dconf/db/local.d
cat > /etc/dconf/db/local.d/00-vixzen <<'EOF'
[org/gnome/shell]
enabled-extensions=['blur-my-shell@aunetx', 'burn-my-windows@schneegans.github.com', 'caffeine@patapon.info', 'clipboard-indicator@tudmotu.com', 'compiz-alike-magic-lamp-effect@hermes83.github.com', 'compiz-windows-effect@hermes83.github.com', 'dash-to-dock@micxgx.gmail.com', 'desktop-cube@schneegans.github.com', 'ding@rastersoft.com', 'flypie@schneegans.github.com', 'gnome-wallpaper-engine@gjs.com', 'gsconnect@andyholmes.github.io', 'logomenu@aryan_k', 'magnific-launcher@gilsonf', 'monitor@astraext.github.io', 'rounded-window-corners@fxgn', 'user-theme@gnome-shell-extensions.gcampax.github.com', 'vixzen-widgets@vixzen.os']', 'rounded-window-corners@fxgn', 'user-theme@gnome-shell-extensions.gcampax.github.com', 'vixzen-widgets@vixzen.os']
[org/gnome/shell/extensions/logo-menu]
use-custom-icon=true
custom-icon-path='/usr/share/vixzen-branding/logo.svg'
menu-button-icon-size=20
favorite-apps=['vixzen-menu.desktop', 'vixzen-search.desktop', 'org.mozilla.firefox.desktop', 'org.gnome.Nautilus.desktop', 'org.gnome.Software.desktop', 'org.gnome.TextEditor.desktop', 'org.gnome.Calculator.desktop']
[org/gnome/desktop/wm/preferences]
button-layout='appmenu:minimize,close'
[org/gnome/mutter]
center-new-windows=true
[org/gnome/settings-daemon/plugins/media-keys]
custom-keybindings=['/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/vixzen-files/', '/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/vixzen-terminal/']
[org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/vixzen-files]
name='Vixzen Files'
command='nautilus'
binding='<Super>e'
[org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/vixzen-terminal]
name='Vixzen Terminal'
command='ptyxis'
binding='<Super>t'
[org/gnome/shell/extensions/dash-to-dock]
# Main taskbar: compact centered dock (macOS-style), dark, minimize-on-click.
# vixzen-shell stays installed but off — enable it instead if you ever want
# the Vixzen bar + Start Menu rather than this dock.
background-color='#1B1E2A'
custom-background-color=true
background-opacity=0.92
click-action='minimize'
running-indicator-style='DOTS'
extend-height=false
always-center-icons=true
autohide=false
intellihide=false
dock-fixed=true
show-windows-preview=true
[org/gnome/shell/extensions/user-theme]
name='Vixzen'
[org/gnome/desktop/interface]
icon-theme='Vixzen'
accent-color='purple'
color-scheme='prefer-dark'
cursor-theme='WhiteSur-cursors'
font-name='Cantarell 11'
document-font-name='Cantarell 12'
clock-show-weekday=true
[org/gnome/login-screen]
logo='/usr/share/vixzen-branding/logo.svg'
[org/gnome/desktop/background]
picture-uri='file:///usr/share/backgrounds/vixzen/vixzen-burst-1920x1080.png'
picture-uri-dark='file:///usr/share/backgrounds/vixzen/vixzen-burst-1920x1080.png'
EOF
dconf update 2>/dev/null || true
cat > /usr/share/applications/os.vixzen.preview.desktop <<'EOF'
[Desktop Entry]
Name=Vixzen Preview
Exec=python3 /usr/share/vixzen/preview/vixzen_preview.py
Icon=/usr/share/vixzen-branding/logo.svg
Type=Application
Categories=System;
EOF
cat > /usr/share/applications/os.vixzen.files.desktop <<'EOF'
[Desktop Entry]
Name=Vixzen Files
Exec=python3 /usr/share/vixzen/files/vixzen_files.py
Icon=org.gnome.Nautilus
Type=Application
Categories=System;FileManager;
EOF
cat > /usr/share/applications/vixzen-menu.desktop <<'EOF'
[Desktop Entry]
Name=Vixzen
Comment=VixzenOS start menu and power
Exec=python3 /usr/share/vixzen/power/vixzen_power.py
Icon=/usr/share/vixzen-branding/logo.svg
Type=Application
Categories=System;
EOF
cat > /usr/share/applications/vixzen-search.desktop <<'EOF'
[Desktop Entry]
Name=Vixzen Search
Comment=Search apps, settings and files
Exec=python3 /usr/share/vixzen/power/vixzen_power.py
Icon=/usr/share/vixzen-branding/vixzen-search.svg
Type=Application
Categories=System;
EOF
cat > /usr/share/applications/os.vixzen.settings.desktop <<'EOF'
[Desktop Entry]
Name=Vixzen Settings
Exec=python3 /usr/share/vixzen/settings/vixzen_settings.py
Icon=org.gnome.Settings
Type=Application
Categories=System;Settings;
EOF
# --- Vixzen look, installed (icons + shell theme the dconf block points at) ---
mkdir -p /usr/share/icons /usr/share/themes/Vixzen/gnome-shell
cp -a /tmp/vixzen-stage/icons/Vixzen /usr/share/icons/ 2>/dev/null || true
cp /tmp/vixzen-stage/gtheme/gnome-shell.css /usr/share/themes/Vixzen/gnome-shell/ 2>/dev/null || true
gtk-update-icon-cache -f /usr/share/icons/Vixzen/ 2>/dev/null || true
# --- WhiteSur look bundle (GTK theme + icon set + macOS wallpapers) ---
if [ -d /tmp/vixzen-stage/looks ]; then
  mkdir -p /usr/share/themes /usr/share/icons /usr/share/backgrounds/vixzen
  cp -a /tmp/vixzen-stage/looks/WhiteSur-Dark-blue /usr/share/themes/ 2>/dev/null || true
  cp -a /tmp/vixzen-stage/looks/WhiteSur-dark /usr/share/icons/ 2>/dev/null || true
  cp -a /tmp/vixzen-stage/looks/whitesur/. /usr/share/backgrounds/vixzen/ 2>/dev/null || true
  gtk-update-icon-cache -f /usr/share/icons/WhiteSur-dark/ 2>/dev/null || true
  echo "VIXZEN: WhiteSur theme + icons + wallpapers installed"
fi
# --- WhiteSur cursors (vendored, gist recipe) ---
# NOTE: installed as WhiteSur-cursors (NOT WhiteSur/) — the WhiteSur *icon*
# theme owns that folder name and would silently overwrite the cursors.
mkdir -p /tmp/vixzen-cursors-work && cp -a /tmp/vixzen-stage/cursors/WhiteSur /tmp/vixzen-cursors-work/WhiteSur-cursors 2>/dev/null || true
cp -a /tmp/vixzen-cursors-work/WhiteSur-cursors /usr/share/icons/ 2>/dev/null || true
# --- Vixzen GTK rework for native apps (Files, Settings, Software) ---
for d in /etc/skel/.config/gtk-4.0 /home/liveuser/.config/gtk-4.0; do
  mkdir -p "$d"
  # Dark sheet in both: only gtk.css is loaded even in dark mode (measured).
  cp /tmp/vixzen-stage/gtk/vixzen-gtk-dark.css "$d/gtk.css" 2>/dev/null || true
  cp /tmp/vixzen-stage/gtk/vixzen-gtk-dark.css "$d/gtk-dark.css" 2>/dev/null || true
done
chown -R liveuser:liveuser /home/liveuser/.config/gtk-4.0 2>/dev/null || true
# --- OS identity: NOTHING of Fedora visible. ID stays 'fedora' on purpose
# (third-party repos and tools key off it); every human-visible field says
# VixzenOS. Standard remix practice. ---
echo "vixzen" > /etc/hostname
cat > /etc/vixzen-release <<'EOF'
NAME="VixzenOS"
VERSION="0.3 (Preview)"
ID=vixzenos
PRETTY_NAME="VixzenOS 0.3 (Preview, Fedora-based)"
ANSI_COLOR="0;38;2;79;70;229"
LOGO=vixzen-logo
EOF
sed -i 's/^NAME.*/NAME="VixzenOS"/' /etc/os-release
sed -i 's/^PRETTY_NAME=.*/PRETTY_NAME="VixzenOS 0.3 (Preview)"/' /etc/os-release
sed -i 's/^VARIANT=.*/VARIANT="VixzenOS"/' /etc/os-release
sed -i 's/^VERSION=.*/VERSION="0.3 (Preview)"/' /etc/os-release
sed -i 's/^ANSI_COLOR=.*/ANSI_COLOR="0;38;2;79;70;229"/' /etc/os-release
echo "VixzenOS release 0.3 (Preview)" > /etc/system-release
# --- Silent boot: no kernel text scroll, no Fedora Plymouth ---
if [ -d /usr/share/plymouth/themes/spinner ]; then
  rm -rf /usr/share/plymouth/themes/vixzen
  cp -r /usr/share/plymouth/themes/spinner /usr/share/plymouth/themes/vixzen
  mv /usr/share/plymouth/themes/vixzen/spinner.plymouth \
     /usr/share/plymouth/themes/vixzen/vixzen.plymouth 2>/dev/null || true
  cp /boot/vixzen/logo.png /usr/share/plymouth/themes/vixzen/watermark.png 2>/dev/null || true
  cp /boot/vixzen/frames/animation-*.png /boot/vixzen/frames/throbber-*.png \
     /usr/share/plymouth/themes/vixzen/ 2>/dev/null || true
  sed -i 's|^ImageDir=.*|ImageDir=/usr/share/plymouth/themes/vixzen|; s/^BackgroundStartColor=.*/BackgroundStartColor=0x02040E/; s/^BackgroundEndColor=.*/BackgroundEndColor=0x02040E/; s/^ProgressBarBackgroundColor=.*/ProgressBarBackgroundColor=0x1B1E2A/; s/^ProgressBarForegroundColor=.*/ProgressBarForegroundColor=0x7C7CFF/; s/^Transition=.*/Transition=fade/' \
    /usr/share/plymouth/themes/vixzen/vixzen.plymouth 2>/dev/null || true
  grep -q '^TransitionDuration=' /usr/share/plymouth/themes/vixzen/vixzen.plymouth 2>/dev/null \
    || echo 'TransitionDuration=0.5' >> /usr/share/plymouth/themes/vixzen/vixzen.plymouth
    /usr/share/plymouth/themes/vixzen/vixzen.plymouth 2>/dev/null || true
  grep -q '^Title=' /usr/share/plymouth/themes/vixzen/vixzen.plymouth 2>/dev/null \
    || echo 'Title=VixzenOS' >> /usr/share/plymouth/themes/vixzen/vixzen.plymouth
  sed -i 's/^Name=.*/Name=Vixzen/; s/^Description=.*/Description=VixzenOS boot splash/' \
    /usr/share/plymouth/themes/vixzen/vixzen.plymouth 2>/dev/null || true
  plymouth-set-default-theme -R vixzen 2>/dev/null || plymouth-set-default-theme vixzen 2>/dev/null || true
fi
# --- De-Fedora scrub (same as personal edition) ---
if [ -f /tmp/vixzen-stage/de-fedora.sh ]; then
  bash /tmp/vixzen-stage/de-fedora.sh 2>&1 | sed 's/^/  /' || true
fi
if grep -q GRUB_CMDLINE_LINUX /etc/default/grub; then
  sed -i 's/^GRUB_CMDLINE_LINUX=.*/GRUB_CMDLINE_LINUX="rhgb quiet loglevel=3 systemd.show_status=false"/' /etc/default/grub
fi
cat > /etc/motd <<'EOF'
  __   ___  ___ ____ ___ _  _  ___  ___
  \ \ / / \/ /_ /_  / __| \ | |/ _ \/ __|
   \ V / |>  < / / |  _|  \| |  __/\__ \
    \_/ /_/\_\_/___|_| |_|\__|\___||___/
   VixzenOS 0.3 (Preview) — lightweight, graphical, yours.
EOF
# --- Boot menu branding: "VixzenOS" entries + logo wallpaper behind GRUB ---
if [ -f /boot/vixzen/background.png ]; then
  mkdir -p /boot/grub2
  cp /boot/vixzen/background.png /boot/grub2/vixzen-background.png
  grep -q GRUB_BACKGROUND /etc/default/grub \
    && sed -i 's|^GRUB_BACKGROUND=.*|GRUB_BACKGROUND="/boot/grub2/vixzen-background.png"|' /etc/default/grub \
    || echo 'GRUB_BACKGROUND="/boot/grub2/vixzen-background.png"' >> /etc/default/grub
fi
grep -q GRUB_DISTRIBUTOR /etc/default/grub \
  && sed -i 's/^GRUB_DISTRIBUTOR=.*/GRUB_DISTRIBUTOR="VixzenOS"/' /etc/default/grub \
  || echo 'GRUB_DISTRIBUTOR="VixzenOS"' >> /etc/default/grub
# --- Login screen theme (proven host recipe: extract, brand, recompile) ---
if command -v glib-compile-resources >/dev/null && command -v gresource >/dev/null; then
  T=/tmp/vixzen-gdm
  rm -rf "$T" && mkdir -p "$T/theme"
  for f in $(gresource list /usr/share/gnome-shell/gnome-shell-theme.gresource); do
    d="$T/theme/$(dirname "$f")"; mkdir -p "$d"
    gresource extract /usr/share/gnome-shell/gnome-shell-theme.gresource "$f" > "$T/theme/$f"
  done
  cp /usr/share/backgrounds/vixzen/vixzen-burst-1920x1080.png \
     "$T/theme/org/gnome/shell/theme/vixzen-login.png" 2>/dev/null || true
  cp /usr/share/vixzen-branding/logo.svg \
     "$T/theme/org/gnome/shell/theme/vixzen-logo.svg" 2>/dev/null || true
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
  if glib-compile-resources --sourcedir="$T/theme/org/gnome/shell/theme" \
       "$T/vixzen-theme.gresource.xml" --target="$T/vixzen-shell-theme.gresource" 2>/dev/null; then
    cp /usr/share/gnome-shell/gnome-shell-theme.gresource \
       /usr/share/gnome-shell/gnome-shell-theme.gresource.stock
    cp "$T/vixzen-shell-theme.gresource" /usr/share/gnome-shell/gnome-shell-theme.gresource
  fi
  rm -rf "$T"
fi
# --- Edu lockdown: admin helper (root-owned so students can't edit it),
# network control rule always-on, store rule shipped dormant until locked ---
install -m 755 /tmp/vixzen-stage/edu/vixzen-edu-admin.sh /usr/libexec/vixzen-edu-admin 2>/dev/null || true
mkdir -p /usr/share/vixzen-edu /usr/share/polkit-1/rules.d
cp /tmp/vixzen-stage/edu/49-vixzen-edu-store.rules /usr/share/vixzen-edu/ 2>/dev/null || true
cp /tmp/vixzen-stage/edu/49-vixzen-edu-network.rules /usr/share/polkit-1/rules.d/ 2>/dev/null || true
chmod 644 /usr/share/vixzen-edu/* /usr/share/polkit-1/rules.d/49-vixzen-edu-*.rules 2>/dev/null || true
echo "VIXZEN EDU payload installed" || true
%end
