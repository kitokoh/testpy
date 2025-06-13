from fastapi import FastAPI
from . import templates
from . import documents
from . import auth as auth_router_module
from . import products # New import for the products router
from . import proformas # New import for the proformas router

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
app.include_router(auth_router_module.router)
app.include_router(products.router) # Register the new products router
app.include_router(proformas.router) # Register the new proformas router

# Further routers will be added here (for documents, auth, etc.)
