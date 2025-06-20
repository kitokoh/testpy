from fastapi import FastAPI
from . import templates
from . import documents
from . import auth as auth_router_module
from . import products # New import for the products router
from . import payments # Import for the payments router
from . import assets as assets_api_router # Import for the assets router
from . import employees # Import for the employees router
from . import leave # Import for the leave router
from . import performance # Import for the performance router
from . import employee_documents # Import for employee documents router
from . import hr_reports # Import for HR reports router
from . import recruitment as recruitment_router_module # Import for the recruitment router
from . import company_expenses_api # Import for the company expenses router
from . import company_factures_api # Import for the company factures router


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
app.include_router(payments.router, prefix="/api/v1/payments", tags=["Payments Management"]) # Register the payments router
app.include_router(assets_api_router.router) # Register the assets router
app.include_router(employees.router) # Register the employees router
app.include_router(leave.router) # Register the leave router
app.include_router(performance.router) # Register the performance router
app.include_router(employee_documents.router) # Register employee documents router
app.include_router(hr_reports.router) # Register HR reports router
app.include_router(recruitment_router_module.router) # Register the recruitment router
app.include_router(company_expenses_api.router) # Register the company expenses router
app.include_router(company_factures_api.router) # Register the company factures router

# Further routers will be added here (for documents, auth, etc.)
