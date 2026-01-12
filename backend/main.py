"""
FastAPI server for ReasonOS - The Autonomous Web Surfer Agent
"""

import asyncio
import os
import sys
import uuid
from typing import Dict, Optional

# Fix for Windows: Set event loop policy for Playwright subprocess support
if sys.platform == 'win32':
    # WindowsProactorEventLoopPolicy supports subprocess operations (required by Playwright)
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    # Enable nest_asyncio to allow nested event loops
    import nest_asyncio
    nest_asyncio.apply()

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent import WebSurferAgent

# Load environment variables from .env file
load_dotenv()


app = FastAPI(title="ReasonOS API", version="1.0.0")


# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session storage (use Redis/DB in production)
sessions: Dict[str, WebSurferAgent] = {}


class StartRequest(BaseModel):
    objective: str


class StepRequest(BaseModel):
    session_id: str


class StartResponse(BaseModel):
    session_id: str
    message: str


class StepResponse(BaseModel):
    screenshot: str
    logs: str
    status: str
    action: Optional[str] = None
    url: Optional[str] = None
    extracted_content: Optional[str] = None


@app.get("/health")
async def health_check():
    """Health check endpoint for GCP Cloud Run."""
    return {"status": "healthy", "service": "reason-os"}


@app.post("/start", response_model=StartResponse)
async def start_session(request: StartRequest):
    """
    Start a new agent session with an objective.
    
    Args:
        request: Contains the objective string
        
    Returns:
        Session ID for subsequent step calls
    """
    if not request.objective or not request.objective.strip():
        raise HTTPException(status_code=400, detail="Objective cannot be empty")
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY environment variable not set"
        )
    
    # Create new session
    session_id = str(uuid.uuid4())
    agent = WebSurferAgent(objective=request.objective.strip())
    
    try:
        await agent.initialize()
        sessions[session_id] = agent
        return StartResponse(
            session_id=session_id,
            message=f"Agent session started with objective: {request.objective}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize agent: {str(e)}"
        )


@app.post("/step", response_model=StepResponse)
async def execute_step(request: StepRequest):
    """
    Execute one step of the agent's execution loop.
    
    Args:
        request: Contains the session_id
        
    Returns:
        Screenshot, logs, status, and action details
    """
    session_id = request.session_id
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    agent = sessions[session_id]
    
    try:
        # Execute one action step
        action_result = await agent.take_action()
        
        # Get current state
        screenshot, logs, extracted_content = await agent.get_state()
        
        # Determine status
        status = "completed" if action_result.get("action") == "finish" else "active"
        
        # If completed, cleanup the session
        if status == "completed":
            await agent.cleanup()
            # Optionally keep session for a bit, or remove immediately
            # sessions.pop(session_id, None)
        
        return StepResponse(
            screenshot=screenshot,
            logs=logs,
            status=status,
            action=action_result.get("action"),
            url=action_result.get("url"),
            extracted_content=extracted_content
        )
        
    except Exception as e:
        # Cleanup on error
        try:
            await agent.cleanup()
        except:
            pass
        sessions.pop(session_id, None)
        raise HTTPException(
            status_code=500,
            detail=f"Error executing step: {str(e)}"
        )


@app.delete("/session/{session_id}")
async def cleanup_session(session_id: str):
    """Manually cleanup a session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    agent = sessions[session_id]
    try:
        await agent.cleanup()
    except:
        pass
    sessions.pop(session_id, None)
    return {"message": "Session cleaned up"}


if __name__ == "__main__":
    import uvicorn
    
    # Ensure Windows event loop policy is set before uvicorn starts
    if sys.platform == 'win32':
        # Create a new event loop with ProactorEventLoopPolicy
        policy = asyncio.WindowsProactorEventLoopPolicy()
        asyncio.set_event_loop_policy(policy)
        # Create and set the event loop
        loop = policy.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Use uvicorn's run with explicit loop configuration
    config = uvicorn.Config(
        app, 
        host="0.0.0.0", 
        port=8000,
        loop="asyncio",
        reload=True
    )
    server = uvicorn.Server(config)
    if sys.platform == 'win32':
        loop.run_until_complete(server.serve())
    else:
        asyncio.run(server.serve())