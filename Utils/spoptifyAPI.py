import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.exceptions import SpotifyException

def validate_spotify_credentials(client_id: str, client_secret: str) -> list:
    print("Validating Spotify credentials...")
    try:
        # Create the Spotify client using the provided credentials
        sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret))
        # Make a simple request to test the credentials
        sp.search(q="test", type="track", limit=1)
        # If the request succeeds, credentials are valid
        return [True, sp]
    except SpotifyException as e:
        print(f"SpotifyException: Invalid credentials. {e}")
        return [False, None]
    except Exception as e:
        # Catch unexpected exceptions to prevent crashing
        print(f"Unexpected exception occurred: {e}")
        return [False, None]

def get_spotify_link_type(spotify_link) -> str | None:
    if "https://open.spotify.com/playlist" in spotify_link:
        return "playlist"
    elif "https://open.spotify.com/" in spotify_link:
        return "song"
    else:
        return None