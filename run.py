"""
Script to run the FastAPI server.
"""
import sys
import uvicorn
from contextlib import suppress


if __name__ == "__main__":
    try:
        print("Starting Cloud Pricing Comparison API...")
        print("API documentation will be available at: http://0.0.0.0:8002/docs")
        uvicorn.run("app.main:app", host="0.0.0.0", port=8002, reload=True)
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        print(f"Error starting the server: {str(e)}")
        sys.exit(1) 