import uuid
import enum
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, ForeignKey, Enum as SQLAlchemyEnum, UniqueConstraint, Boolean
from sqlalchemy.orm import relationship, sessionmaker, declarative_base
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime

from typing import Optional, List, Dict, Any # Keep existing Pydantic imports for now

# SQLAlchemy Base
Base = declarative_base()

# Placeholder SQLAlchemy models for existing entities
# These should be replaced with actual definitions if they exist elsewhere
# or be fully defined here.

class User(Base): # Assuming User model might be needed for created_by/modified_by later
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4())) # user_id in schema is TEXT
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False) # Changed nullable to False
    password_hash = Column(String, nullable=False)
    salt = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_deleted = Column(Integer, default=0, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    # Example relationship (if users create proformas, not directly requested but good for structure)
    # proforma_invoices_created = relationship("ProformaInvoice", back_populates="created_by_user")


class Client(Base):
    __tablename__ = "clients"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    # Relationships
    proforma_invoices = relationship("ProformaInvoice", order_by="ProformaInvoice.id", back_populates="client")
    # client_documents = relationship("ClientDocument", back_populates="client") # If ClientDocument links back to Client

class Project(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    client_id = Column(String, ForeignKey("clients.id"))
    # Relationships
    proforma_invoices = relationship("ProformaInvoice", order_by="ProformaInvoice.id", back_populates="project")

class Company(Base): # Represents the user's company (seller)
    __tablename__ = "companies"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    # Relationships
    proforma_invoices = relationship("ProformaInvoice", order_by="ProformaInvoice.id", back_populates="company")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=True)
    language_code = Column(String, default='fr', nullable=False)
    base_unit_price = Column(Float, nullable=False)
    unit_of_measure = Column(String, nullable=True)
    weight = Column(Float, nullable=True)
    dimensions = Column(Text, nullable=True) # Using Text for dimensions
    is_active = Column(Boolean, default=True, nullable=False)
    is_deleted = Column(Integer, default=0, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (UniqueConstraint('product_name', 'language_code', name='uq_product_name_language'),)
    # No back_populates to ProformaInvoiceItem unless specified, as one product can be in many items

class ClientDocument(Base): # For storing generated PDFs like Proformas or Invoices
    __tablename__ = "client_documents"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    document_type = Column(String) # e.g., "proforma_invoice", "final_invoice"
    file_path = Column(String) # Path to the stored document
    client_id = Column(String, ForeignKey("clients.id"), nullable=True) # Optional: link document to client
    # client = relationship("Client", back_populates="client_documents") # If ClientDocument links back to Client

# Enum for ProformaInvoice status
class ProformaInvoiceStatusEnum(enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    INVOICED = "invoiced"
    CANCELLED = "cancelled"

# ProformaInvoice Model
class ProformaInvoice(Base):
    __tablename__ = "proforma_invoices"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    proforma_invoice_number = Column(String, unique=True, index=True, nullable=False)
    client_id = Column(String, ForeignKey("clients.id"), nullable=False, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=True, index=True)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True) # The seller

    created_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sent_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(SQLAlchemyEnum(ProformaInvoiceStatusEnum), nullable=False, default=ProformaInvoiceStatusEnum.DRAFT, index=True)

    currency = Column(String(3), nullable=False, default="USD")
    subtotal_amount = Column(Float, nullable=False, default=0.0)
    discount_amount = Column(Float, nullable=True, default=0.0)
    vat_amount = Column(Float, nullable=False, default=0.0)
    grand_total_amount = Column(Float, nullable=False, default=0.0)

    payment_terms = Column(String, nullable=True)
    delivery_terms = Column(String, nullable=True)
    incoterms = Column(String, nullable=True)
    named_place_of_delivery = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    linked_document_id = Column(String, ForeignKey("client_documents.id"), nullable=True)
    generated_invoice_id = Column(String, ForeignKey("client_documents.id"), nullable=True)

    # Relationships
    client = relationship("Client", back_populates="proforma_invoices")
    project = relationship("Project", back_populates="proforma_invoices")
    company = relationship("Company", back_populates="proforma_invoices")

    items = relationship("ProformaInvoiceItem", back_populates="proforma_invoice", cascade="all, delete-orphan")
    linked_document = relationship("ClientDocument", foreign_keys=[linked_document_id])
    generated_invoice_document = relationship("ClientDocument", foreign_keys=[generated_invoice_id])

# ProformaInvoiceItem Model
class ProformaInvoiceItem(Base):
    __tablename__ = "proforma_invoice_items"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    proforma_invoice_id = Column(String, ForeignKey("proforma_invoices.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True) # Nullable if custom item
    description = Column(Text, nullable=False)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False) # quantity * unit_price

    # Relationships
    proforma_invoice = relationship("ProformaInvoice", back_populates="items")
    product = relationship("Product") # No back_populates needed on Product for this item


class Contact(Base):
    __tablename__ = "contacts"

    contact_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=True)
    phone = Column(String, nullable=True)
    position = Column(String, nullable=True)
    company_name = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    givenName = Column(String, nullable=True)
    familyName = Column(String, nullable=True)
    displayName = Column(String, nullable=True)
    phone_type = Column(String, nullable=True)
    email_type = Column(String, nullable=True)
    address_formattedValue = Column(String, nullable=True)
    address_streetAddress = Column(String, nullable=True)
    address_city = Column(String, nullable=True)
    address_region = Column(String, nullable=True)
    address_postalCode = Column(String, nullable=True)
    address_country = Column(String, nullable=True)
    organization_name = Column(String, nullable=True)
    organization_title = Column(String, nullable=True)
    birthday_date = Column(String, nullable=True) # SQLite stores dates as TEXT
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<Contact(contact_id={self.contact_id}, name='{self.name}', email='{self.email}')>"


# --- Existing Pydantic Models Below ---
# It's unusual to mix SQLAlchemy and Pydantic models in the same file this way,
# but adhering to the subtask's request to modify api/models.py.
# Consider separating them into different files/modules in a real application.

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
    line_items: Optional[List[Dict[str, Any]]] = Field(None, description="List of line items, e.g., products with quantities and prices")
    additional_context: Optional[Dict[str, Any]] = Field(None, description="Other context-specific data needed for the document")

class DocumentGenerationResponse(BaseModel):
    message: str = Field(..., description="Status message of the generation process")
    document_id: Optional[str] = Field(None, description="Unique ID of the generated document record in the database")
    client_id: str = Field(..., description="ID of the client for whom the document was generated")
    file_name: Optional[str] = Field(None, description="Name of the generated file")
    download_url: Optional[str] = Field(None, description="URL to download the generated document")

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
    image_url: Optional[str] = Field(None, description="Full URL to the original image.")
    thumbnail_url: Optional[str] = Field(None, description="Full URL to the image thumbnail.")
    media_title: Optional[str] = Field(None, description="Title of the media item.")

    class Config:
        from_attributes = True

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
    product_code: str = Field(..., description="Unique code for the product.")

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    product_code: Optional[str] = None
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
    product_id: int = Field(..., description="Unique identifier for the product.") # This was int, but Product SQLAlchemy model uses String ID.
    media_links: List[ProductImageLinkResponse] = Field([], description="List of associated media items (images).")
    # product_code will be inherited from ProductBase and is required.

    class Config:
        from_attributes = True

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
        from_attributes = True
