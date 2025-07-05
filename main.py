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

prog_scope = ["playlist-read-private", "playlist-read-collaborative"]
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def get_access_token(auth_code: str):
    response = requests.post(
        "https://accounts.spotify.com/api/token",
        data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": redirect_uri,
        },
        auth=(client_id, client_secret),
    )
    access_token = response.json()["access_token"]
    return {"Authorization": "Bearer " + access_token}, access_token


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.ico")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    scope = prog_scope
    auth_url = f"https://accounts.spotify.com/authorize?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&scope={' '.join(scope)}"
    return templates.TemplateResponse("auth.html", {"request": request, "auth_url": auth_url})

@app.get("/dashboard")
async def dashboard(request: Request, user_id: str):
    return templates.TemplateResponse("landing.html", {"request": request, "user_id": user_id})

@app.get("/playlists")
async def dashboard(request:Request, user_id: str, access_token: str = Cookie(None)):
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"https://api.spotify.com/v1/users/{user_id}/playlists?limit=50"
    playlists = []


    while url is not None:
        response = requests.get(url=url, headers=headers)
        data = response.json()


        for item in data.get("items", []):
            playlists.append({
                "name": item.get("name"),
                "id": item.get("id"),
                "track_count": item.get("tracks", {}).get("total")
            })
        url = data.get("next")
    return {"playlists": playlists}



@app.get("/callback")
async def callback(code):

    headers, token = get_access_token(code)
    response = requests.get("https://api.spotify.com/v1/me", headers = headers)
    user_id = response.json()["id"]

    red_response = RedirectResponse(url=f"/dashboard?user_id={user_id}", headers=headers)
    red_response.set_cookie(key="access_token", value=token, httponly=True, secure=False)

    return red_response



if __name__ == "__main__":
    uvicorn.run(app)