#!/bin/bash
set -euo pipefail

root=$(cd -- "$(dirname -- "$0")/.." && pwd)
version=$(sed -n 's/^version = "\([0-9.]*\)"$/\1/p' "$root/pyproject.toml")
if [[ "$(uname -s)" != Darwin || "$(uname -m)" != arm64 || -z "$version" ]]; then
    printf '%s\n' 'Build this disk image on an Apple Silicon Mac with Go and uv installed.' >&2
    exit 1
fi

out="$root/release"
scratch=$(mktemp -d "${TMPDIR:-/tmp}/localsrt-macos.XXXXXXXX")
trap 'rm -r "$scratch"' EXIT
stage="$scratch/image"
worker="$scratch/worker"
app="$stage/Local SRT.app"
resources="$app/Contents/Resources"
mkdir -p "$out" "$app/Contents/MacOS" "$resources" "$worker"
(
    cd "$root/desktop"
    CGO_ENABLED=0 GOOS=darwin GOARCH=arm64 go build -trimpath -ldflags "-X main.appVersion=$version" -o "$app/Contents/MacOS/LocalSRT" .
)
install -m 755 "$(command -v uv)" "$resources/uv"
uv_version=$(uv --version | awk '{ print $2 }')
for license in LICENSE-MIT LICENSE-APACHE; do
    curl -fLsS --retry 2 "https://raw.githubusercontent.com/astral-sh/uv/$uv_version/$license" -o "$resources/uv-$license"
done
install -m 644 "$root/packaging/macos/prepare-worker.sh" "$resources/prepare-worker.sh"
cp "$root/pyproject.toml" "$root/README.md" "$worker/"
git -C "$root" ls-files -z src/local_srt | while IFS= read -r -d '' relative; do
    target="$worker/$relative"
    mkdir -p "$(dirname "$target")"
    install -m 644 "$root/$relative" "$target"
done
uv --no-config build --wheel --python 3.12 --out-dir "$resources" "$worker"
cat > "$app/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>Local SRT</string>
    <key>CFBundleDisplayName</key><string>Local SRT</string>
    <key>CFBundleIdentifier</key><string>com.auodsgae.localsrt</string>
    <key>CFBundleExecutable</key><string>LocalSRT</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleVersion</key><string>$version</string>
    <key>CFBundleShortVersionString</key><string>$version</string>
    <key>LSMinimumSystemVersion</key><string>14.0</string>
    <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
EOF
plutil -lint "$app/Contents/Info.plist"
codesign --force --sign - "$resources/uv"
codesign --force --sign - "$app"
codesign --verify --deep --strict "$app"
ln -s /Applications "$stage/Applications"
hdiutil create -ov -format UDZO -volname "Local SRT" -srcfolder "$stage" "$out/LocalSRT-v$version-macOS-arm64.dmg"
