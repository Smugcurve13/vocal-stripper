#!/bin/sh
set -eu

base='https://github.com/eugeneware/ffmpeg-static/releases/download/b6.1.1'
dir='assets/ffmpeg/macos'
mkdir -p "$dir"

curl -sSLf -o "$dir/ffmpeg.gz" "$base/ffmpeg-darwin-arm64.gz"
curl -sSLf -o "$dir/ffprobe.gz" "$base/ffprobe-darwin-arm64.gz"
echo '8923876afa8db5585022d7860ec7e589af192f441c56793971276d450ed3bbfa  assets/ffmpeg/macos/ffmpeg.gz' | shasum -a 256 -c -
echo 'd986a8ec7b030899fe66a8a288ed809a3543338705a3ce178cfb85869c5d80be  assets/ffmpeg/macos/ffprobe.gz' | shasum -a 256 -c -
gunzip -f "$dir/ffmpeg.gz" "$dir/ffprobe.gz"
chmod +x "$dir/ffmpeg" "$dir/ffprobe"
"$dir/ffmpeg" -hide_banner -version | sed -n '1p'
