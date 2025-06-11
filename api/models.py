from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class TemplateInfo(BaseModel):
    template_id: int = Field(..., description="Unique identifier for the template")
    template_name: str = Field(..., description="Display name of the template")
    description: Optional[str] = Field(None, description="Optional description of the template")
    template_type: str = Field(..., description="Type of the template, e.g., 'document_excel', 'document_word', 'html_cover_page'")
    language_code: Optional[str] = Field(None, description="Language code of the template, e.g., 'en', 'fr'")

class DocumentGenerationRequest(BaseModel):
    template_id: int = Field(..., description="ID of the template to use for generation")
    client_id: str = Field(..., description="ID of the client for whom the document is generated")
    project_id: Optional[str] = Field(None, description="Optional ID of the project related to this document")
    company_id: str = Field(..., description="ID of the company (seller/our company) generating the document")
    target_language_code: str = Field(..., description="Target language for the document content, e.g., 'fr', 'en'")
    document_title: Optional[str] = Field(None, description="Optional title for the document, overrides template default if provided")
    # For product-specific data, like in a proforma or invoice
    # This allows flexible input for different document types.
    # Example for proforma: [{"product_id": 1, "quantity": 2, "unit_price_override": 50.0}, ...]
    line_items: Optional[List[Dict[str, Any]]] = Field(None, description="List of line items, e.g., products with quantities and prices")
    # For other context-specific data that might be needed by get_document_context_data
    additional_context: Optional[Dict[str, Any]] = Field(None, description="Other context-specific data needed for the document")

class DocumentGenerationResponse(BaseModel):
    message: str = Field(..., description="Status message of the generation process")
    document_id: Optional[str] = Field(None, description="Unique ID of the generated document record in the database")
    client_id: str = Field(..., description="ID of the client for whom the document was generated")
    file_name: Optional[str] = Field(None, description="Name of the generated file")
    download_url: Optional[str] = Field(None, description="URL to download the generated document")

# You can add more models here as needed for other API endpoints

class Token(BaseModel):
    access_token: str = Field(..., description="The JWT access token string.")
    token_type: str = Field("bearer", description="The type of token, typically 'bearer'.")

class TokenData(BaseModel):
    username: Optional[str] = Field(None, description="The username extracted from the token.")

class UserInDB(BaseModel): # For current user dependency and user info
    username: str = Field(..., description="The user's unique username.")
    email: Optional[str] = Field(None, description="The user's email address.")
    full_name: Optional[str] = Field(None, description="The user's full name.")
    role: str = Field(..., description="The user's role, determining permissions.")
    is_active: bool = Field(..., description="Flag indicating if the user account is active.")
    user_id: str = Field(..., description="The unique identifier for the user.")
