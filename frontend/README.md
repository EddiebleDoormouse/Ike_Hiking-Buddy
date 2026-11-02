# Hiking Buddy frontend

## Setup

Requires Node.js 22 and npm.

```sh
npm install
npm run dev
npm run build
```

The development server is available at http://localhost:5173.

Copy `.env.example` to `.env` to configure the frontend:

- `VITE_API_URL` sets the backend base URL (default: `http://localhost:8000`).
- `VITE_USE_MOCKS=true` enables the in-memory demo data and mock API.

## Open it on your phone

The dev server listens on all interfaces (`server.host`) and allows
`*.trycloudflare.com` origins, so a Cloudflare quick tunnel can reach it.

Run two tunnels — one for the frontend and one for the backend:

```sh
cloudflared tunnel --url http://localhost:5173   # frontend
cloudflared tunnel --url http://localhost:8000   # backend
```

Then, in `frontend/.env`:

1. Set `VITE_API_URL` to the backend tunnel URL (e.g. `https://<backend>.trycloudflare.com`).
2. Add the **frontend** tunnel origin (e.g. `https://<frontend>.trycloudflare.com`) to `ALLOWED_ORIGINS` in the repo-root `.env` so the backend CORS middleware accepts it.
3. Restart `npm run dev` and open the frontend tunnel URL on your phone.

Requests from the tunnel host are allowed by `server.allowedHosts` in `vite.config.ts`.
