import json
import os
import shutil
import uuid
from . import models

MEDIA_LIBRARY_FILE = "media_library.json"
MEDIA_FILES_DIR = "media_files"

def _load_media_library() -> list[dict]:
    """Loads the media library from a JSON file."""
    if not os.path.exists(MEDIA_LIBRARY_FILE):
        return []
    try:
        with open(MEDIA_LIBRARY_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return [] # Return empty list if JSON is invalid

def _save_media_library(library: list[dict]) -> None:
    """Saves the given library to media_library.json."""
    with open(MEDIA_LIBRARY_FILE, 'w') as f:
        json.dump(library, f, indent=4)

def _generate_id() -> str:
    """Generates a unique ID."""
    return str(uuid.uuid4())

def add_video(title: str, description: str, category: str, filepath: str) -> models.VideoItem:
    """Adds a new video item."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Video file not found: {filepath}")

    item_id = _generate_id()
    _, extension = os.path.splitext(filepath)
    new_filename = f"{item_id}{extension}"
    new_filepath = os.path.join(MEDIA_FILES_DIR, new_filename)

    os.makedirs(MEDIA_FILES_DIR, exist_ok=True) # Ensure media_files directory exists
    shutil.copy(filepath, new_filepath)

    video_item = models.VideoItem(id=item_id, title=title, description=description, category=category, filepath=new_filepath)

    library = _load_media_library()
    library.append(video_item.to_dict())
    _save_media_library(library)

    return video_item

def add_image(title: str, description: str, category: str, filepath: str) -> models.ImageItem:
    """Adds a new image item."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Image file not found: {filepath}")

    item_id = _generate_id()
    _, extension = os.path.splitext(filepath)
    new_filename = f"{item_id}{extension}"
    new_filepath = os.path.join(MEDIA_FILES_DIR, new_filename)

    os.makedirs(MEDIA_FILES_DIR, exist_ok=True) # Ensure media_files directory exists
    shutil.copy(filepath, new_filepath)

    image_item = models.ImageItem(id=item_id, title=title, description=description, category=category, filepath=new_filepath)

    library = _load_media_library()
    library.append(image_item.to_dict())
    _save_media_library(library)

    return image_item

def add_link(title: str, description: str, category: str, url: str) -> models.LinkItem:
    """Adds a new link item."""
    item_id = _generate_id()
    link_item = models.LinkItem(id=item_id, title=title, description=description, category=category, url=url)

    library = _load_media_library()
    library.append(link_item.to_dict())
    _save_media_library(library)

    library.append(link_item.to_dict())
    _save_media_library(library)

    return link_item

def list_media(filter_category: str | None = None, filter_type: str | None = None) -> list[models.MediaItem]:
    """Lists all media items, with optional filtering by category and/or type."""
    library_dicts = _load_media_library()
    media_items_objects = []
    for item_dict in library_dicts:
        try:
            media_items_objects.append(models.MediaItem.from_dict(item_dict))
        except ValueError as e:
            print(f"Error reconstructing media item: {e}. Skipping item: {item_dict.get('id')}")
            # Continue to next item if one is corrupted

    # Apply category filter (case-insensitive)
    if filter_category:
        media_items_objects = [
            item for item in media_items_objects
            if item.category.lower() == filter_category.lower()
        ]

    # Apply type filter (exact match)
    if filter_type:
        media_items_objects = [
            item for item in media_items_objects
            if item.item_type == filter_type
        ]
            # Alternative: isinstance check if filter_type is mapped to class types
            # For example, if filter_type == "video":
            #   media_items_objects = [item for item in media_items_objects if isinstance(item, models.VideoItem)]
            # But using item.item_type is more direct with current setup.

    return media_items_objects

def search_media(query: str) -> list[models.MediaItem]:
    """Searches media items by keyword in title and description."""
    all_items = list_media() # Get all media items, no filters

    if not query or query.isspace():
        return [] # Return empty list if query is empty or just whitespace

    normalized_query = query.lower()
    matched_items_set = set() # Use a set to store IDs of matched items to ensure uniqueness
    result_items = []

    for item in all_items:
        # Check if item already added to avoid duplicate processing if not strictly necessary
        # (though set logic below handles final uniqueness)
        # if item.id in matched_items_set:
        # continue

        # Check title
        if normalized_query in item.title.lower():
            if item.id not in matched_items_set:
                result_items.append(item)
                matched_items_set.add(item.id)
            # No continue here, to allow checking description as well,
            # though the set handles uniqueness.
            # If we only want to add once and stop, `continue` would be here.

        # Check description (only if not already added from title match)
        if item.id not in matched_items_set: # Optimization: check description only if not already added
            if normalized_query in item.description.lower():
                result_items.append(item)
                matched_items_set.add(item.id)

    return result_items

