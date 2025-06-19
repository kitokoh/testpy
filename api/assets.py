from typing import List, Optional
from datetime import datetime, date
import sqlite3 # Added for exception handling in endpoints

from pydantic import BaseModel, ConfigDict
from fastapi import APIRouter, HTTPException, Depends, status, Response

import shutil
import tempfile
import os

# Assuming these imports are valid for the project structure
from ..db.cruds.company_assets_crud import company_assets_crud
from ..db.cruds.asset_assignments_crud import asset_assignments_crud
from ..db.cruds.asset_media_links_crud import asset_media_links_crud
# from ..db.cruds.media_items_crud import media_items_crud # Assuming this might exist for validating media_item_id
from ..models.user_models import User # Standardized path
from .auth import get_current_active_user # Standardized path
from media_manager import operations as media_manager_operations # Assumed import
from fastapi import UploadFile, File, Form


# Initialize API Router
router = APIRouter(
    prefix="/assets",
    tags=["Assets Management"],
    responses={404: {"description": "Not found"}},
)

# --- Asset Models ---

class CompanyAssetBase(BaseModel):
    asset_name: str
    asset_type: str
    serial_number: Optional[str] = None
    description: Optional[str] = None
    purchase_date: Optional[date] = None
    purchase_value: Optional[float] = None
    current_status: str
    notes: Optional[str] = None

class CompanyAssetCreate(CompanyAssetBase):
    pass

class CompanyAssetUpdate(BaseModel):
    asset_name: Optional[str] = None
    asset_type: Optional[str] = None
    serial_number: Optional[str] = None
    description: Optional[str] = None
    purchase_date: Optional[date] = None
    purchase_value: Optional[float] = None
    current_status: Optional[str] = None
    notes: Optional[str] = None

class CompanyAsset(CompanyAssetBase):
    asset_id: str  # UUID
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False # Default to False for active records, reflects DB state if fetched with include_deleted

    model_config = ConfigDict(from_attributes=True)


# --- Assignment Models ---

class AssetAssignmentBase(BaseModel):
    asset_id: str  # UUID
    personnel_id: int
    assignment_date: datetime
    expected_return_date: Optional[datetime] = None
    assignment_status: str  # e.g., 'Active', 'Returned', 'Pending Maintenance'
    notes: Optional[str] = None

class AssetAssignmentCreate(AssetAssignmentBase):
    pass

class AssetAssignmentUpdate(BaseModel):
    expected_return_date: Optional[datetime] = None
    actual_return_date: Optional[datetime] = None
    assignment_status: Optional[str] = None
    notes: Optional[str] = None

class AssetAssignment(AssetAssignmentBase):
    assignment_id: str  # UUID
    actual_return_date: Optional[datetime] = None # Included from base, but explicitly listed for clarity
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Asset Media Link Models ---

class AssetMediaLinkBase(BaseModel):
    media_item_id: str  # UUID
    alt_text: Optional[str] = None
    display_order: int = 0 # Changed to non-optional with default as per prompt

class AssetMediaLinkCreate(AssetMediaLinkBase):
    pass # asset_id will be a path parameter typically

class AssetMediaLink(AssetMediaLinkBase):
    link_id: int
    asset_id: str  # UUID
    created_at: datetime

    # Fields populated from joined MediaItem table by the CRUD method
    media_title: Optional[str] = None
    media_item_type: Optional[str] = None
    media_thumbnail_path: Optional[str] = None
    # Could also include media_filepath or media_url if needed for direct linking

    model_config = ConfigDict(from_attributes=True)

# --- Media Upload Model (Convenience for combined operations) ---

class AssetMediaUpload(BaseModel):
    """
    Represents data for uploading a new media file and linking it to an asset.
    The actual file upload will be handled by FastAPI's UploadFile.
    This model is for metadata associated with the upload and link.
    """
    title: str
    description: Optional[str] = None
    alt_text: Optional[str] = None # For the AssetMediaLink
    display_order: int = 0 # For the AssetMediaLink, changed to non-optional with default
    tags: Optional[List[str]] = None # For the MediaItem

