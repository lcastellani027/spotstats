from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import requests
import uvicorn
from starlette.responses import RedirectResponse
from fastapi import Cookie

client_id = "7a84e47e4908413cbbb2386b7e1e2aeb"
client_secret = "2e83d8fd6af3436491f364203e5c6757"
redirect_uri = "http://localhost:8000/callback"

prog_scope = ["playlist-read-private", "playlist-read-collaborative", "user-top-read"]
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


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

    details = [{
        "display_name": data.get("display_name"),
        "followers": data.get("followers", {}).get("total"),
        "pfp": img_url
    }]

    return templates.TemplateResponse("profile.html", {"request": request, "user_info": details})







if __name__ == "__main__":
    uvicorn.run(app)