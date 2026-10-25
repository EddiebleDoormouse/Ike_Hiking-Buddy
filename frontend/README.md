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
