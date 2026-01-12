# ReasonOS Frontend

React + Vite frontend for the Mission Control Dashboard.

## Setup

1. Install dependencies:
```bash
bun install
```

2. Set API URL (optional, defaults to http://localhost:8000):
```bash
# Create .env file
echo "VITE_API_URL=http://localhost:8000" > .env
```

3. Run dev server:
```bash
bun run dev
```

4. Build for production:
```bash
bun run build
```

## Environment Variables

- `VITE_API_URL`: Backend API URL (default: http://localhost:8000)
