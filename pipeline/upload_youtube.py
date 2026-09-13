#!/usr/bin/env python3
"""
YouTube uploader for the rendered episode.

IMPORTANT - READ FIRST (this is the #1 trap of automated YouTube channels):
Videos uploaded through the YouTube Data API from an *unaudited* Google Cloud
project are LOCKED AS PRIVATE by Google and cannot be appealed
(https://developers.google.com/youtube/v3/docs/videos).
So you have two supported modes:

  MODE A (recommended until your audit is approved): do not set the YT_*
           secrets. Download the mp4 from the GitHub Actions artifact and
           upload it in YouTube Studio (30 seconds a day).

  MODE B (fully automatic): submit the free API compliance audit form
           (https://support.google.com/youtube/contact/yt_api_form). Once
           approved, set the two secrets and uploads go public automatically.

First-time authorisation (run once on your own computer):
  pip install google-api-python-client google-auth-oauthlib
  export YT_CLIENT_SECRET='{"installed":{...}}'   # OAuth client json from Cloud Console
  python pipeline/upload_youtube.py --auth
  -> prints a URL, open it, log into your channel account, paste the code back.
  -> creates token.json ; paste its base64 into the YT_TOKEN_JSON secret.
"""
import base64, glob, json, os, sys
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
HERE = Path(__file__).resolve().parent

def load_client_secret():
    if os.environ.get("YT_CLIENT_SECRET"):
        return os.environ["YT_CLIENT_SECRET"]
    for p in (Path.cwd() / "client_secret.json",
              HERE.parent / "client_secret.json",
              HERE / "client_secret.json"):
        if p.exists():
            return p.read_text()
    sys.exit("client_secret.json not found and YT_CLIENT_SECRET not set.\n"
             "Create it: Cloud Console -> APIs & Services -> Credentials ->\n"
             "+ Create credentials -> OAuth client ID -> Desktop app -> download\n"
             "the JSON and save it as client_secret.json in the repo root.\n"
             "NEVER commit that file (it is in .gitignore).")

def get_credentials():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    client_secret = json.loads(load_client_secret())
    token = json.loads(base64.b64decode(os.environ["YT_TOKEN_JSON"]))
    creds = Credentials.from_authorized_user_info(token, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds

def auth_first_time():
    load_client_secret()  # friendly message if missing, before any imports
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        sys.exit("Missing library. Run:  python -m pip install --user "
                 "google-api-python-client google-auth-oauthlib\n"
                 "(or just double-click scripts/setup_once.*)")
    flow = InstalledAppFlow.from_client_config(json.loads(load_client_secret()), SCOPES)
    creds = flow.run_local_server(port=0)
    print("TOKEN_JSON base64 (put this in the YT_TOKEN_JSON secret):")
    print(base64.b64encode(json.dumps({
        "token": creds.token, "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri, "client_id": creds.client_id,
        "client_secret": creds.client_secret, "scopes": list(creds.scopes)
    }).encode()).decode())

def upload():
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    vids = sorted(glob.glob("out/episode-*.mp4"))
    if not vids:
        print("no video found"); return
    v = vids[-1]
    desc_file = v.replace(".mp4", ".description.txt")
    creds = get_credentials()
    yt = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {
            "title": os.path.basename(v).replace(".mp4", "").replace("-", " ").title()
                     + " - Mr Long & Ronnie Learn English",
            "description": open(desc_file).read() if os.path.exists(desc_file) else "",
            "categoryId": "27",  # Education
            "tags": ["learn english", "khmer kids", "english for kids",
                     "mr long and ronnie", "cartoon"],
        },
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": True},
    }
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(v, mimetype="video/mp4",
                                                        resumable=True))
    resp = req.execute()
    print("uploaded https://youtu.be/" + resp["id"])

if __name__ == "__main__":
    if "--auth" in sys.argv:
        auth_first_time()
    else:
        upload()
