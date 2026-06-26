# Deploying JLC Textile Manager to Railway

This is a **single service**: one Docker image builds the React frontend and
serves it together with the FastAPI backend. You only need to add a
**PostgreSQL** database and a few environment variables.

---

## What's in the box
- `Dockerfile` — multi-stage build (React → FastAPI). Railway auto-detects it.
- `railway.json` — tells Railway to use the Dockerfile.
- `backend/` — FastAPI API + PDF + analytics.
- `frontend/` — React app (built into the image).
- Fonts for the order-form PDF are bundled / installed in the image.

The app reads `PORT` (Railway sets it) and `DATABASE_URL` (from the Postgres
plugin) automatically — no code changes needed.

---

## Option A — Deploy from GitHub (recommended)

1. **Push this folder to a GitHub repo** (see "Push to GitHub" below).
2. Go to **railway.app → New Project → Deploy from GitHub repo** → pick the repo.
   Railway detects the `Dockerfile` and starts building.
3. In the project, click **New → Database → PostgreSQL**.
4. Open your **app service → Variables** and add:

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` *(use the "reference" picker → Postgres → DATABASE_URL)* |
   | `SHOP_USERNAME` | your login username (e.g. `jailaxmi`) |
   | `SHOP_PASSWORD` | a strong password |
   | `SECRET_KEY` | `FqDLgwnmH8_tWurbSehYfhlhi8SFwmRP_bXUGCxQkDX6f0tNGv3Oxq4jf4DuFbNQ` *(or your own long random string)* |
   | `STABILITY_API_KEY` | *(optional — only for AI Image→Image)* |

5. **App service → Settings → Networking → Generate Domain.**
6. Open that URL on the tablet and log in. Done. 🎉

---

## Option B — Deploy with the Railway CLI (no GitHub)

```bash
npm i -g @railway/cli
railway login
cd C:\Users\ASUS\Desktop\JLC
railway init                # create a new project
railway add                 # choose "PostgreSQL"
railway up                  # builds the Dockerfile and deploys
```
Then set the variables (same table as above) in the Railway dashboard or with
`railway variables --set SHOP_PASSWORD=...`, and run `railway domain` to get a URL.

---

## Push to GitHub (for Option A)

```bash
cd C:\Users\ASUS\Desktop\JLC
git add .
git commit -m "JLC web app"
# create an empty repo on github.com first, then:
git remote add origin https://github.com/<you>/<repo>.git
git branch -M main
git push -u origin main
```
*(A git repo has already been initialised with a first commit — you only need
to add the remote and push.)*

---

## After it's live
- **First login** uses the `SHOP_USERNAME` / `SHOP_PASSWORD` you set.
- **Add to tablet home screen** (Safari/Chrome → Share → Add to Home Screen) so
  it opens like an app.
- **Backups:** Settings → Download Backup saves a full JSON copy of all data.
- The PostgreSQL data persists across deploys; redeploying code never wipes it.

## Notes
- The cursive "Jlc" logo uses the bundled **Great Vibes** font, so it renders
  the same on the server as the vector design.
- To change the login later, just edit the `SHOP_USERNAME` / `SHOP_PASSWORD`
  variables in Railway and redeploy.
