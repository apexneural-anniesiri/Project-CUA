# ReasonOS Backend

FastAPI backend for the autonomous web surfer agent.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
playwright install chromium
```

2. Set environment variable:
```bash
export OPENAI_API_KEY=your_api_key_here
```

3. Run the server:
```bash
uvicorn main:app --host 0.0.0.0 --port 8080
```

## Docker

Build:
```bash
docker build -t reason-os-backend .
```

Run:
```bash
docker run -p 8080:8080 -e OPENAI_API_KEY=your_key reason-os-backend
```

## Environment Variables

- `OPENAI_API_KEY` (required): Your OpenAI API key for GPT-4o access
