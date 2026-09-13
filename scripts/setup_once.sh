#!/usr/bin/env bash
# One-time: switch on automatic publishing. macOS/Linux. (Windows: setup_once.bat)
set -e
cd "$(dirname "$0")/.."
echo "=== Mr Long & Ronnie: switch on auto-upload (one-time, ~2 min) ==="
python3 -m pip install --user -q google-api-python-client google-auth-oauthlib

echo ""
echo "A web address will appear below. Open it, sign into the Google account"
echo "that owns the channel, click Allow, then paste the code back here."
echo ""
python3 pipeline/upload_youtube.py --auth

echo ""
echo "==============================================================="
echo "DONE. Now add two secrets in GitHub (repo -> Settings ->"
echo "Secrets and variables -> Actions -> New repository secret):"
echo ""
echo "  1) YT_CLIENT_SECRET  -> paste the CONTENT of client_secret.json"
echo "  2) YT_TOKEN_JSON     -> paste the base64 line printed above"
echo ""
echo "From tomorrow the daily episode publishes itself. Nothing else to do."
