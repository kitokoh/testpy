from fastapi import APIRouter, HTTPException, Depends, Body, Query, Path, Request
from typing import List, Optional, Dict, Any
import os # For URL construction if base URL comes from env

# Assuming db is structured to allow from db import cruds or similar
# Or from ..db import cruds if api is a subdir of a main app package
# For this subtask, let's assume db.cruds gives access to modules
from product_management import crud as products_crud_module
from product_management import media_links_crud as product_media_links_crud_module
from ..models import ( # Relative import from parent models.py
    ProductResponse, ProductCreate, ProductUpdate, ProductBase, # Added ProductBase for clarity if used directly
    LinkMediaToProductRequest, ProductImageLinkResponse, ProductImageLinkUpdateRequest,
    ReorderProductMediaLinksRequest,
    UserInDB # For authentication
)
from .auth import get_current_active_user # Assuming auth is in the same directory

router = APIRouter(
    prefix="/api/products",
    tags=["Products"],
    responses={404: {"description": "Not found"}},
)

# Configuration for media URLs (ideally from environment or config file)
# Example: MEDIA_BASE_URL = os.getenv("MEDIA_BASE_URL", "/media_files/")
# For simplicity in subtask, we might hardcode or skip if filepaths are served directly by another mechanism.
# Let's assume for now consumers of the API know how to prefix relative paths.
# Or, we can construct them here if a base URL is known. Let's try to construct them.

def construct_media_url(request: Request, relative_path: Optional[str]) -> Optional[str]:
    if not relative_path:
        return None
    # Example: if relative_path is "image_uuid.jpg" and MEDIA_FILES_BASE_PATH from config
    # points to a directory served at "/media", then URL is "/media/image_uuid.jpg".
    # For this example, let's assume a static path prefix.
    # A more robust solution would use app config.
    # Using request.base_url to build absolute URLs if needed, or just relative paths.
    # For now, let's return the path relative to a hypothetical /media_assets/ endpoint/dir.
    # This part is highly dependent on how static files are served.
    # A common pattern is to have a config for MEDIA_URL_PREFIX.
    media_url_prefix = "/static_media_placeholder/" # Placeholder
    return f"{media_url_prefix}{relative_path.lstrip('/')}"


def format_product_response(db_product: Dict[str, Any], request: Request) -> ProductResponse:
    # Helper to format DB output to Pydantic model, especially for media_links URLs
    media_links_response = []
    if db_product.get('media_links'):
        for link_data in db_product['media_links']:
            media_links_response.append(ProductImageLinkResponse(
                link_id=link_data['link_id'],
                media_item_id=link_data['media_item_id'],
                display_order=link_data['display_order'],
                alt_text=link_data['alt_text'],
                image_url=construct_media_url(request, link_data.get('media_filepath')),
                thumbnail_url=construct_media_url(request, link_data.get('media_thumbnail_path')),
                media_title=link_data.get('media_title')
            ))

    # Create the ProductResponse object
    product_data_for_model = {key: db_product[key] for key in ProductBase.__fields__ if key in db_product}
    product_data_for_model['product_id'] = db_product['product_id'] # Ensure product_id is included

    return ProductResponse(
        **product_data_for_model,
        media_links=media_links_response
    )

# --- Product CRUD Endpoints ---
@router.post("", response_model=ProductResponse, status_code=201)
async def create_product_api(
    product: ProductCreate,
    request: Request,
    current_user: UserInDB = Depends(get_current_active_user)
):
    # product_data should not contain product_id as it's auto-generated
    product_dict = product.dict(exclude_unset=True)
    # add_product from product_management.crud returns a dict {'success': True/False, 'id': new_id}
    result = products_crud_module.add_product(product_data=product_dict)
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=f"Failed to create product: {result.get('error', 'Unknown error')}")

    db_product_id = result.get('id')
    if db_product_id is None : # Should not happen if success is True
        raise HTTPException(status_code=500, detail="Product creation succeeded but no ID returned.")


    created_product = products_crud_module.get_product_by_id(product_id=db_product_id)
    if not created_product:
        raise HTTPException(status_code=500, detail="Product created but could not be retrieved.") # Should not happen
    return format_product_response(created_product, request)

