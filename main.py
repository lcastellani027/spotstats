from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import requests
import uvicorn
from starlette.responses import RedirectResponse
from fastapi import Cookie
import random

client_id = "7a84e47e4908413cbbb2386b7e1e2aeb"
client_secret = "2e83d8fd6af3436491f364203e5c6757"
redirect_uri = "http://localhost:8000/callback"

prog_scope = ["playlist-read-private", "playlist-read-collaborative", "user-top-read"]
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

ranking_tracks = []

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.ico")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    scope = prog_scope
    auth_url = f"https://accounts.spotify.com/authorize?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&scope={' '.join(scope)}"
    return templates.TemplateResponse("auth.html", {"request": request, "auth_url": auth_url})

@app.get("/callback") #get user auth and redirect to dashboard
async def callback(code):

    response = requests.post(
        "https://accounts.spotify.com/api/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        },
        auth=(client_id, client_secret),
    )
    access_token = response.json()["access_token"]
    headers = {"Authorization": "Bearer " + access_token}

    red_response = RedirectResponse(url=f"/dashboard", headers=headers)
    red_response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False)

    return red_response

@app.get("/dashboard")
async def dashboard(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})

@app.get("/playlists")
async def dashboard(request:Request, access_token: str = Cookie(None)):
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"https://api.spotify.com/v1/me/playlists?limit=50"
    playlists = []


    while url is not None:
        response = requests.get(url=url, headers=headers)
        data = response.json()


        for item in data.get("items", []):
            imgs = item.get("images", [])
            if imgs is not None:
                img_url = imgs[0].get("url")
            else:
                img_url = f"static/blank_pfp.jpg"
            playlists.append({
                "name": item.get("name"),
                "id": item.get("id"),
                "track_count": item.get("tracks", {}).get("total"),
                "image_url": img_url,
            })
        url = data.get("next")
    return templates.TemplateResponse("playlists.html", {"request": request, "playlists": playlists})

@app.get("/profile")
async def profile(request: Request, access_token: str = Cookie(None)):
    headers = {"Authorization": f"Bearer {access_token}"}

    url = f"https://api.spotify.com/v1/me"

    response = requests.get(url=url, headers=headers)
    data = response.json()

    img = data.get("images", [])
    if img is not None:
        img_url = img[0].get("url")
    else:
        img_url = f"static/blank_pfp.jpg"

    details = {
        "display_name": data.get("display_name"),
        "followers": data.get("followers", {}).get("total"),
        "pfp": img_url
    }

    return templates.TemplateResponse("profile.html", {"request": request, "user_info": details})


@app.get("/api/analytics/artists")
async def analytics(request: Request, time_range: str, access_token: str = Cookie(None)):
    headers = {"Authorization": f"Bearer {access_token}"}


@app.get("/api/analytics/tracks")
async def analytics(request: Request, time_range: str, access_token: str = Cookie(None)):
    headers = {"Authorization": f"Bearer {access_token}"}


@app.get("/analytics")
async def analytics(request: Request, access_token: str = Cookie(None)):
    headers = {"Authorization": f"Bearer {access_token}"}

    artists = []
    tracks = []

    #get user top artists
    art_url = f'https://api.spotify.com/v1/me/top/artists?limit=5'
    art_response = requests.get(url=art_url, headers=headers)
    art_data = art_response.json()

    for item in art_data.get("items", []):

        img = item.get("images", [])
        if img is not None:
            img_url = img[0].get("url")
        else:
            img_url = f"static/blank_pfp.jpg"

        artists.append({
            "name": item.get("name"),
            "id": item.get("id"),
            "genres": item.get("genres"),
            "image_url": img_url,
        })



    #get user top songs
    track_url = f'https://api.spotify.com/v1/me/top/tracks?limit=25'
    track_response = requests.get(url=track_url, headers=headers)
    track_data = track_response.json()

    for item in track_data.get("items", []):

        album = item.get("album", {})
        artist = item.get("artists", [])

        tracks.append({
            "name": item.get("name"),
            "id": item.get("id"),
            "album_url": album.get("images", [])[0].get("url"),
            "album_external_url": album.get("external_urls", {}).get("spotify"),
            "album_name": album.get("name"),
            "artist_external_url": artist[0].get("external_urls", {}).get("spotify"),
            "artist_name": artist[0].get("name"),
        })

    print(tracks)
    print(artists)

    return templates.TemplateResponse("analytics.html", {"request": request, "artist_info": artists, "track_info": tracks})

#========================================================#
#======================== RANKER ========================#
#========================================================#

@app.get("/api/rank/next") #return next randomized track to user
async def ranker():
    if not ranking_tracks:
        return None

    track = ranking_tracks.pop()


    return {
        "track_name": track["name"],
        "track_id": track["id"],
        "album_name": track["album"]
    }

@app.get("/ranker")
async def ranker(request: Request, access_token: str = Cookie(None)):
    headers = {"Authorization": f"Bearer {access_token}"}
    # TODO: not require auth here, optional top artist ranking

    artist_uri = "6yJ6QQ3Y5l0s0tn7b0arrO"  # peggy
    # artist_uri = id

    url = f"https://api.spotify.com/v1/artists/{artist_uri}/albums?include_groups=album"
    # TODO: option for including features, etc from spot api options

    albums = []
    tracks = []

    while url is not None:
        response = requests.get(url=url, headers=headers)
        data = response.json()

        for item in data.get("items", []):
            imgs = item.get("images", [])
            if imgs is not None:
                img_url = imgs[0].get("url")
            else:
                img_url = f"static/blank_pfp.jpg"
            albums.append({
                "name": item.get("name"),
                "id": item.get("id"),
                "image_url": img_url,
            })
        url = data.get("next")

    for album in albums:

        album_id = album.get("id")
        url = f"https://api.spotify.com/v1/albums/{album_id}/tracks?limit=50"

        while url is not None:
            response = requests.get(url=url, headers=headers)
            data = response.json()
            for track in data.get("items", []):
                tracks.append({
                    "name": track.get("name"),
                    "id": track.get("id"),
                    "album": album.get("name")
                })
            url = data.get("next")

    global ranking_tracks
    ranking_tracks = tracks
    random.shuffle(ranking_tracks)

    return templates.TemplateResponse("ranker.html", {"request": request})


if __name__ == "__main__":
    uvicorn.run(app)