def get_media_items_by_ids(ids: list[str]) -> list[models.MediaItem]:
    """Retrieves media items based on a list of their IDs."""
    all_items = list_media() # Get all media items

    if not ids:
        return []

    selected_ids_set = set(ids)
    found_items = []

    for item in all_items:
        if item.id in selected_ids_set:
            found_items.append(item)
            # If items should be unique and order of input `ids` list matters,
            # and an ID might be duplicated in `ids`:
            # selected_ids_set.remove(item.id) # To ensure we pick an item once if ID is duplicated in input.
            # However, standard use is unique IDs in the input list.

    # The problem statement says: "order of returned items can be based on the order
    # in the original library or the order of IDs provided; for simplicity,
    # the order from list_media() is fine."
    # The current implementation respects the order from list_media().

    # If preserving input ID order is strictly needed and all_items is large,
    # creating an item_map first might be more efficient for lookup.
    # Example for preserving input ID order:
    # item_map = {item.id: item for item in all_items}
    # ordered_found_items = [item_map[id_val] for id_val in ids if id_val in item_map]
    # return ordered_found_items

    return found_items

def download_selected_media(selected_ids: list[str], download_path: str) -> list[str]:
    """Downloads selected media items (copies files, saves links)."""
    if not selected_ids:
        return []

    media_items_to_download = get_media_items_by_ids(selected_ids)
    if not media_items_to_download:
        return []

    os.makedirs(download_path, exist_ok=True)
    downloaded_file_paths = []
    link_file_data = [] # Collect all links to write them once

    for item in media_items_to_download:
        if isinstance(item, (models.VideoItem, models.ImageItem)):
            if hasattr(item, 'filepath') and os.path.exists(item.filepath):
                try:
                    # Sanitize title for use as a filename component, or use ID
                    # For simplicity, using original filename from item.filepath
                    base_filename = os.path.basename(item.filepath)
                    destination_path = os.path.join(download_path, base_filename)
                    shutil.copy(item.filepath, destination_path)
                    downloaded_file_paths.append(destination_path)
                except Exception as e:
                    print(f"Error copying file {item.filepath} for item ID {item.id}: {e}")
            else:
                print(f"Filepath for item ID {item.id} not found or invalid: {getattr(item, 'filepath', 'N/A')}")
        elif isinstance(item, models.LinkItem):
            if hasattr(item, 'url'):
                link_file_data.append(f"Title: {item.title}\nURL: {item.url}\n")
            else:
                print(f"URL for item ID {item.id} not found.")

    if link_file_data:
        links_file_path = os.path.join(download_path, "downloaded_links.txt")
        try:
            with open(links_file_path, 'w') as f:
                f.write("\n---\n".join(link_file_data)) # Separate entries
            downloaded_file_paths.append(links_file_path)
        except Exception as e:
            print(f"Error writing links file to {links_file_path}: {e}")

    return downloaded_file_paths

def share_media_by_email(selected_ids: list[str], recipient_email: str) -> str:
    """Placeholder for sharing media by email."""
    items = get_media_items_by_ids(selected_ids)
    if not items:
        return f"No media items found for IDs: {selected_ids}."

    # In a real implementation, this would involve formatting and sending an email.
    # For example, listing titles, descriptions, and attaching/linking files.

    message = (
        f"Attempting to share {len(items)} media item(s) with IDs {selected_ids} to {recipient_email}.\n"
        "Email functionality is not fully implemented in this backend module."
    )
    print(message)
    # Simulate a success/failure message
    return f"Placeholder: Email sharing process initiated for {len(items)} items to {recipient_email}."

def share_media_by_whatsapp(selected_ids: list[str], recipient_phone: str) -> str:
    """Placeholder for sharing media by WhatsApp."""
    items = get_media_items_by_ids(selected_ids)
    if not items:
        return f"No media items found for IDs: {selected_ids}."

    # Real implementation would use WhatsApp Business API or similar.
    # This would involve formatting messages, handling media uploads/links per WhatsApp constraints.

    message = (
        f"Attempting to share {len(items)} media item(s) with IDs {selected_ids} to WhatsApp user {recipient_phone}.\n"
        "WhatsApp functionality is not fully implemented and may require specific API integrations."
    )
    print(message)
    return f"Placeholder: WhatsApp sharing process initiated for {len(items)} items to {recipient_phone}."