@router.get("/{product_id}", response_model=ProductResponse)
async def get_product_api(
    product_id: int = Path(..., description="The ID of the product to retrieve"),
    request: Request,
    current_user: UserInDB = Depends(get_current_active_user) # Optional auth
):
    db_product = products_crud_module.get_product_by_id(product_id=product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return format_product_response(db_product, request)

@router.get("", response_model=List[ProductResponse]) # Simplified response for list view
async def get_all_products_api(
    request: Request,
    category: Optional[str] = Query(None),
    language_code: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: UserInDB = Depends(get_current_active_user) # Optional auth
):
    filters = {}
    if category is not None: filters['category'] = category
    if language_code is not None: filters['language_code'] = language_code
    if is_active is not None: filters['is_active'] = is_active

    db_products = products_crud_module.get_all_products(filters=filters)
    # For list view, media_links are typically not included for performance.
    # The format_product_response will handle empty media_links if the CRUD doesn't add them for list views.
    # products_crud.get_all_products currently does NOT fetch media_links.
    # So, the media_links list in each ProductResponse here will be empty, which is fine for a list.
    return [format_product_response(p, request) for p in db_products]


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product_api(
    product_id: int,
    product_update: ProductUpdate,
    request: Request,
    current_user: UserInDB = Depends(get_current_active_user)
):
    update_data = product_update.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided.")

    update_result = products_crud_module.update_product(product_id=product_id, data=update_data)
    if not update_result.get('success'):
        # Could be product not found or DB error
        existing_product = products_crud_module.get_product_by_id(product_id=product_id) # Check if it's a 404
        if not existing_product:
            raise HTTPException(status_code=404, detail="Product not found")
        raise HTTPException(status_code=500, detail=f"Failed to update product: {update_result.get('error', 'Unknown error')}")

    updated_product = products_crud_module.get_product_by_id(product_id=product_id)
    if not updated_product:
         raise HTTPException(status_code=500, detail="Product updated but could not be retrieved.")
    return format_product_response(updated_product, request)

@router.delete("/{product_id}", status_code=204)
async def delete_product_api(
    product_id: int,
    current_user: UserInDB = Depends(get_current_active_user)
):
    # Consider implications: what happens to linked media items?
    # The DB schema for ProductMediaLinks has ON DELETE CASCADE for product_id,
    # so links will be auto-deleted. MediaItems themselves are not deleted.
    existing_product = products_crud_module.get_product_by_id(product_id=product_id)
    if not existing_product:
        raise HTTPException(status_code=404, detail="Product not found")

    delete_result = products_crud_module.delete_product(product_id=product_id)
    if not delete_result.get('success'):
        raise HTTPException(status_code=500, detail=f"Failed to delete product: {delete_result.get('error', 'Unknown error')}")
    return # No content for 204


# --- Product Media Links Endpoints ---

@router.post("/{product_id}/media_links", response_model=ProductImageLinkResponse, status_code=201)
async def link_media_to_product_api(
    product_id: int,
    link_request: LinkMediaToProductRequest,
    request_obj: Request, # Renamed to avoid conflict with pydantic 'request'
    current_user: UserInDB = Depends(get_current_active_user)
):
    # Check if product exists
    db_product = products_crud_module.get_product_by_id(product_id=product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    # TODO: Check if media_item_id exists in MediaItems table (optional, for robustness)

    link_id = product_media_links_crud_module.link_media_to_product(
        product_id=product_id,
        media_item_id=link_request.media_item_id,
        display_order=link_request.display_order,
        alt_text=link_request.alt_text
    )
    if link_id is None:
        raise HTTPException(status_code=400, detail="Failed to link media to product. Media may already be linked or invalid IDs.")

    # Retrieve the newly created link with joined MediaItem details for response
    # Need a CRUD function like get_media_link_details_by_link_id that joins with MediaItems
    # For now, let's use get_media_links_for_product and find the one we just added.
    # This is not ideal. A direct fetch of the created link with media details would be better.
    # Let's assume get_media_link_by_link_id exists in product_media_links_crud_module
    # and we enhance it or add another to fetch joined data.
    # The `get_media_links_for_product` returns a list, we need one item.
    # A new function `get_detailed_media_link_by_id(link_id)` would be good.
    # For now, let's construct the response manually or from get_media_link_by_ids if sufficient.

    # Simplified: refetch all and find by media_item_id (assuming it's unique for the product)
    all_links = product_media_links_crud_module.get_media_links_for_product(product_id)
    newly_linked_info = next((l for l in all_links if l['media_item_id'] == link_request.media_item_id and l['link_id'] == link_id), None)

    if not newly_linked_info:
         # Fallback if the above doesn't work as expected (e.g. no media_filepath)
         # This means the get_media_links_for_product didn't return enough info for ProductImageLinkResponse
         # which requires media_filepath and media_thumbnail_path.
         # The `get_media_links_for_product` in the CRUD subtask was designed to join and get these.
        raise HTTPException(status_code=500, detail="Media linked, but could not retrieve link details for response.")

    return ProductImageLinkResponse(
        link_id=newly_linked_info['link_id'],
        media_item_id=newly_linked_info['media_item_id'],
        display_order=newly_linked_info['display_order'],
        alt_text=newly_linked_info['alt_text'],
        image_url=construct_media_url(request_obj, newly_linked_info.get('media_filepath')),
        thumbnail_url=construct_media_url(request_obj, newly_linked_info.get('media_thumbnail_path')),
        media_title=newly_linked_info.get('media_title')
    )


@router.put("/media_links/{link_id}", response_model=ProductImageLinkResponse)
async def update_product_media_link_api(
    link_id: int,
    update_request: ProductImageLinkUpdateRequest,
    request_obj: Request,
    current_user: UserInDB = Depends(get_current_active_user)
):
    if update_request.display_order is None and update_request.alt_text is None:
        raise HTTPException(status_code=400, detail="No update data provided (display_order or alt_text).")

    # Check if link exists
    existing_link = product_media_links_crud_module.get_media_link_by_link_id(link_id=link_id)
    if not existing_link:
        raise HTTPException(status_code=404, detail="Product media link not found.")

    success = product_media_links_crud_module.update_media_link(
        link_id=link_id,
        display_order=update_request.display_order,
        alt_text=update_request.alt_text
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update product media link.")

    # Fetch the updated link with joined MediaItem details
    # Again, a specific CRUD function get_detailed_media_link_by_id(link_id) would be best.
    # For now, use get_media_links_for_product with the product_id from existing_link
    product_id = existing_link['product_id']
    all_product_links = product_media_links_crud_module.get_media_links_for_product(product_id)
    updated_link_info = next((l for l in all_product_links if l['link_id'] == link_id), None)

    if not updated_link_info:
        raise HTTPException(status_code=500, detail="Link updated, but could not retrieve details for response.")

    return ProductImageLinkResponse(
        link_id=updated_link_info['link_id'],
        media_item_id=updated_link_info['media_item_id'],
        display_order=updated_link_info['display_order'],
        alt_text=updated_link_info['alt_text'],
        image_url=construct_media_url(request_obj, updated_link_info.get('media_filepath')),
        thumbnail_url=construct_media_url(request_obj, updated_link_info.get('media_thumbnail_path')),
        media_title=updated_link_info.get('media_title')
    )

@router.delete("/media_links/{link_id}", status_code=204)
async def unlink_media_from_product_api(
    link_id: int,
    current_user: UserInDB = Depends(get_current_active_user)
):
    existing_link = product_media_links_crud_module.get_media_link_by_link_id(link_id=link_id)
    if not existing_link:
        raise HTTPException(status_code=404, detail="Product media link not found.")

    success = product_media_links_crud_module.unlink_media_from_product(link_id=link_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to unlink media from product.")
    return # No content

@router.post("/{product_id}/media_links/reorder", response_model=List[ProductImageLinkResponse])
async def reorder_product_media_links_api(
    product_id: int,
    reorder_request: ReorderProductMediaLinksRequest,
    request_obj: Request,
    current_user: UserInDB = Depends(get_current_active_user)
):
    # Check if product exists
    db_product = products_crud_module.get_product_by_id(product_id=product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    success = product_media_links_crud_module.update_product_media_display_orders(
        product_id=product_id,
        ordered_media_item_ids=reorder_request.ordered_media_item_ids
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to reorder media links. Ensure all media IDs are valid and linked to the product.")

    # Return the new order
    updated_links_raw = product_media_links_crud_module.get_media_links_for_product(product_id)

    response_links = []
    for link_data in updated_links_raw:
        response_links.append(ProductImageLinkResponse(
            link_id=link_data['link_id'],
            media_item_id=link_data['media_item_id'],
            display_order=link_data['display_order'],
            alt_text=link_data['alt_text'],
            image_url=construct_media_url(request_obj, link_data.get('media_filepath')),
            thumbnail_url=construct_media_url(request_obj, link_data.get('media_thumbnail_path')),
            media_title=link_data.get('media_title')
        ))
    return response_links
