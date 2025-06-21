import uuid
import enum
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, ForeignKey, Enum as SQLAlchemyEnum, UniqueConstraint, Boolean, Date, Table
from sqlalchemy.orm import relationship, sessionmaker, declarative_base
from sqlalchemy.sql import func
from pydantic import BaseModel, Field, EmailStr
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


class Employee(Base):
    __tablename__ = "employees"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    phone_number = Column(String, nullable=True)
    position = Column(String, nullable=True)
    department = Column(String, nullable=True)
    salary = Column(Float, nullable=True)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<Employee(id={self.id}, email='{self.email}')>"


# SQLAlchemy Models for Leave Management

class LeaveType(Base):
    __tablename__ = "leave_types"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    default_days_entitled = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<LeaveType(id={self.id}, name='{self.name}')>"

class LeaveBalance(Base):
    __tablename__ = "leave_balances"
    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(String, ForeignKey("employees.id"), nullable=False, index=True)
    leave_type_id = Column(Integer, ForeignKey("leave_types.id"), nullable=False, index=True)
    year = Column(Integer, nullable=False) # e.g., 2023, 2024
    entitled_days = Column(Float, nullable=False)
    used_days = Column(Float, nullable=False, default=0.0)

    employee = relationship("Employee")
    leave_type = relationship("LeaveType")

    __table_args__ = (UniqueConstraint('employee_id', 'leave_type_id', 'year', name='uq_employee_leave_year'),)

    def __repr__(self):
        return f"<LeaveBalance(id={self.id}, employee_id='{self.employee_id}', leave_type_id={self.leave_type_id}, year={self.year})>"

