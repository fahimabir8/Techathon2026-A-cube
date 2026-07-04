"""
Smart Office Monitor — Entry-point convenience script.

Usage:
    python main.py
    # or
    uvicorn backend.main:app --reload
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
