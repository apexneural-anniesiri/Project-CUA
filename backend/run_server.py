"""
Server startup script with proper Windows event loop configuration.
Run this instead of uvicorn directly on Windows.
"""
import asyncio
import sys

if sys.platform == 'win32':
    # Set event loop policy BEFORE importing uvicorn
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    # Apply nest_asyncio
    import nest_asyncio
    nest_asyncio.apply()

import uvicorn

if __name__ == "__main__":
    # Pass app as import string for reload to work
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        loop="asyncio"
    )
