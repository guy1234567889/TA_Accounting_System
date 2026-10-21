"""Run ONCE on your own computer (not in the cloud) to get a Drive refresh token for a
personal Google account. Needed only if you don't have a Google Workspace shared drive.

  pip install google-auth-oauthlib
  python get_drive_token.py client_secret.json
"""
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

flow = InstalledAppFlow.from_client_secrets_file(
    sys.argv[1] if len(sys.argv) > 1 else "client_secret.json",
    ["https://www.googleapis.com/auth/drive"])
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
print("\nPaste this into secrets.toml:\n")
print("[drive]")
print('folder_id = "<ROOT_FOLDER_ID>"')
print(f'client_id = "{creds.client_id}"')
print(f'client_secret = "{creds.client_secret}"')
print(f'refresh_token = "{creds.refresh_token}"')
