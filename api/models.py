from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime

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

# Models for Product Media Links / Images
class ProductImageLinkBase(BaseModel):
    media_item_id: str = Field(..., description="ID of the linked media item (image).")
    display_order: Optional[int] = Field(0, description="Display order of the image for the product.")
    alt_text: Optional[str] = Field(None, description="Alternative text for the image.")

class ProductImageLinkCreate(ProductImageLinkBase):
    pass

class ProductImageLinkUpdateRequest(BaseModel):
    display_order: Optional[int] = Field(None, description="New display order of the image.")
    alt_text: Optional[str] = Field(None, description="New alternative text for the image.")

class ProductImageLinkResponse(ProductImageLinkBase):
    link_id: int = Field(..., description="Unique ID of the product-media link.")
    # URLs will be constructed at runtime by the API endpoint
    image_url: Optional[str] = Field(None, description="Full URL to the original image.") # Using str for now, HttpUrl if validation is strict
    thumbnail_url: Optional[str] = Field(None, description="Full URL to the image thumbnail.") # Using str for now
    media_title: Optional[str] = Field(None, description="Title of the media item.")

    class Config:
        orm_mode = True

# Models for Products
class ProductBase(BaseModel):
    product_name: str = Field(..., description="Name of the product.")
    description: Optional[str] = Field(None, description="Description of the product.")
    category: Optional[str] = Field(None, description="Product category.")
    language_code: Optional[str] = Field("fr", description="Language code for the product details.")
    base_unit_price: Optional[float] = Field(None, description="Base unit price of the product.")
    unit_of_measure: Optional[str] = Field(None, description="Unit of measure (e.g., pcs, kg).")
    weight: Optional[float] = Field(None, description="Weight of the product.")
    dimensions: Optional[str] = Field(None, description="Dimensions of the product (e.g., LxWxH cm).")
    is_active: Optional[bool] = Field(True, description="Whether the product is currently active.")

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel): # Allow partial updates
    product_name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    language_code: Optional[str] = None
    base_unit_price: Optional[float] = None
    unit_of_measure: Optional[str] = None
    weight: Optional[float] = None
    dimensions: Optional[str] = None
    is_active: Optional[bool] = None

class ProductResponse(ProductBase):
    product_id: int = Field(..., description="Unique identifier for the product.")
    media_links: List[ProductImageLinkResponse] = Field([], description="List of associated media items (images).")
    # created_at: Optional[datetime] # Example, if you add timestamps
    # updated_at: Optional[datetime]

    class Config:
        orm_mode = True

# Request model for linking an existing MediaItem to a product
class LinkMediaToProductRequest(BaseModel):
    media_item_id: str = Field(..., description="The ID of the MediaItem to link.")
    display_order: Optional[int] = Field(0, description="Desired display order for this media.")
    alt_text: Optional[str] = Field(None, description="Alternative text for this media link.")

class ReorderProductMediaLinksRequest(BaseModel):
    ordered_media_item_ids: List[str] = Field(..., description="List of media_item_ids in the new desired display order.")

# Models for Invoices
class InvoiceBase(BaseModel):
    client_id: str
    project_id: Optional[str] = None
    document_id: Optional[str] = None
    invoice_number: str
    issue_date: date
    due_date: date
    total_amount: float
    currency: str
    payment_status: Optional[str] = "unpaid"
    payment_date: Optional[date] = None
    payment_method: Optional[str] = None
    transaction_id: Optional[str] = None
    notes: Optional[str] = None

class InvoiceCreate(InvoiceBase):
    pass

class InvoiceUpdate(BaseModel):
    client_id: Optional[str] = None
    project_id: Optional[str] = None
    document_id: Optional[str] = None
    invoice_number: Optional[str] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = None
    payment_status: Optional[str] = None
    payment_date: Optional[date] = None
    payment_method: Optional[str] = None
    transaction_id: Optional[str] = None
    notes: Optional[str] = None

class Invoice(InvoiceBase):
    invoice_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