class LeaveRequestStatusEnum(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(String, ForeignKey("employees.id"), nullable=False, index=True)
    leave_type_id = Column(Integer, ForeignKey("leave_types.id"), nullable=False, index=True)
    status = Column(SQLAlchemyEnum(LeaveRequestStatusEnum), nullable=False, default=LeaveRequestStatusEnum.PENDING, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=True)
    num_days = Column(Float, nullable=False) # Calculated, can be stored or computed
    request_date = Column(DateTime, server_default=func.now(), nullable=False)
    approved_by_id = Column(String, ForeignKey("users.id"), nullable=True) # Assuming User model exists
    processed_date = Column(DateTime, nullable=True)
    comments = Column(Text, nullable=True) # For approver's comments

    employee = relationship("Employee")
    leave_type = relationship("LeaveType")
    approved_by = relationship("User") # Adjust if User model name/key is different

    def __repr__(self):
        return f"<LeaveRequest(id={self.id}, employee_id='{self.employee_id}', status='{self.status.value if self.status else None}')>"


# SQLAlchemy Models for Performance Review Module

class GoalStatusEnum(enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"

class Goal(Base):
    __tablename__ = "goals"
    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(String, ForeignKey("employees.id"), nullable=False, index=True)
    set_by_id = Column(String, ForeignKey("users.id"), nullable=True) # Manager/user who set the goal
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(Date, nullable=True)
    status = Column(SQLAlchemyEnum(GoalStatusEnum), nullable=False, default=GoalStatusEnum.OPEN, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    employee = relationship("Employee")
    set_by = relationship("User")

    def __repr__(self):
        return f"<Goal(id={self.id}, title='{self.title}', employee_id='{self.employee_id}')>"

class ReviewCycle(Base):
    __tablename__ = "review_cycles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<ReviewCycle(id={self.id}, name='{self.name}')>"

class PerformanceReviewStatusEnum(enum.Enum):
    DRAFT = "draft"
    PENDING_EMPLOYEE_INPUT = "pending_employee_input"
    PENDING_MANAGER_REVIEW = "pending_manager_review"
    PENDING_FINAL_DISCUSSION = "pending_final_discussion"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

# Association table for PerformanceReview and Goal (Many-to-Many)
performance_review_goals_link = Table('performance_review_goals_link', Base.metadata,
    Column('performance_review_id', Integer, ForeignKey('performance_reviews.id'), primary_key=True),
    Column('goal_id', Integer, ForeignKey('goals.id'), primary_key=True)
)

class PerformanceReview(Base):
    __tablename__ = "performance_reviews"
    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(String, ForeignKey("employees.id"), nullable=False, index=True)
    reviewer_id = Column(String, ForeignKey("users.id"), nullable=True) # Typically the manager
    review_cycle_id = Column(Integer, ForeignKey("review_cycles.id"), nullable=True)
    review_date = Column(Date, nullable=True) # Date of the review meeting/finalization
    overall_rating = Column(Integer, nullable=True) # E.g., 1-5 scale
    strengths = Column(Text, nullable=True)
    areas_for_improvement = Column(Text, nullable=True)
    employee_comments = Column(Text, nullable=True)
    manager_comments = Column(Text, nullable=True)
    status = Column(SQLAlchemyEnum(PerformanceReviewStatusEnum), nullable=False, default=PerformanceReviewStatusEnum.DRAFT, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    employee = relationship("Employee")
    reviewer = relationship("User")
    review_cycle = relationship("ReviewCycle")
    goals_reviewed = relationship("Goal", secondary=performance_review_goals_link, backref="performance_reviews")

    def __repr__(self):
        return f"<PerformanceReview(id={self.id}, employee_id='{self.employee_id}', status='{self.status.value if self.status else None}')>"


# SQLAlchemy Models for Employee Document Management

class DocumentCategory(Base):
    __tablename__ = "document_categories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)

    def __repr__(self):
        return f"<DocumentCategory(id={self.id}, name='{self.name}')>"

class EmployeeDocument(Base):
    __tablename__ = "employee_documents"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    employee_id = Column(String, ForeignKey("employees.id"), nullable=False, index=True)
    document_category_id = Column(Integer, ForeignKey("document_categories.id"), nullable=True)

    file_name = Column(String, nullable=False)  # Original name of the uploaded file
    file_path_or_key = Column(String, nullable=False) # Path if local, or key if cloud (S3)
    file_type = Column(String, nullable=True)   # MIME type, e.g., "application/pdf"
    file_size = Column(Integer, nullable=True)  # Size in bytes

    description = Column(Text, nullable=True)   # User-provided description
    uploaded_at = Column(DateTime, server_default=func.now(), nullable=False)
    uploaded_by_id = Column(String, ForeignKey("users.id"), nullable=True)

    employee = relationship("Employee")
    document_category = relationship("DocumentCategory")
    uploaded_by = relationship("User")

    def __repr__(self):
        return f"<EmployeeDocument(id='{self.id}', file_name='{self.file_name}', employee_id='{self.employee_id}')>"


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

class TemplateVisibilityInfo(BaseModel):
    template_id: int # Matches TemplateInfo.template_id and DB schema
    template_name: Optional[str] = None
    description: Optional[str] = None
    template_type: Optional[str] = None
    language_code: Optional[str] = None
    is_visible: bool

class UpdateTemplateVisibilityItem(BaseModel):
    template_id: int # Matches TemplateInfo.template_id
    is_visible: bool

class UpdateTemplateVisibilityRequest(BaseModel):
    preferences: List[UpdateTemplateVisibilityItem]

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

# --- Company Facture Models (Added for Expense Management) ---

class CompanyFactureBasePydantic(BaseModel): # Renamed to avoid conflict if a SQLAlchemy model with same name exists
    original_file_name: str = Field(..., example="facture_proveedor_XYZ_2023-10-28.pdf")
    stored_file_path: str = Field(..., example="/secure_storage/factures/facture_proveedor_XYZ_2023-10-28_uuid.pdf")
    file_mime_type: Optional[str] = Field(None, example="application/pdf")
    extraction_status: str = Field(default='pending_review', example="pending_review")
    extracted_data_json: Optional[str] = Field(None, example='{"amount": "120.50", "date": "2023-10-25", "vendor": "Proveedor XYZ"}')

class CompanyFactureCreatePydantic(CompanyFactureBasePydantic):
    pass

class CompanyFactureReadPydantic(CompanyFactureBasePydantic):
    facture_id: int
    upload_date: datetime
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False # Include soft delete status

    class Config:
        from_attributes = True # Changed from orm_mode for Pydantic v2 compatibility if needed, but from_attributes is better.

class CompanyFactureUpdatePydantic(BaseModel):
    original_file_name: Optional[str] = None
    stored_file_path: Optional[str] = None
    file_mime_type: Optional[str] = None
    extraction_status: Optional[str] = None
    extracted_data_json: Optional[str] = None


# --- Company Expense Models (Added for Expense Management) ---

class CompanyExpenseBasePydantic(BaseModel): # Renamed
    expense_date: date = Field(..., example="2023-10-28")
    amount: float = Field(..., gt=0, example=120.50)
    currency: str = Field(..., min_length=3, max_length=3, example="USD")
    recipient_name: str = Field(..., example="Proveedor XYZ S.A.")
    description: Optional[str] = Field(None, example="Monthly subscription for accounting software")

class CompanyExpenseCreatePydantic(CompanyExpenseBasePydantic):
    facture_id: Optional[int] = None # Can be created without a facture initially

class CompanyExpenseReadPydantic(CompanyExpenseBasePydantic):
    expense_id: int
    facture_id: Optional[int] = None
    created_by_user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False # Include soft delete status
    facture: Optional[CompanyFactureReadPydantic] = None # To hold linked facture details

    class Config:
        from_attributes = True

class CompanyExpenseUpdatePydantic(BaseModel):
    expense_date: Optional[date] = None
    amount: Optional[float] = Field(None, gt=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    recipient_name: Optional[str] = None
    description: Optional[str] = None
    # To update/link a facture, use a dedicated endpoint or ensure this field is handled carefully.
    # Explicitly allowing facture_id to be set to None to unlink.
    facture_id: Optional[int] = Field(None, allow_none=True)


# For linking a facture to an expense via an existing expense
class LinkFactureToExpenseRequestPydantic(BaseModel): # Renamed
    facture_id: int


# Pydantic Models for HR Reporting Responses

class HeadcountReportItem(BaseModel):
    department: Optional[str] = "N/A" # Department name, or "N/A" if not set
    count: int

class HeadcountReportResponse(BaseModel):
    report_name: str = "Department Headcount"
    generated_at: datetime # from datetime import datetime
    data: List[HeadcountReportItem]

class AnniversaryReportItem(BaseModel):
    employee_id: str # UUID as string
    full_name: str # Combine first_name and last_name
    anniversary_date: date # The upcoming anniversary date, from datetime import date
    years_of_service: int

class AnniversaryReportResponse(BaseModel):
    report_name: str = "Upcoming Work Anniversaries"
    generated_at: datetime # from datetime import datetime
    time_window_days: int # The number of upcoming days the report covers (e.g., 30, 60)
    data: List[AnniversaryReportItem]

class LeaveSummaryReportItem(BaseModel):
    leave_type_name: str
    total_days_taken_or_requested: float # Could be approved days, or pending days depending on query
    number_of_requests: int

class LeaveSummaryReportResponse(BaseModel):
    report_name: str = "Leave Summary"
    generated_at: datetime # from datetime import datetime
    filter_status: Optional[str] = None # e.g., "approved", "pending"
    data: List[LeaveSummaryReportItem]


# Pydantic Models for Employee
class EmployeeBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    position: Optional[str] = None
    department: Optional[str] = None
    salary: Optional[float] = None
    start_date: date
    end_date: Optional[date] = None
    is_active: bool = True

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    position: Optional[str] = None
    department: Optional[str] = None
    salary: Optional[float] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None

class EmployeeResponse(EmployeeBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Pydantic Models for Employee Document Management

# DocumentCategory
class DocumentCategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class DocumentCategoryCreate(DocumentCategoryBase):
    pass

class DocumentCategoryResponse(DocumentCategoryBase):
    id: int

    class Config:
        from_attributes = True

# EmployeeDocument
class EmployeeDocumentBase(BaseModel):
    employee_id: str # UUID as string, matches Employee.id
    document_category_id: Optional[int] = None
    description: Optional[str] = None
    # file_name, file_path_or_key, file_type, file_size are typically set by server during upload

class EmployeeDocumentCreate(EmployeeDocumentBase):
    # This model is for creating the metadata record.
    # Actual file upload might be handled separately (e.g. FastAPI UploadFile)
    # and these fields would be populated by the server.
    # If client needs to send filename, it can be added here.
    pass

class EmployeeDocumentUpdate(BaseModel):
    document_category_id: Optional[int] = None
    description: Optional[str] = None

class EmployeeDocumentResponse(EmployeeDocumentBase):
    id: str # UUID as string
    file_name: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None # in bytes
    uploaded_at: datetime # from datetime import datetime
    uploaded_by_id: Optional[str] = None # UUID as string for User.id

    document_category: Optional[DocumentCategoryResponse] = None # Nested
    employee: Optional[EmployeeResponse] = None # Optional for context, EmployeeResponse already defined

    download_url: Optional[str] = None # To be constructed by API endpoint logic

    class Config:
        from_attributes = True


# Pydantic Models for Performance Review Module

# Goal
class GoalBase(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[date] = None # from datetime import date
    status: Optional[str] = Field(GoalStatusEnum.OPEN.value, description="Status of the goal")

class GoalCreate(GoalBase):
    employee_id: str # Employee this goal is for (UUID as string)
    set_by_id: Optional[str] = None # User who set goal (UUID as string), can be inferred from current_user

class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[date] = None
    status: Optional[str] = None # Allow updating status, should map to GoalStatusEnum values

class GoalResponse(GoalBase):
    id: int
    employee_id: str # UUID as string
    set_by_id: Optional[str] = None # UUID as string
    created_at: datetime # from datetime import datetime
    updated_at: datetime # from datetime import datetime
    employee: Optional[EmployeeResponse] = None # Optional nesting

    class Config:
        from_attributes = True

# ReviewCycle
class ReviewCycleBase(BaseModel):
    name: str
    start_date: date # from datetime import date
    end_date: date   # from datetime import date
    is_active: Optional[bool] = True

class ReviewCycleCreate(ReviewCycleBase):
    pass

class ReviewCycleUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None

class ReviewCycleResponse(ReviewCycleBase):
    id: int

    class Config:
        from_attributes = True

# PerformanceReview
class PerformanceReviewBase(BaseModel):
    review_cycle_id: Optional[int] = None
    review_date: Optional[date] = None # from datetime import date
    overall_rating: Optional[int] = Field(None, ge=1, le=5) # Example 1-5 rating
    strengths: Optional[str] = None
    areas_for_improvement: Optional[str] = None
    employee_comments: Optional[str] = None
    manager_comments: Optional[str] = None
    status: Optional[str] = Field(PerformanceReviewStatusEnum.DRAFT.value, description="Status of the review")

class PerformanceReviewCreate(PerformanceReviewBase):
    employee_id: str # UUID as string
    reviewer_id: Optional[str] = None # Manager (UUID as string), can be inferred or set

class PerformanceReviewUpdate(BaseModel): # Fields that can be updated at different stages
    review_cycle_id: Optional[int] = None
    review_date: Optional[date] = None
    overall_rating: Optional[int] = Field(None, ge=1, le=5)
    strengths: Optional[str] = None
    areas_for_improvement: Optional[str] = None
    employee_comments: Optional[str] = None
    manager_comments: Optional[str] = None
    status: Optional[str] = None # Should map to PerformanceReviewStatusEnum values
    goal_ids_to_link: Optional[List[int]] = None # For linking goals to review
    goal_ids_to_unlink: Optional[List[int]] = None # For unlinking goals

class PerformanceReviewResponse(PerformanceReviewBase):
    id: int
    employee_id: str # UUID as string
    reviewer_id: Optional[str] = None # UUID as string
    created_at: datetime # from datetime import datetime
    updated_at: datetime # from datetime import datetime
    employee: Optional[EmployeeResponse] = None # Optional nesting
    reviewer: Optional[UserInDB] = None # Optional nesting for reviewer info (UserInDB defined in this file)
    review_cycle: Optional[ReviewCycleResponse] = None # Optional nesting
    goals_reviewed: List[GoalResponse] = [] # List of linked goals

    class Config:
        from_attributes = True


# Pydantic Models for Leave Management

# LeaveType
class LeaveTypeBase(BaseModel):
    name: str
    default_days_entitled: Optional[int] = None

class LeaveTypeCreate(LeaveTypeBase):
    pass

class LeaveTypeResponse(LeaveTypeBase):
    id: int

    class Config:
        from_attributes = True

# LeaveBalance
class LeaveBalanceBase(BaseModel):
    employee_id: str # UUID as string
    leave_type_id: int
    year: int
    entitled_days: float
    used_days: float = 0.0

class LeaveBalanceCreate(LeaveBalanceBase):
    pass

class LeaveBalanceUpdate(BaseModel):
    entitled_days: Optional[float] = None
    used_days: Optional[float] = None

class LeaveBalanceResponse(LeaveBalanceBase):
    id: int
    leave_type: LeaveTypeResponse
    employee: EmployeeResponse # Nested Employee details

    class Config:
        from_attributes = True

# LeaveRequest
class LeaveRequestBase(BaseModel):
    leave_type_id: int
    start_date: date # from datetime import date
    end_date: date   # from datetime import date
    reason: Optional[str] = None
    num_days: float # Client might send this, or API calculates it

class LeaveRequestCreate(LeaveRequestBase):
    # employee_id will be set from path or current user, not in request body typically
    pass

class LeaveRequestUpdate(BaseModel): # For admin/manager to update status/comments
    status: Optional[str] = None # Should map to LeaveRequestStatusEnum values
    comments: Optional[str] = None

class LeaveRequestResponse(LeaveRequestBase):
    id: int
    employee_id: str # UUID as string
    status: str # Enum value as string
    request_date: datetime # from datetime import datetime
    approved_by_id: Optional[str] = None # UUID as string
    processed_date: Optional[datetime] = None
    comments: Optional[str] = None
    leave_type: LeaveTypeResponse # Nested LeaveType details
    employee: EmployeeResponse    # Nested Employee details

    class Config:
        from_attributes = True


# Pydantic Models for Employee
class EmployeeBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    position: Optional[str] = None
    department: Optional[str] = None
    salary: Optional[float] = None
    start_date: date
    end_date: Optional[date] = None
    is_active: bool = True

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    position: Optional[str] = None
    department: Optional[str] = None
    salary: Optional[float] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None

class EmployeeResponse(EmployeeBase):
    id: str
    created_at: datetime
    updated_at: datetime

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
