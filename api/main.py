from fastapi import FastAPI
from . import templates # New import for the templates router
from . import documents # New import for the documents router
from . import auth as auth_router_module # Renamed to avoid conflict

app = FastAPI(
    title="ClientDocManager API",
    description="API for managing clients, documents, and related functionalities.",
    version="0.1.0",
)

@app.get("/")
async def read_root():
    """
    Root endpoint for the API.
    Returns a welcome message.
    """
    return {"message": "Welcome to the ClientDocManager API"}

# Register the templates router
app.include_router(templates.router)
app.include_router(documents.router)
app.include_router(auth_router_module.router) # Auth router

# Further routers will be added here (for documents, auth, etc.)
