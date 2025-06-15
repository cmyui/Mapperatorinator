import atexit
import base64
import os
import pprint
import secrets
import socket
import urllib.parse

import httpx
from pydantic import BaseModel

CLIENT_ID = os.environ["SPOTIFY_CLIENT_ID"]
CLIENT_SECRET = os.environ["SPOTIFY_CLIENT_SECRET"]

http_client = httpx.Client(
    base_url="https://api.spotify.com/v1",
)
server: socket.socket | None = None

def close_server():
    global server
    if server:
        server.close()
        server = None

atexit.register(close_server)

class AuthorizationGrant(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

def authorize() -> AuthorizationGrant:
    state = secrets.token_urlsafe(16)
    redirect_uri = "http://127.0.0.1:8000/callback"
    auth_url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode({
        "response_type": "code",
        "client_id": CLIENT_ID,
        "scope": "user-read-private user-library-read",
        "redirect_uri": redirect_uri,
        "state": state,
    })
    print(f"Please visit the following URL to authorize the application: {auth_url}")

    # spin up temp local server to handle the callback
    with socket.socket() as server:
        server.bind(("localhost", 8000))
        server.listen(1)
        conn, _ = server.accept()
        with conn:
            request = conn.recv(1024).decode()
            response = "HTTP/1.1 200 OK\n\nAuthorization successful! You can close this window."
            conn.sendall(response.encode())

    # Extract the authorization code from the request
    query_string = request.split(" ")[1].split("?")[1]
    params = urllib.parse.parse_qs(query_string)
    code = params.get("code")
    if not code:
        raise ValueError("Authorization code not found in the request.")

    # verify state parameter
    unverified_state = params.get("state")
    if not unverified_state or unverified_state[0] != state:
        raise ValueError("State parameter mismatch. Possible CSRF attack.")

    # Exchange the authorization code for an access token
    response = http_client.post(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": "Basic " + base64.b64encode(
                f"{CLIENT_ID}:{CLIENT_SECRET}".encode()
            ).decode(),
        },
        data={
            "grant_type": "authorization_code",
            "code": code[0],
            "redirect_uri": redirect_uri,
        },
    )
    response.raise_for_status()
    data = response.json()
    return AuthorizationGrant(**data)


authorization = authorize()

def get_current_users_playlists() -> list:
    response = http_client.get(
        "/me/playlists",
        headers={
            "Authorization": f"{authorization.token_type} {authorization.access_token}",
        },
    )
    response.raise_for_status()
    data = response.json()
    return data

def get_saved_tracks() -> list:
    response = http_client.get(
        "/me/tracks",
        headers={
            "Authorization": f"{authorization.token_type} {authorization.access_token}",
        },
    )
    response.raise_for_status()
    data = response.json()
    return data

if __name__ == "__main__":
    saved_tracks = get_saved_tracks()
    pprint.pp(saved_tracks)
