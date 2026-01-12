# ReasonOS - Autonomous Web Surfer Agent

ReasonOS is a "Computer-Using Agent" (CUA) that autonomously browses the web to complete tasks, based on the Synapse Report 2026 architecture.

## Project Structure

```
reason-os/
├── backend/          # FastAPI + Playwright
│   ├── agent.py      # WebSurferAgent class with execution loop
│   ├── main.py       # FastAPI endpoints
│   ├── run_server.py # Windows-compatible server startup script
│   ├── requirements.txt
│   ├── .env          # Environment variables (OPENAI_API_KEY)
│   ├── upload/       # Demo videos and showcases
│   │   └── video.mp4 # Screen recording demo
│   └── Dockerfile    # GCP Cloud Run compatible
└── frontend/         # React + Vite + Tailwind (Bun)
    ├── src/
    │   ├── App.jsx   # Mission Control Dashboard
    │   └── ...
    ├── package.json
    └── favicon.svg   # Custom favicon
```

## Features

- **Autonomous Web Browsing**: Uses GPT-4o vision to analyze screenshots and make decisions
- **Smart Navigation**: Direct URL navigation to avoid security challenges
- **Action Execution**: Can navigate, click, type, scroll, and finish tasks
- **Content Extraction**: Automatically extracts and displays results (post titles, links, etc.)
- **Real-time Monitoring**: Live screenshot feed and reasoning logs
- **Mission Results**: Displays extracted content and final results
- **Mission Control Dashboard**: Dark mode UI for monitoring agent activity

## Demo / Showcase

Watch the agent in action! See a screen recording of ReasonOS autonomously browsing the web:

**📹 [View Demo Video](./backend/upload/video.mp4)** *(Click to download and watch)*

> **💡 Tip:** For the best viewing experience, download the video file and play it in your video player. GitHub doesn't support inline video playback in README files, but you can also:
> - Upload the video to [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository) for better hosting
> - Convert to GIF format for inline preview
> - Host on YouTube/Vimeo and embed the link

**The demo showcases:**
- ✅ Real-time agent reasoning and decision-making
- ✅ Live screenshot feed of the agent's browser view
- ✅ Content extraction and results display
- ✅ Complete mission execution from start to finish
- ✅ Mission Control Dashboard in action

## Backend Setup

1. **Install dependencies:**
```bash
cd backend
pip install -r requirements.txt
playwright install chromium
```

2. **Set environment variable:**
```bash
# Windows PowerShell
$env:OPENAI_API_KEY="your_api_key_here"

# Or create a .env file in backend/ directory
echo "OPENAI_API_KEY=your_api_key_here" > backend/.env
```

3. **Run the server:**
```bash
# On Windows, use the run_server.py script for proper event loop configuration:
python run_server.py

# Or on Linux/Mac, you can use uvicorn directly:
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Frontend Setup

1. **Install dependencies:**
```bash
cd frontend
bun install
```

2. **Set API URL (optional):**
```bash
# Create .env file
echo "VITE_API_URL=http://localhost:8000" > .env
```

3. **Run the dev server:**
```bash
bun run dev
```

4. **Build for production:**
```bash
bun run build
```

## Docker Deployment (GCP Cloud Run)

1. **Build the Docker image:**
```bash
cd backend
docker build -t reason-os-backend .
```

2. **Run locally:**
```bash
docker run -p 8080:8080 -e OPENAI_API_KEY=your_key reason-os-backend
```

3. **Deploy to GCP Cloud Run:**
```bash
gcloud run deploy reason-os \
  --source . \
  --platform managed \
  --region us-central1 \
  --set-env-vars OPENAI_API_KEY=your_key \
  --allow-unauthenticated
```

## API Endpoints

- `POST /start` - Start a new agent session
  - Body: `{ "objective": "..." }`
  - Returns: `{ "session_id": "...", "message": "..." }`

- `POST /step` - Execute one step of the agent loop
  - Body: `{ "session_id": "..." }`
  - Returns: `{ "screenshot": "...", "logs": "...", "status": "active|completed", "extracted_content": "...", "url": "...", ... }`

- `GET /health` - Health check endpoint

- `DELETE /session/{session_id}` - Cleanup a session

## Usage

1. **Start the backend server:**
   ```bash
   cd backend
   python run_server.py  # Windows
   # or
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload  # Linux/Mac
   ```

2. **Start the frontend:**
   ```bash
   cd frontend
   bun run dev
   ```

3. **Open the frontend** (http://localhost:5173)

4. **Enter an objective** using direct navigation prompts:
   - ✅ **Good**: "Go to reddit.com/r/programming and show me the top posts"
   - ✅ **Good**: "Navigate to amazon.com and search for iPhone 15"
   - ❌ **Avoid**: "Search Google for Reddit" (may trigger CAPTCHA)

5. **Click "Run"** to start the agent

6. **Monitor the mission:**
   - Watch live screenshots in the "Live Vision Feed" panel
   - View reasoning logs in the "Agent Reasoning Logs" section
   - See extracted content in the "Results" panel when available

7. **View final results:**
   - Extracted content appears in the "Results" panel
   - Final screenshot in "Live Vision Feed"
   - Download complete logs with "Download Results" button

## Example Prompts

### Direct Navigation (Recommended)
```
Go to reddit.com/r/programming and show me the top posts
```

```
Navigate to amazon.com and search for iPhone 15
```

```
Go to github.com and search for fastapi repositories
```

### Shopping & Research
```
Navigate to amazon.com and find the price of MacBook Pro M3
```

```
Go to techcrunch.com and show me the latest AI news
```

```
Navigate to wikipedia.org and search for quantum computing
```

## Architecture

The agent implements the CUA Execution Loop from Synapse Report 2026:

1. **Initialize**: Start headless Playwright browser with anti-detection measures
2. **Take Action**: 
   - Capture screenshot
   - Send to GPT-4o with objective
   - Parse action (navigate/click/type/scroll/finish)
   - Execute action
3. **Extract Content**: Automatically extract relevant content from the page
4. **Return State**: Return screenshot, logs, and extracted content
5. **Repeat**: Until objective is complete

### Actions Available

- **navigate**: Directly navigate to a URL (avoids Google security challenges)
- **click**: Click on elements using CSS selectors or text
- **type**: Type text into input fields
- **scroll**: Scroll the page in any direction
- **finish**: Complete the task when objective is achieved

### Windows Compatibility

The backend uses `sync_playwright` in a thread pool executor to avoid asyncio event loop issues on Windows. Use `run_server.py` on Windows for proper configuration.

## Output & Results

When a mission completes, you'll see:

1. **Extracted Content**: Automatically extracted text, links, and data from the page
2. **Final Screenshot**: Last captured screenshot in Live Vision Feed
3. **Reasoning Logs**: Complete step-by-step reasoning of all actions
4. **Final URL**: The URL where the mission ended
5. **Downloadable Results**: All data can be downloaded as a text file

> 💡 **See it in action**: Watch the embedded demo video above to see the complete output showcase!

## Troubleshooting

### Google CAPTCHA Issues
- Use direct navigation prompts instead of searching Google
- Example: "Go to reddit.com" instead of "Search for Reddit on Google"

### Port Already in Use
- Backend uses port 8000 by default
- Change port in `run_server.py` or uvicorn command if needed

### Windows Event Loop Errors
- Always use `python run_server.py` on Windows
- Ensures proper event loop configuration for Playwright

## License

MIT