# Example placeholder for where endpoints would go:
# @router.post("/", response_model=CompanyAsset)
# async def create_asset(asset: CompanyAssetCreate):
#     # ... logic to create asset ...
#     return asset_db_object


# --- Asset Endpoints ---

@router.post("/", response_model=CompanyAsset, status_code=status.HTTP_201_CREATED)
async def create_company_asset(
    asset_in: CompanyAssetCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new company asset.
    - `asset_name`: Name of the asset.
    - `asset_type`: Type of asset (e.g., Laptop, Monitor, Software License).
    - `serial_number`: Unique serial number (optional).
    - `description`: Detailed description (optional).
    - `purchase_date`: Date of purchase (optional).
    - `purchase_value`: Value at purchase (optional).
    - `current_status`: Current operational status (e.g., In Use, In Stock, Disposed).
    - `notes`: Additional notes (optional).
    """
    asset_data = asset_in.model_dump(exclude_unset=True)
    try:
        asset_id = company_assets_crud.add_asset(asset_data)
        if not asset_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create asset due to invalid data or pre-check failure.")
    except sqlite3.IntegrityError as e:
        detail = "Failed to create asset. A similar asset (e.g., duplicate serial number) might already exist."
        # Check if the specific error is due to serial number uniqueness
        # Note: Error message string checking is fragile. Better if CRUD raises specific custom exceptions.
        if "companyassets.serial_number" in str(e).lower() and "unique constraint failed" in str(e).lower():
            detail = "An asset with this serial number already exists."
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    except Exception as e:
        # log.error(f"Unexpected error creating asset: {e}", exc_info=True) # Consider more detailed logging
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while creating the asset.")

    created_asset_db = company_assets_crud.get_asset_by_id(asset_id)
    if not created_asset_db:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Asset created but could not be retrieved.")

    return CompanyAsset.model_validate(created_asset_db)


@router.get("/", response_model=List[CompanyAsset])
async def list_company_assets(
    asset_type: Optional[str] = None,
    current_status: Optional[str] = None,
    serial_number: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    include_deleted: bool = False,
    current_user: User = Depends(get_current_active_user)
):
    """
    List all company assets with optional filtering and pagination.
    - `asset_type`: Filter by asset type.
    - `current_status`: Filter by current status.
    - `serial_number`: Filter by serial number.
    - `limit`: Maximum number of assets to return.
    - `offset`: Number of assets to skip.
    - `include_deleted`: Whether to include soft-deleted assets.
    """
    filters = {}
    if asset_type:
        filters["asset_type"] = asset_type
    if current_status:
        filters["current_status"] = current_status
    if serial_number:
        filters["serial_number"] = serial_number

    assets_db = company_assets_crud.get_assets(
        filters=filters, limit=limit, offset=offset, include_deleted=include_deleted
    )
    return [CompanyAsset.model_validate(asset) for asset in assets_db]


@router.get("/{asset_id}", response_model=CompanyAsset)
async def get_company_asset(
    asset_id: str,
    include_deleted: bool = False,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific company asset by its ID.
    - `asset_id`: The UUID of the asset.
    - `include_deleted`: Set to true to fetch the asset even if it has been soft-deleted.
    """
    asset_db = company_assets_crud.get_asset_by_id(asset_id, include_deleted=include_deleted)
    if not asset_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return CompanyAsset.model_validate(asset_db)


@router.put("/{asset_id}", response_model=CompanyAsset)
async def update_company_asset(
    asset_id: str,
    asset_in: CompanyAssetUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Update an existing company asset.
    Fields in the request body are optional. Only provided fields will be updated.
    - `asset_id`: The UUID of the asset to update.
    """
    existing_asset = company_assets_crud.get_asset_by_id(asset_id, include_deleted=True) # Check even if deleted
    if not existing_asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    update_data = asset_in.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided.")

    # If trying to update a currently soft-deleted asset, it might involve "undeleting" it.
    # The CRUD `update_asset` handles `is_deleted` and `deleted_at` fields.
    if existing_asset.get('is_deleted') and 'is_deleted' not in update_data:
        # By default, if is_deleted is not in update_data, it won't be changed by CRUD.
        # If we want to prevent updates on deleted assets unless 'is_deleted' is explicitly set to False:
        # raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Asset is deleted. To update, first restore it or include 'is_deleted': false in your request.")
        pass # Current CRUD allows updating other fields of a soft-deleted asset.

    try:
        updated = company_assets_crud.update_asset(asset_id, update_data)
        if not updated:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update asset. Verify data or check for conflicts.")
    except sqlite3.IntegrityError as e:
        detail = "Failed to update asset due to a data conflict."
        if "companyassets.serial_number" in str(e).lower() and "unique constraint failed" in str(e).lower():
            detail = "An asset with the new serial number already exists."
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    except Exception as e:
        # log.error(f"Unexpected error updating asset {asset_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while updating the asset.")

    updated_asset_db = company_assets_crud.get_asset_by_id(asset_id, include_deleted=True) # Fetch with include_deleted to see current state
    if not updated_asset_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset updated but could not be retrieved.")

    return CompanyAsset.model_validate(updated_asset_db)


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_company_asset(
    asset_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Soft delete a company asset by its ID.
    This marks the asset as deleted but does not remove it from the database.
    - `asset_id`: The UUID of the asset to soft delete.
    """
    asset_to_delete = company_assets_crud.get_asset_by_id(asset_id, include_deleted=False)
    if not asset_to_delete:
        already_deleted_asset = company_assets_crud.get_asset_by_id(asset_id, include_deleted=True)
        if already_deleted_asset and already_deleted_asset.get('is_deleted'):
            return Response(status_code=status.HTTP_204_NO_CONTENT) # Idempotent: already deleted
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")

    deleted_successfully = company_assets_crud.delete_asset(asset_id)
    if not deleted_successfully:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to soft delete asset.")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Asset Assignment Endpoints ---

@router.post("/assignments/", response_model=AssetAssignment, status_code=status.HTTP_201_CREATED)
async def create_asset_assignment(
    assignment_in: AssetAssignmentCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new asset assignment.
    Links an asset to a personnel member.
    - `asset_id`: UUID of the asset to be assigned.
    - `personnel_id`: ID of the personnel member receiving the asset.
    - `assignment_date`: Date and time of the assignment.
    - `expected_return_date`: Optional date and time for expected return.
    - `assignment_status`: Status of the assignment (e.g., 'Active', 'Pending Pickup').
    - `notes`: Optional notes for the assignment.
    """
    # Optional: Pre-check if asset_id and personnel_id exist
    asset = company_assets_crud.get_asset_by_id(assignment_in.asset_id)
    if not asset or asset.get('is_deleted'): # Ensure asset exists and is not deleted
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset with ID '{assignment_in.asset_id}' not found or is deleted.")

    # Placeholder for personnel check - requires CompanyPersonnelCRUD
    # personnel = company_personnel_crud.get_personnel_by_id(assignment_in.personnel_id)
    # if not personnel:
    #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Personnel with ID '{assignment_in.personnel_id}' not found.")

    assignment_data = assignment_in.model_dump(exclude_unset=True)
    try:
        assignment_id = asset_assignments_crud.add_assignment(assignment_data)
        if not assignment_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create assignment due to invalid data.")
    except sqlite3.IntegrityError as e:
        # This typically means FK constraint failed if asset_id or personnel_id are invalid despite checks,
        # or other DB integrity rules.
        # logger.error(f"Integrity error creating assignment: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Failed to create assignment due to data conflict (e.g., invalid asset or personnel ID).")
    except Exception as e:
        # logger.error(f"Unexpected error creating assignment: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

    created_assignment_db = asset_assignments_crud.get_assignment_by_id(assignment_id)
    if not created_assignment_db:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Assignment created but could not be retrieved.")

    return AssetAssignment.model_validate(created_assignment_db)


@router.get("/assignments/{assignment_id}", response_model=AssetAssignment)
async def get_asset_assignment_by_id(
    assignment_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific asset assignment by its ID.
    - `assignment_id`: The UUID of the assignment.
    """
    assignment_db = asset_assignments_crud.get_assignment_by_id(assignment_id)
    if not assignment_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset assignment not found.")
    return AssetAssignment.model_validate(assignment_db)


@router.get("/assets/{asset_id}/assignments", response_model=List[AssetAssignment])
async def list_assignments_for_an_asset(
    asset_id: str,
    assignment_status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user)
):
    """
    List all assignments for a specific asset.
    - `asset_id`: UUID of the asset.
    - `assignment_status`: Filter by assignment status (optional).
    - `limit`: Maximum number of assignments to return.
    - `offset`: Number of assignments to skip.
    """
    # Check if asset exists
    asset = company_assets_crud.get_asset_by_id(asset_id, include_deleted=True) # Allow viewing assignments for deleted assets
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset with ID '{asset_id}' not found.")

    filters = {}
    if assignment_status:
        filters["assignment_status"] = assignment_status

    assignments_db = asset_assignments_crud.get_assignments_for_asset(
        asset_id=asset_id, filters=filters # Limit/offset not directly supported by this CRUD method, would need modification or do it in get_all_assignments
    )
    # For now, applying limit/offset post-fetch if CRUD doesn't support it directly for this specific query
    # This is inefficient for large datasets. CRUD should ideally handle pagination.
    paginated_assignments = assignments_db[offset : offset + limit]
    return [AssetAssignment.model_validate(assign) for assign in paginated_assignments]


@router.get("/personnel/{personnel_id}/assignments", response_model=List[AssetAssignment])
async def list_assignments_for_a_personnel(
    personnel_id: int,
    assignment_status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user)
):
    """
    List all assignments for a specific personnel member.
    - `personnel_id`: ID of the personnel member.
    - `assignment_status`: Filter by assignment status (optional).
    - `limit`: Maximum number of assignments to return.
    - `offset`: Number of assignments to skip.
    """
    # Placeholder: Check if personnel exists - requires CompanyPersonnelCRUD
    # personnel = company_personnel_crud.get_personnel_by_id(personnel_id)
    # if not personnel:
    #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Personnel with ID '{personnel_id}' not found.")

    filters = {}
    if assignment_status:
        filters["assignment_status"] = assignment_status

    assignments_db = asset_assignments_crud.get_assignments_for_personnel(
        personnel_id=personnel_id, filters=filters # Similar pagination concern as above
    )
    paginated_assignments = assignments_db[offset : offset + limit]
    return [AssetAssignment.model_validate(assign) for assign in paginated_assignments]


@router.put("/assignments/{assignment_id}", response_model=AssetAssignment)
async def update_asset_assignment(
    assignment_id: str,
    assignment_in: AssetAssignmentUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Update an existing asset assignment.
    Used for actions like recording return date, changing status, or adding notes.
    - `assignment_id`: UUID of the assignment to update.
    """
    existing_assignment = asset_assignments_crud.get_assignment_by_id(assignment_id)
    if not existing_assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset assignment not found.")

    update_data = assignment_in.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided.")

    try:
        updated = asset_assignments_crud.update_assignment(assignment_id, update_data)
        if not updated:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update assignment.")
    except Exception as e: # More specific exceptions could be caught from CRUD if defined
        # logger.error(f"Error updating assignment {assignment_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

    updated_assignment_db = asset_assignments_crud.get_assignment_by_id(assignment_id)
    if not updated_assignment_db:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment updated but could not be retrieved.")

    return AssetAssignment.model_validate(updated_assignment_db)


@router.get("/assignments/", response_model=List[AssetAssignment])
async def list_all_assignments(
    asset_id: Optional[str] = None,
    personnel_id: Optional[int] = None,
    assignment_status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user) # Potentially restrict to admin/manager roles
):
    """
    List all asset assignments, typically for admin or reporting purposes.
    Supports filtering by asset_id, personnel_id, and assignment_status.
    - `asset_id`: Filter by asset UUID (optional).
    - `personnel_id`: Filter by personnel ID (optional).
    - `assignment_status`: Filter by assignment status (optional).
    - `limit`: Maximum number of assignments to return.
    - `offset`: Number of assignments to skip.
    """
    filters = {}
    if asset_id:
        filters["asset_id"] = asset_id
    if personnel_id:
        filters["personnel_id"] = personnel_id
    if assignment_status:
        filters["assignment_status"] = assignment_status

    assignments_db = asset_assignments_crud.get_all_assignments(
        filters=filters, limit=limit, offset=offset
    )
    return [AssetAssignment.model_validate(assign) for assign in assignments_db]


# --- Asset Media Link Endpoints ---

@router.post("/assets/{asset_id}/media/link", response_model=AssetMediaLink, status_code=status.HTTP_201_CREATED)
async def link_media_item_to_asset(
    asset_id: str,
    link_in: AssetMediaLinkCreate, # Contains media_item_id, alt_text, display_order
    current_user: User = Depends(get_current_active_user)
):
    """
    Link an existing media item to an asset.
    - `asset_id`: UUID of the asset.
    - `media_item_id`: UUID of the media item to link.
    - `alt_text`: Optional alt text for the media in context of this asset.
    - `display_order`: Optional display order for the media on this asset.
    """
    # 1. Ensure asset exists
    asset = company_assets_crud.get_asset_by_id(asset_id)
    if not asset or asset.get('is_deleted'):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset with ID '{asset_id}' not found or is deleted.")

    # 2. Ensure media item exists (using media_manager_operations or a media_items_crud)
    # Assuming media_manager_operations.get_media_item_details(media_item_id) or similar exists
    # For now, we'll rely on DB FK constraint or assume media_item_id is validated by caller/frontend
    # Alternatively, a media_items_crud.get_by_id(link_in.media_item_id) could be used.
    # If not found, raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Media item with ID '{link_in.media_item_id}' not found.")

    # Example check (if media_items_crud existed):
    # media_item = media_items_crud.get_media_item_by_id(link_in.media_item_id)
    # if not media_item:
    #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"MediaItem with ID {link_in.media_item_id} not found.")


    try:
        link_id = asset_media_links_crud.link_media_to_asset(
            asset_id=asset_id,
            media_item_id=link_in.media_item_id,
            display_order=link_in.display_order,
            alt_text=link_in.alt_text
        )
        if not link_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to link media to asset.")
    except sqlite3.IntegrityError as e:
        # Handles FK violation if media_item_id is invalid, or duplicate link if (asset_id, media_item_id) is UNIQUE
        # logger.error(f"Integrity error linking media: {e}", exc_info=True)
        if "unique constraint failed: assetmedialinks.asset_id, assetmedialinks.media_item_id" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This media item is already linked to this asset.")
        if "foreign key constraint failed" in str(e).lower():
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Media item with ID '{link_in.media_item_id}' not found or asset ID invalid.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to link media due to data integrity issues.")
    except Exception as e:
        # logger.error(f"Unexpected error linking media: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

    # Fetch the created link with joined media details to match AssetMediaLink response model
    # The CRUD's get_media_links_for_asset already joins, but we need a single link.
    # A new CRUD method get_single_media_link_with_details(link_id) would be ideal.
    # For now, let's fetch all and filter, or make a simpler direct fetch.

    # Simpler: fetch the basic link, then try to augment it.
    # More robust: get_media_link_by_link_id and then separately get media_item details if not joined by default.
    # Best: a dedicated CRUD method get_asset_media_link_details_by_link_id(link_id)

    # Using existing get_media_link_by_link_id from the crud
    newly_created_link_db = asset_media_links_crud.get_media_link_by_link_id(link_id)
    if not newly_created_link_db:
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Media linked but could not be retrieved.")

    # Augment with media details for the response model (AssetMediaLink expects this)
    # This part ideally comes from a single efficient query in CRUD.
    # Assuming media_manager_operations.get_media_item_details exists
    media_details = {}
    try:
        # This is a placeholder for how you might get media details.
        # media_item_obj = media_manager_operations.get_media_item_details(newly_created_link_db["media_item_id"])
        # if media_item_obj:
        #    media_details["media_title"] = media_item_obj.get("title")
        #    media_details["media_item_type"] = media_item_obj.get("item_type")
        #    media_details["media_thumbnail_path"] = media_item_obj.get("thumbnail_path")
        # For now, we'll rely on what get_media_link_by_link_id provides, and AssetMediaLink model uses Optionals.
        # The get_media_links_for_asset method IS designed to provide these, so we could potentially use that and filter.
        all_links_for_asset = asset_media_links_crud.get_media_links_for_asset(asset_id)
        found_link_details = next((lnk for lnk in all_links_for_asset if lnk['link_id'] == link_id), None)
        if found_link_details:
            return AssetMediaLink.model_validate(found_link_details)

    except Exception: # Broad catch if media_manager fails or media item deleted post-link (race condition)
        # logger.error(f"Failed to fetch full media details for linked item {newly_created_link_db['media_item_id']}", exc_info=True)
        # Fallback to returning the basic link data if media details can't be fetched
        pass # This will return the object from get_media_link_by_link_id, which might miss joined fields

    return AssetMediaLink.model_validate(newly_created_link_db) # May not have all fields like media_title


@router.post("/assets/{asset_id}/media/upload", response_model=AssetMediaLink, status_code=status.HTTP_201_CREATED)
async def upload_new_media_and_link_to_asset(
    asset_id: str,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    alt_text: Optional[str] = Form(None), # For the AssetMediaLink
    display_order: int = Form(0),       # For the AssetMediaLink
    tags: Optional[List[str]] = Form(None), # For the MediaItem, FastAPI converts list-like form data
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload a new media file (image, video, document) and link it to an asset.
    - `asset_id`: UUID of the asset to link the new media to.
    - `file`: The media file to upload.
    - `title`: Title for the new media item.
    - `description`: Optional description for the media item.
    - `alt_text`: Optional alt text for this media specifically for this asset link.
    - `display_order`: Optional display order for this media on this asset.
    - `tags`: Optional list of tags for the new media item.
    """
    # 1. Ensure asset exists
    asset = company_assets_crud.get_asset_by_id(asset_id)
    if not asset or asset.get('is_deleted'):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset with ID '{asset_id}' not found or is deleted.")

    # 2. Save uploaded file temporarily
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, file.filename)
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        # logger.error(f"Failed to save temporary upload file: {e}", exc_info=True)
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process uploaded file.")
    finally:
        file.file.close() # Ensure the UploadFile stream is closed

    # 3. Determine media type (basic) and use media_manager to add file
    media_item_id = None
    try:
        content_type = file.content_type
        uploader_user_id = current_user.user_id # Assuming User model has user_id

        # This is a simplified interaction with media_manager_operations
        # Actual function names and parameters might vary.
        # add_media_item args: (user_id, file_path, title, description, item_type_hint, tags_list=None, **kwargs)
        # Assume it returns a dict or object with at least 'media_item_id'
        media_item_data = media_manager_operations.add_media_item(
            user_id=uploader_user_id,
            file_path=temp_file_path,
            title=title,
            description=description,
            item_type_hint=content_type, # Media manager might do more sophisticated type detection
            tags_list=tags if tags else []
        )
        if not media_item_data or "media_item_id" not in media_item_data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to add media to library.")
        media_item_id = media_item_data["media_item_id"]

    except Exception as e: # Catch errors from media_manager or file ops
        # logger.error(f"Error during media processing or adding to media_manager: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to process and store media: {str(e)}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True) # Clean up temp file/dir

    # 4. Link the new media_item_id to the asset_id
    if not media_item_id: # Should have been caught above, but defensive check
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Media item ID not obtained after upload.")

    try:
        link_id = asset_media_links_crud.link_media_to_asset(
            asset_id=asset_id,
            media_item_id=media_item_id,
            display_order=display_order,
            alt_text=alt_text
        )
        if not link_id:
            # This is an issue: media was saved, but linking failed. May need cleanup logic for orphaned media.
            # logger.error(f"Media item {media_item_id} created, but failed to link to asset {asset_id}.")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Media uploaded but failed to link to asset. Please check asset media links.")
    except sqlite3.IntegrityError: # e.g. if somehow this exact link was made by a race condition
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This media item (newly uploaded) seems already linked. This is unexpected.")
    except Exception as e:
        # logger.error(f"Unexpected error linking newly uploaded media: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error linking uploaded media.")

    # Fetch and return the created link with details
    all_links_for_asset = asset_media_links_crud.get_media_links_for_asset(asset_id)
    created_link_details = next((lnk for lnk in all_links_for_asset if lnk['link_id'] == link_id), None)
    if created_link_details:
        return AssetMediaLink.model_validate(created_link_details)
    else:
        # Fallback if somehow the detailed link isn't found immediately (should be rare)
        fallback_link = asset_media_links_crud.get_media_link_by_link_id(link_id)
        if fallback_link: return AssetMediaLink.model_validate(fallback_link) # Will miss joined media details
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Media uploaded and linked, but link details could not be fully retrieved.")


@router.get("/assets/{asset_id}/media", response_model=List[AssetMediaLink])
async def list_media_for_asset(
    asset_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    List all media linked to a specific asset.
    The response includes details from the MediaItems table.
    - `asset_id`: UUID of the asset.
    """
    asset = company_assets_crud.get_asset_by_id(asset_id, include_deleted=True) # Allow viewing media for deleted assets
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset with ID '{asset_id}' not found.")

    linked_media = asset_media_links_crud.get_media_links_for_asset(asset_id)
    return [AssetMediaLink.model_validate(lm) for lm in linked_media]


@router.delete("/assets/{asset_id}/media/{media_item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_media_item_from_asset(
    asset_id: str,
    media_item_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Unlink a media item from an asset. This does not delete the media item itself.
    - `asset_id`: UUID of the asset.
    - `media_item_id`: UUID of the media item to unlink.
    """
    # Check if asset exists (optional, as unlink_media_by_ids might just return 0 rows affected)
    # asset = company_assets_crud.get_asset_by_id(asset_id, include_deleted=True)
    # if not asset:
    #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset with ID '{asset_id}' not found.")

    # Check if the link exists before trying to delete
    link = asset_media_links_crud.get_media_link_by_ids(asset_id, media_item_id)
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media link not found for this asset and media item.")

    if not asset_media_links_crud.unlink_media_by_ids(asset_id, media_item_id):
        # This condition might be redundant if the check above is solid,
        # but good for catching unexpected failures in CRUD.
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to unlink media from asset.")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/assets/{asset_id}/media/order", response_model=List[AssetMediaLink])
async def update_asset_media_display_order(
    asset_id: str,
    ordered_media_item_ids: List[str], # List of media_item_ids in the new desired order
    current_user: User = Depends(get_current_active_user)
):
    """
    Update the display order of all media items linked to a specific asset.
    The request body should be a list of media_item_ids in the desired order.
    - `asset_id`: UUID of the asset.
    """
    asset = company_assets_crud.get_asset_by_id(asset_id, include_deleted=True)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset with ID '{asset_id}' not found.")

    # Optional: Validate that all media_item_ids in the list are currently linked to the asset.
    # current_links = asset_media_links_crud.get_media_links_for_asset(asset_id)
    # current_media_ids = {link['media_item_id'] for link in current_links}
    # for mid in ordered_media_item_ids:
    #     if mid not in current_media_ids:
    #         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Media item ID '{mid}' is not linked to asset '{asset_id}'.")
    # if len(ordered_media_item_ids) != len(current_media_ids): # Check if any are missing
    #    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The list of media item IDs for reordering does not match current links.")


    if not asset_media_links_crud.update_asset_media_display_orders(asset_id, ordered_media_item_ids):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update media display orders.")

    # Return the updated list of media links in the new order
    updated_links = asset_media_links_crud.get_media_links_for_asset(asset_id)
    return [AssetMediaLink.model_validate(ul) for ul in updated_links]


if __name__ == "__main__": # pragma: no cover
    # This block can be used for simple validation of models if run directly.
    # It's not a replacement for proper unit tests.
    print("Validating CompanyAsset models...")
    try:
        asset_create_data = {
            "asset_name": "Dev Laptop 001", "asset_type": "Laptop",
            "serial_number": "SN001XYZ", "current_status": "In Use",
            "purchase_date": "2023-01-01" # Pydantic will parse this to date
        }
        asset_create_obj = CompanyAssetCreate(**asset_create_data)
        print(f"CompanyAssetCreate valid: {asset_create_obj.asset_name}, Purchase Date: {type(asset_create_obj.purchase_date)}")

        asset_response_data = {
            **asset_create_obj.model_dump(), "asset_id": "uuid-asset-123",
            "created_at": datetime.now(), "updated_at": datetime.now(), "is_deleted": False
        }
        asset_response_obj = CompanyAsset(**asset_response_data)
        print(f"CompanyAsset valid: {asset_response_obj.asset_id}")
    except Exception as e:
        print(f"Error in CompanyAsset model validation: {e}")

    print("\nValidating AssetAssignment models...")
    try:
        assignment_create_data = {
            "asset_id": "uuid-asset-123", "personnel_id": 101,
            "assignment_date": datetime.now(), "assignment_status": "Assigned"
        }
        assignment_create_obj = AssetAssignmentCreate(**assignment_create_data)
        print(f"AssetAssignmentCreate valid: Status {assignment_create_obj.assignment_status}")

        assignment_response_data = {
            **assignment_create_obj.model_dump(), "assignment_id": "uuid-assign-456",
            "created_at": datetime.now(), "updated_at": datetime.now()
        }
        assignment_response_obj = AssetAssignment(**assignment_response_data)
        print(f"AssetAssignment valid: {assignment_response_obj.assignment_id}")
    except Exception as e:
        print(f"Error in AssetAssignment model validation: {e}")

    print("\nValidating AssetMediaLink models...")
    try:
        link_create_data = {"media_item_id": "uuid-media-789", "display_order": 1, "alt_text": "Asset view"}
        link_create_obj = AssetMediaLinkCreate(**link_create_data)
        print(f"AssetMediaLinkCreate valid: Media ID {link_create_obj.media_item_id}")

        link_response_data = {
            **link_create_obj.model_dump(), "link_id": 1, "asset_id": "uuid-asset-123",
            "created_at": datetime.now(), "media_title": "Asset Front View", "media_item_type": "image"
        }
        link_response_obj = AssetMediaLink(**link_response_data)
        print(f"AssetMediaLink valid: Link ID {link_response_obj.link_id}, Title: {link_response_obj.media_title}")
    except Exception as e:
        print(f"Error in AssetMediaLink model validation: {e}")

    print("\nValidating AssetMediaUpload model...")
    try:
        upload_data = {
            "title": "New Product Image", "description": "Side view of the new product",
            "alt_text": "Side view", "display_order": 0, "tags": ["product", "new"]
        }
        upload_obj = AssetMediaUpload(**upload_data)
        print(f"AssetMediaUpload valid: Title {upload_obj.title}, Tags: {upload_obj.tags}")
    except Exception as e:
        print(f"Error in AssetMediaUpload model validation: {e}")

    print("\nAll basic model validations complete (if no errors above).")
    print("Note: `is_deleted: bool = False` on CompanyAsset means by default, active records are represented this way. If a soft-deleted asset is fetched and mapped to this model, its `is_deleted` field should be True.")
    print("`display_order: Optional[int] = 0` in AssetMediaLinkBase was changed to `display_order: int = 0` to reflect the prompt's default value making it non-optional.")

```
