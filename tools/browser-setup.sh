#!/usr/bin/env bash
# Set up headless Chromium for tools/layout-check.mjs on a machine without
# root (no system fonts, no Chromium, no apt lists).
#
#   bash tools/browser-setup.sh            # installs into /tmp/pw + /tmp/libx
#   LD_LIBRARY_PATH=/tmp/libx/root/usr/lib/x86_64-linux-gnu \
#   FONTCONFIG_FILE=/tmp/libx/fonts.conf  \
#   PW=/tmp/pw/node_modules/playwright node tools/layout-check.mjs
#
# Chromium needs a handful of shared libraries and at least one font; both are
# unpacked locally (no sudo). Re-run after a restore, /tmp is not preserved.
set -euo pipefail

PW_DIR=${PW_DIR:-/tmp/pw}
LIB_DIR=${LIB_DIR:-/tmp/libx}
M=http://archive.ubuntu.com/ubuntu            # bionic..noble pool (stable URLs)
ARCH=amd64

mkdir -p "$PW_DIR" "$LIB_DIR/debs" "$LIB_DIR/root" "$LIB_DIR/fontcache"

# --- playwright + its bundled browser ---------------------------------------
cd "$PW_DIR"
[ -f package.json ] || npm init -y >/dev/null
npm i playwright --no-audit --no-fund
npx playwright install chromium

# --- the shared libraries chrome-headless-shell links against ----------------
fetch() { # fetch <pooldir> <package names...>
  local dir=$1; shift
  local list pkg file
  list=$(curl -fsS --max-time 60 --retry 3 "$M/$dir/" | grep -oE 'href="[^"]+"' | sed 's/href="//;s/"//')
  for pkg in "$@"; do
    # amd64 build if there is one, otherwise the arch-independent package
    file=$(printf '%s\n' "$list" | grep -E "^${pkg}_[^/]*_${ARCH}\.deb$" | sort -V | tail -1)
    [ -n "$file" ] || file=$(printf '%s\n' "$list" | grep -E "^${pkg}_[^/]*_all\.deb$" | sort -V | tail -1)
    if [ -n "$file" ]; then curl -fsS --max-time 180 --retry 3 -O "$M/$dir/$file" || echo "download failed: $file" >&2
    else echo "missing: $pkg" >&2; fi
  done
}
cd "$LIB_DIR/debs"
fetch pool/main/n/nspr       libnspr4
fetch pool/main/n/nss        libnss3
fetch pool/main/a/at-spi2-core libatk1.0-0t64 libatk-bridge2.0-0t64 libatspi2.0-0t64
fetch pool/main/libx/libxcomposite libxcomposite1
fetch pool/main/libx/libxdamage    libxdamage1
fetch pool/main/libx/libxfixes     libxfixes3
fetch pool/main/libx/libxrandr     libxrandr2
fetch pool/main/libx/libxrender    libxrender1
fetch pool/main/libx/libxi         libxi6
fetch pool/main/libx/libxres       libxres1
fetch pool/main/libx/libxkbcommon  libxkbcommon0
# libasound2t64 from the pool links GLIBC_2.43 (newer than the host), so take
# the older build that still provides the same soname
curl -fsS --max-time 180 --retry 3 -O \
  "$M/pool/main/a/alsa-lib/libasound2_1.2.6.1-1ubuntu1.2_${ARCH}.deb"
fetch pool/main/f/fonts-dejavu     fonts-dejavu-core

for deb in *.deb; do dpkg-deb -x "$deb" "$LIB_DIR/root"; done

# libasound2 ships as libasound.so.2.0.0 + a symlink; make sure the symlink is
# the one we just extracted rather than a leftover newer build.
ldd "$LIB_DIR/root/usr/lib/x86_64-linux-gnu/libasound.so.2" 2>/dev/null \
  | grep -q 'not found' && echo "libasound: version conflict, see note above" >&2 || true

# --- fontconfig: without a font, chromium dies in SkFontMgr ----------------
cat > "$LIB_DIR/fonts.conf" <<XML
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <dir>$LIB_DIR/root/usr/share/fonts</dir>
  <cachedir>$LIB_DIR/fontcache</cachedir>
</fontconfig>
XML

echo
echo "ready. run the layout check with:"
echo "  LD_LIBRARY_PATH=$LIB_DIR/root/usr/lib/x86_64-linux-gnu \\"
echo "  FONTCONFIG_FILE=$LIB_DIR/fonts.conf \\"
echo "  PW=$PW_DIR/node_modules/playwright node tools/layout-check.mjs"
