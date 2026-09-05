#!/usr/bin/env bash
set -euo pipefail
UPSTREAM_REPO=${UPSTREAM_REPO:-https://github.com/diffusionstudio/editor.git};UPSTREAM_COMMIT=${UPSTREAM_COMMIT:-c64067bd45768b45287cb4ca53f76c9fb5a037e1};PKG_VERSION=${PKG_VERSION:-0.204.1+fa3.1};ARCH=${ARCH:-amd64}
ROOT=$(cd "$(dirname "$0")/../.." && pwd);WORK=${WORK:-$ROOT/.build/diffusion-studio};OUT=${OUT:-$ROOT/dist};rm -rf "$WORK";mkdir -p "$WORK" "$OUT"
git clone --filter=blob:none --no-checkout "$UPSTREAM_REPO" "$WORK/upstream";git -C "$WORK/upstream" checkout --detach "$UPSTREAM_COMMIT";test "$(git -C "$WORK/upstream" rev-parse HEAD)" = "$UPSTREAM_COMMIT";cd "$WORK/upstream"
npm ci;cp apps/web/.env.example apps/web/.env
python3 - <<'PY'
p='apps/desktop/scripts/stage-cli.mjs';s=open(p).read();needle='const wrapper = `#!/bin/sh\n';prefix='const isDarwin = process.platform === "darwin";\nconst appPathRel = isDarwin ? "$DIR/../../../.." : "$DIR/../../..";\nconst binaryRel = isDarwin ? "$DIR/../../../MacOS/Diffusion Studio" : "$DIR/../../../Diffusion Studio";\n';assert needle in s;s=s.replace(needle,prefix+needle,1);s=s.replace('export DIFFUSION_APP_PATH="$(cd "$DIR/../../../.." && pwd)"','export DIFFUSION_APP_PATH="$(cd "${appPathRel}" && pwd)"',1);s=s.replace('ELECTRON_RUN_AS_NODE=1 exec "$DIR/../../../MacOS/Diffusion Studio" "$DIR/../dapi.js" "$@"','ELECTRON_RUN_AS_NODE=1 exec "${binaryRel}" "$DIR/../dapi.js" "$@"',1);open(p,'w').write(s)
PY
npm run package --workspace=@diffusionstudio/desktop
APP=$(find apps/desktop/out -maxdepth 1 -type d -name 'Diffusion Studio-linux-x64' -print -quit);test -n "$APP";STAGE="$WORK/deb";mkdir -p "$STAGE/DEBIAN" "$STAGE/usr/lib/diffusion-studio" "$STAGE/usr/bin" "$STAGE/usr/share/applications" "$STAGE/usr/share/metainfo" "$STAGE/usr/share/icons/hicolor/512x512/apps" "$STAGE/usr/share/fa3/providers/diffusion-studio" "$STAGE/usr/lib/fa3/diffusion-studio";cp -a "$APP"/. "$STAGE/usr/lib/diffusion-studio/"
cat > "$STAGE/DEBIAN/control" <<EOF
Package: diffusion-studio-fa3
Version: $PKG_VERSION
Section: video
Priority: optional
Architecture: $ARCH
Maintainer: FA3 local integration
Depends: libc6, libnss3, libxss1, xdg-utils, libgtk-3-0t64 | libgtk-3-0, libasound2t64 | libasound2
Description: Diffusion Studio v0.204.1 with FA3 agent/capability integration
 Wayland-first KDE Plasma desktop package pinned to immutable upstream source.
EOF
cat > "$STAGE/usr/bin/diffusion-studio" <<'EOF'
#!/bin/sh
APP='/usr/lib/diffusion-studio/Diffusion Studio'
if [ "${XDG_SESSION_TYPE:-}" = wayland ]; then exec "$APP" --ozone-platform=wayland "$@";fi
exec "$APP" "$@"
EOF
chmod 0755 "$STAGE/usr/bin/diffusion-studio";ln -s ../lib/diffusion-studio/resources/cli/bin/dapi "$STAGE/usr/bin/dapi";install -m 0755 "$ROOT/src/fa3_diffusion_studio_adapter.py" "$STAGE/usr/lib/fa3/diffusion-studio/adapter.py";ln -s ../lib/fa3/diffusion-studio/adapter.py "$STAGE/usr/bin/fa3-diffusion-studio";install -m 0644 "$ROOT/canonical/providers/FA3-PROVIDER-DIFFUSION-STUDIO-001.json" "$STAGE/usr/share/fa3/providers/diffusion-studio/provider.json"
cat > "$STAGE/usr/share/applications/diffusion-studio-fa3.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Diffusion Studio (FA3)
GenericName=Video Editor
Comment=Agent-operable programmable video editor
Exec=diffusion-studio %U
Icon=diffusion-studio
Terminal=false
Categories=AudioVideo;Video;
StartupNotify=true
MimeType=x-scheme-handler/diffusion;
EOF
if [ -f apps/desktop/assets/icon.png ];then install -m 0644 apps/desktop/assets/icon.png "$STAGE/usr/share/icons/hicolor/512x512/apps/diffusion-studio.png";fi
if [ -f "$STAGE/usr/lib/diffusion-studio/chrome-sandbox" ];then chmod 4755 "$STAGE/usr/lib/diffusion-studio/chrome-sandbox";fi
DEB="$OUT/diffusion-studio-fa3_${PKG_VERSION}_${ARCH}.deb";dpkg-deb --build --root-owner-group "$STAGE" "$DEB";dpkg-deb --info "$DEB";dpkg-deb --contents "$DEB" | grep -E 'usr/bin/(diffusion-studio|dapi|fa3-diffusion-studio)|provider.json' >/dev/null;sha256sum "$DEB" | tee "$DEB.sha256"
python3 - <<PY > "$OUT/diffusion-studio-fa3-build-evidence.json"
import hashlib,json,os
p='$DEB';b=open(p,'rb').read();print(json.dumps({'schema':'fa3.build-evidence.v1','provider_id':'FA3-PROVIDER-DIFFUSION-STUDIO-001','upstream_commit':'$UPSTREAM_COMMIT','package':os.path.basename(p),'sha256':hashlib.sha256(b).hexdigest(),'architecture':'$ARCH','result':'PASS'},indent=2))
PY
