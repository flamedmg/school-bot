from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.router import router
from src.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # Add any startup logic here (db connections, etc.)
    yield
    # Shutdown
    # Add any cleanup logic here


app = FastAPI(
    title="EKlasse Bot API",
    description="API for handling authenticated redirects and other functionalities",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api/v1")


# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}


def start_api():
    """Function to start the API server using uvicorn"""
    import uvicorn

    uvicorn.run(
        "src.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        reload=True,  # Enable auto-reload during development
    )


if __name__ == "__main__":
    start_api()
