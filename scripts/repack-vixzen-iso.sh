#!/bin/bash
# Repack the VixzenOS live image into a bootable ISO.
#
# One-shot, unattended. Run with sudo:
#   sudo ./scripts/repack-vixzen-iso.sh
#
# Steps:
#   1. restore SELinux labels INSIDE the tree (chroot) — without this the
#      image boots to a splash and hangs (systemd cannot set contexts).
#   2. verify the labels are correct now
#   3. repack the squashfs (2 threads / 1 GB so it stays light)
#   4. assemble the ISO and implant the md5 checksum
#   5. leave the finished ISO in vixzen-surgery/
set -u
SURG=/home/shonshyjo/Documents/vixzen-surgery
TREE=$SURG/vixroot
ISO=$SURG/VixzenOS-0.3-full-x86_64.iso
LOG=$SURG/repack.log
TREEISO=$SURG/isotree

log(){ echo "[$(date +%H:%M:%S)] $*"; }
: > "$LOG"
say(){ log "$*" | tee -a "$LOG"; }

[ "$(id -u)" -eq 0 ] || { echo "Run with sudo."; exit 1; }
[ -d "$TREE" ] || { echo "Missing tree $TREE"; exit 1; }

say "STEP 1/5 restoring SELinux labels (setfiles with -r alt-root)"
# setfiles -r maps the tree's real paths (/etc, /usr, ...) onto the label
# database. The host policy (policy.35) matches the tree's, so the computed
# labels are exactly the ones the installer would have written.
# NOTE: run this with -r, NOT via chroot — a chrooted restorecon silently
# no-ops here, which is what left the tree labelled user_home_t and the
# system hanging on the splash.
SPEC=/etc/selinux/targeted/contexts/files/file_contexts
setfiles -F -r "$TREE" "$SPEC" /etc /usr /var /root /home /boot /opt >>"$LOG" 2>&1
say "  setfiles done"

say "STEP 2/5 verifying labels"
chk=$(getfattr -n security.selinux --only-values "$TREE/etc/fstab" 2>/dev/null | tr -d '\0')
echo "    etc/fstab label: $chk" >>"$LOG"
case "$chk" in
  *etc_t*) say "  label OK (etc_t)" ;;
  *) say "  ERROR: label is '$chk' (expected etc_t) — aborting before packing"; exit 1 ;;
esac
chk2=$(getfattr -n security.selinux --only-values "$TREE/usr/lib/systemd/systemd" 2>/dev/null | tr -d '\0')
echo "    systemd label: $chk2" >>"$LOG"
case "$chk2" in
  *init_exec_t*) say "  systemd label OK (init_exec_t)" ;;
  *) say "  WARNING: systemd label is '$chk2'" ;;
esac

say "STEP 3/5 repacking squashfs (2 threads, 1G mem — takes ~25-40 min)"
rm -f "$SURG/squashfs.new"
nice -n 10 mksquashfs "$TREE" "$SURG/squashfs.new" -comp xz -b 131072 -noappend \
  -force-uid 0 -force-gid 0 -processors 2 -mem 1G >>"$LOG" 2>&1
[ -f "$SURG/squashfs.new" ] || { say "  FAILED: no squashfs produced"; exit 1; }
say "  squashfs: $(du -h "$SURG/squashfs.new" | cut -f1)"

say "STEP 4/5 assembling ISO"
rm -f "$TREEISO/LiveOS/squashfs.img"
cp "$SURG/squashfs.new" "$TREEISO/LiveOS/squashfs.img"
cd "$SURG" || exit 1
xorrisofs -o "$ISO" -R -J -V VixzenOS_44_x86_64 \
  --grub2-mbr /usr/lib/grub/i386-pc/boot_hybrid.img -partition_offset 16 \
  -appended_part_as_gpt \
  -append_partition 2 C12A7328-F81F-11D2-BA4B-00A0C93EC93B "$TREEISO/images/efiboot.img" \
  -iso_mbr_part_type EBD0A0A2-B9E5-4433-87C0-68B6B72699C7 -c boot.cat \
  --boot-catalog-hide -b images/eltorito.img -no-emul-boot -boot-load-size 4 \
  -boot-info-table --grub2-boot-info -eltorito-alt-boot \
  -e '--interval:appended_partition_2:all::' -no-emul-boot \
  -graft-points .discinfo="$TREEISO/.discinfo" \
  images/pxeboot="$TREEISO/images/pxeboot" LiveOS="$TREEISO/LiveOS" \
  Fedora-Legal-README.txt="$TREEISO/Fedora-Legal-README.txt" \
  LICENSE="$TREEISO/LICENSE" boot/grub2="$TREEISO/boot/grub2" \
  boot/grub2/i386-pc=/usr/lib/grub/i386-pc \
  images/eltorito.img="$TREEISO/images/eltorito.img" \
  EFI/BOOT="$TREEISO/EFI/BOOT" >>"$LOG" 2>&1
[ -f "$ISO" ] || { say "  FAILED: no ISO produced"; exit 1; }
say "  ISO: $(du -h "$ISO" | cut -f1)"

say "STEP 5/5 implanting md5 checksum"
implantisomd5 --force "$ISO" >>"$LOG" 2>&1 && say "  checksum OK" || say "  checksum failed (first GRUB entry still boots)"

say "DONE: $ISO"
