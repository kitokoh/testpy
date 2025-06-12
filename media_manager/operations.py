import os
import shutil
import uuid
import sqlite3
from datetime import datetime
from typing import List
from . import models
import db

import asyncio
import aiofiles
import aiofiles.os as aios

from PIL import Image # For Pillow
import cv2 # For OpenCV

from config import MEDIA_FILES_BASE_PATH, DEFAULT_DOWNLOAD_PATH

THUMBNAIL_SIZE = (128, 128)
THUMBNAIL_DIR_NAME = ".thumbnails" # Relative to MEDIA_FILES_BASE_PATH
=======
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

def _get_or_create_tag_id(tag_name: str, cursor: sqlite3.Cursor) -> int:
    normalized_tag_name = tag_name.strip().lower()
    if not normalized_tag_name:
        raise ValueError("Tag name cannot be empty.")
    cursor.execute("SELECT tag_id FROM Tags WHERE tag_name = ?", (normalized_tag_name,))
    row = cursor.fetchone()
    if row:
        return row['tag_id']
    else:
        cursor.execute("INSERT INTO Tags (tag_name) VALUES (?)", (normalized_tag_name,))
        return cursor.lastrowid

def get_tags_for_media_item(media_item_id: str, cursor: sqlite3.Cursor) -> List[str]:
    cursor.execute("""
        SELECT t.tag_name
        FROM Tags t
        JOIN MediaItemTags mit ON t.tag_id = mit.tag_id
        WHERE mit.media_item_id = ?
        ORDER BY t.tag_name
    """, (media_item_id,))
    return [row['tag_name'] for row in cursor.fetchall()]

def _blocking_pil_image_thumbnail(source_path: str, thumb_dest_path: str, size: tuple[int, int]):
    """Synchronous/blocking function to create image thumbnail using Pillow."""
    try:
        img = Image.open(source_path)
        img.thumbnail(size)
        # Ensure the image is in RGB mode before saving as JPG if it's RGBA (like PNGs)
        if img.mode in ("RGBA", "P"): # P is for paletted images
            img = img.convert("RGB")
        img.save(thumb_dest_path, "JPEG") # Save as JPEG
        return True
    except Exception as e:
        print(f"Pillow: Error generating image thumbnail for {source_path}: {e}")
        return False

async def _generate_image_thumbnail(source_media_path: str, media_item_id: str) -> str | None:
    """Generates a thumbnail for an image file using Pillow in an executor."""
    thumb_dir = os.path.join(MEDIA_FILES_BASE_PATH, THUMBNAIL_DIR_NAME)
    await aios.makedirs(thumb_dir, exist_ok=True)
    thumb_filename = f"{media_item_id}.jpg" # Standardize to JPG
    thumb_dest_path_abs = os.path.join(thumb_dir, thumb_filename)

    loop = asyncio.get_event_loop()
    success = await loop.run_in_executor(None, _blocking_pil_image_thumbnail, source_media_path, thumb_dest_path_abs, THUMBNAIL_SIZE)

    if success:
        return os.path.join(THUMBNAIL_DIR_NAME, thumb_filename) # Return relative path
    return None

def _blocking_cv2_video_thumbnail(source_path: str, thumb_dest_path: str, size: tuple[int, int]):
    """Synchronous/blocking function to create video thumbnail using OpenCV and Pillow."""
    cap = None
    try:
        cap = cv2.VideoCapture(source_path)
        if not cap.isOpened():
            print(f"OpenCV: Could not open video file: {source_path}")
            return False

        # Try to capture a frame a few seconds into the video
        cap.set(cv2.CAP_PROP_POS_FRAMES, min(50, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) -1 )) # frame 50 or last frame
        ret, frame = cap.read()
        if not ret: # If that fails, try the first frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()

        if ret:
            pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            pil_img.thumbnail(size)
            if pil_img.mode in ("RGBA", "P"):
                pil_img = pil_img.convert("RGB")
            pil_img.save(thumb_dest_path, "JPEG")
            return True
        else:
            print(f"OpenCV: Could not read frame from video: {source_path}")
            return False
    except Exception as e:
        print(f"OpenCV/Pillow: Error generating video thumbnail for {source_path}: {e}")
        return False
    finally:
        if cap:
            cap.release()

async def _generate_video_thumbnail(source_media_path: str, media_item_id: str) -> str | None:
    """Generates a thumbnail for a video file using OpenCV and Pillow in an executor."""
    thumb_dir = os.path.join(MEDIA_FILES_BASE_PATH, THUMBNAIL_DIR_NAME)
    await aios.makedirs(thumb_dir, exist_ok=True)
    thumb_filename = f"{media_item_id}.jpg"
    thumb_dest_path_abs = os.path.join(thumb_dir, thumb_filename)

    loop = asyncio.get_event_loop()
    success = await loop.run_in_executor(None, _blocking_cv2_video_thumbnail, source_media_path, thumb_dest_path_abs, THUMBNAIL_SIZE)

    if success:
        return os.path.join(THUMBNAIL_DIR_NAME, thumb_filename) # Relative path
    return None


async def add_video(title: str, description: str, filepath: str, uploader_user_id: str, tags: List[str] | None = None) -> models.VideoItem:
    if not await aios.path.exists(filepath):
        raise FileNotFoundError(f"Video file not found: {filepath}")
    if not uploader_user_id:
        raise ValueError("uploader_user_id is mandatory to add media.")
def add_video(title: str, description: str, category: str, filepath: str) -> models.VideoItem:
    """Adds a new video item."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Video file not found: {filepath}")

    item_id = _generate_id()
    _, extension = os.path.splitext(filepath)
    new_filename = f"{item_id}{extension}"
    new_media_filepath_abs = os.path.join(MEDIA_FILES_BASE_PATH, new_filename) # Absolute path for copy
    new_media_filepath_rel = os.path.join(new_filename) # Relative path for DB and model (relative to MEDIA_FILES_BASE_PATH)


    await aios.makedirs(MEDIA_FILES_BASE_PATH, exist_ok=True)
    thumbnail_rel_path = None # Initialize

    try:
        async with aiofiles.open(filepath, 'rb') as src_f:
            async with aiofiles.open(new_media_filepath_abs, 'wb') as dest_f:
                while True:
                    chunk = await src_f.read(8192)
                    if not chunk: break
                    await dest_f.write(chunk)

        # Generate thumbnail after successful file copy
        thumbnail_rel_path = await _generate_video_thumbnail(new_media_filepath_abs, item_id)

    except Exception as e_copy:
        print(f"Error during async file copy/thumb for {filepath}: {e_copy}")
        if await aios.path.exists(new_media_filepath_abs):
            try: await aios.remove(new_media_filepath_abs)
            except OSError as oe: print(f"Error cleaning up file {new_media_filepath_abs}: {oe}")
        raise

    video_item_model = models.VideoItem(id=item_id, title=title, description=description, filepath=new_media_filepath_rel, tags=tags if tags else [], thumbnail_path=thumbnail_rel_path)

    conn = None
    try:
        conn = db.get_db_connection()
        cursor = conn.cursor()
        now_iso = datetime.utcnow().isoformat()

        cursor.execute(
            """INSERT INTO MediaItems (media_item_id, title, description, item_type, filepath, url, uploader_user_id, created_at, updated_at, thumbnail_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (video_item_model.id, video_item_model.title, video_item_model.description,
             video_item_model.item_type, video_item_model.filepath, None, uploader_user_id, now_iso, now_iso, video_item_model.thumbnail_path)
        )

        if video_item_model.tags:
            for tag_name in video_item_model.tags:
                tag_id = _get_or_create_tag_id(tag_name, cursor)
                cursor.execute("INSERT INTO MediaItemTags (media_item_id, tag_id) VALUES (?, ?)", (video_item_model.id, tag_id))

        conn.commit()
    except sqlite3.Error as e_db:
        if conn: conn.rollback()
        print(f"Database error in add_video: {e_db}")
        # File was already copied, and thumbnail might have been generated.
        # This state might require manual cleanup or more sophisticated rollback of file ops.
        raise
    finally:
        if conn: conn.close()
    return video_item_model

async def add_image(title: str, description: str, filepath: str, uploader_user_id: str, tags: List[str] | None = None) -> models.ImageItem:
    if not await aios.path.exists(filepath):
        raise FileNotFoundError(f"Image file not found: {filepath}")
    if not uploader_user_id:
        raise ValueError("uploader_user_id is mandatory to add media.")

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
    new_media_filepath_abs = os.path.join(MEDIA_FILES_BASE_PATH, new_filename)
    new_media_filepath_rel = os.path.join(new_filename) # Relative to MEDIA_FILES_BASE_PATH

    await aios.makedirs(MEDIA_FILES_BASE_PATH, exist_ok=True)
    thumbnail_rel_path = None

    try:
        async with aiofiles.open(filepath, 'rb') as src_f:
            async with aiofiles.open(new_media_filepath_abs, 'wb') as dest_f:
                while True:
                    chunk = await src_f.read(8192)
                    if not chunk: break
                    await dest_f.write(chunk)

        thumbnail_rel_path = await _generate_image_thumbnail(new_media_filepath_abs, item_id)
    except Exception as e_copy:
        print(f"Error during async file copy/thumb for {filepath}: {e_copy}")
        if await aios.path.exists(new_media_filepath_abs):
            try: await aios.remove(new_media_filepath_abs)
            except OSError as oe: print(f"Error cleaning up file {new_media_filepath_abs}: {oe}")
        raise

    image_item_model = models.ImageItem(id=item_id, title=title, description=description, filepath=new_media_filepath_rel, tags=tags if tags else [], thumbnail_path=thumbnail_rel_path)

    conn = None
    try:
        conn = db.get_db_connection()
        cursor = conn.cursor()
        now_iso = datetime.utcnow().isoformat()

        cursor.execute(
            """INSERT INTO MediaItems (media_item_id, title, description, item_type, filepath, url, uploader_user_id, created_at, updated_at, thumbnail_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (image_item_model.id, image_item_model.title, image_item_model.description,
             image_item_model.item_type, image_item_model.filepath, None, uploader_user_id, now_iso, now_iso, image_item_model.thumbnail_path)
        )

        if image_item_model.tags:
            for tag_name in image_item_model.tags:
                tag_id = _get_or_create_tag_id(tag_name, cursor)
                cursor.execute("INSERT INTO MediaItemTags (media_item_id, tag_id) VALUES (?, ?)", (image_item_model.id, tag_id))

        conn.commit()
    except sqlite3.Error as e_db:
        if conn: conn.rollback()
        print(f"Database error in add_image: {e_db}")
        raise
    finally:
        if conn: conn.close()
    return image_item_model

# add_link remains synchronous
def add_link(title: str, description: str, url: str, uploader_user_id: str, tags: List[str] | None = None) -> models.LinkItem:
    if not uploader_user_id:
        raise ValueError("uploader_user_id is mandatory to add media.")
    item_id = _generate_id()
    # Links don't have file-based thumbnails generated by this system.
    link_item_model = models.LinkItem(id=item_id, title=title, description=description, url=url, tags=tags if tags else [], thumbnail_path=None)
    conn = None
    try:
        conn = db.get_db_connection()
        cursor = conn.cursor()
        now_iso = datetime.utcnow().isoformat()
        cursor.execute(
            """INSERT INTO MediaItems (media_item_id, title, description, item_type, filepath, url, uploader_user_id, created_at, updated_at, thumbnail_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (link_item_model.id, link_item_model.title, link_item_model.description,
             link_item_model.item_type, None, link_item_model.url, uploader_user_id, now_iso, now_iso, None) # thumbnail_path is None for links
        )
        if link_item_model.tags:
            for tag_name in link_item_model.tags:
                tag_id = _get_or_create_tag_id(tag_name, cursor)
                cursor.execute("INSERT INTO MediaItemTags (media_item_id, tag_id) VALUES (?, ?)", (link_item_model.id, tag_id))
        conn.commit()
    except sqlite3.Error as e:
        if conn: conn.rollback()
        print(f"Database error in add_link: {e}")
        raise
    finally:
        if conn: conn.close()
    return link_item_model

# list_media, search_media, get_media_items_by_ids remain synchronous for DB queries
# but they already correctly fetch all columns including thumbnail_path for from_dict.
def list_media(filter_tags: List[str] | None = None, filter_type: str | None = None, filter_by_uploader_id: str | None = None) -> list[models.MediaItem]:
    conn = None
    media_items_objects = []
    try:
        conn = db.get_db_connection()
        cursor = conn.cursor()
        params = []
        sql = "SELECT DISTINCT m.* FROM MediaItems m"
        join_clauses = []
        where_clauses = []
        if filter_tags:
            normalized_filter_tags = [tag.strip().lower() for tag in filter_tags if tag.strip()]
            if normalized_filter_tags:
                for i, tag_name in enumerate(normalized_filter_tags):
                    alias_mit = f"mit{i}"
                    alias_t = f"t{i}"
                    join_clauses.append(f"JOIN MediaItemTags {alias_mit} ON m.media_item_id = {alias_mit}.media_item_id")
                    join_clauses.append(f"JOIN Tags {alias_t} ON {alias_mit}.tag_id = {alias_t}.tag_id")
                    where_clauses.append(f"{alias_t}.tag_name = ?")
                    params.append(tag_name)
        if filter_type:
            where_clauses.append("m.item_type = ?")
            params.append(filter_type)
        if filter_by_uploader_id:
            where_clauses.append("m.uploader_user_id = ?")
            params.append(filter_by_uploader_id)
        if join_clauses:
            sql += " " + " ".join(join_clauses)
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        sql += " ORDER BY m.created_at DESC"
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        for row_data in rows:
            item_dict = dict(row_data)
            item_tags = get_tags_for_media_item(item_dict['media_item_id'], cursor)
            item_dict['tags'] = item_tags
            if 'item_type' in item_dict and 'type' not in item_dict:
                item_dict['type'] = item_dict['item_type']
            try:
                media_items_objects.append(models.MediaItem.from_dict(item_dict))
            except ValueError as e:
                print(f"Error reconstructing media item from DB row: {e}. Skipping item ID: {item_dict.get('media_item_id')}")
    except sqlite3.Error as e:
        print(f"Database error in list_media: {e}")
    finally:
        if conn: conn.close()
    return media_items_objects

def search_media(
    query: str | None = None,
    created_after: str | None = None,
    created_before: str | None = None,
    updated_after: str | None = None,
    updated_before: str | None = None,
    filter_by_uploader_id: str | None = None
) -> list[models.MediaItem]:
    media_items_objects = []
    conn = None
    if not query and not created_after and not created_before and \
       not updated_after and not updated_before and not filter_by_uploader_id:
        return []
    try:
        conn = db.get_db_connection()
        cursor = conn.cursor()
        sql_conditions = []
        params = []
        sql_base = "SELECT DISTINCT m.* FROM MediaItems m"
        sql_joins = ""
        if query and not query.isspace():
            normalized_query = f"%{query.lower()}%"
            sql_conditions.append("(LOWER(m.title) LIKE ? OR LOWER(m.description) LIKE ?)")
            params.extend([normalized_query, normalized_query])
        if created_after:
            sql_conditions.append("m.created_at >= ?")
            params.append(created_after)
        if created_before:
            adjusted_created_before = created_before
            if len(created_before) == 10:
                adjusted_created_before = f"{created_before}T23:59:59.999Z"
            sql_conditions.append("m.created_at <= ?")
            params.append(adjusted_created_before)
        if updated_after:
            sql_conditions.append("m.updated_at >= ?")
            params.append(updated_after)
        if updated_before:
            adjusted_updated_before = updated_before
            if len(updated_before) == 10:
                adjusted_updated_before = f"{updated_before}T23:59:59.999Z"
            sql_conditions.append("m.updated_at <= ?")
            params.append(adjusted_updated_before)
        if filter_by_uploader_id:
            sql_conditions.append("m.uploader_user_id = ?")
            params.append(filter_by_uploader_id)
        if not sql_conditions:
             if not query and not created_after and not created_before and not updated_after and not updated_before and not filter_by_uploader_id:
                return []
        sql = sql_base + " " + sql_joins
        if sql_conditions:
            sql += " WHERE " + " AND ".join(sql_conditions)
        sql += " ORDER BY m.created_at DESC"
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        for row_data in rows:
            item_dict = dict(row_data)
            item_tags = get_tags_for_media_item(item_dict['media_item_id'], cursor)
            item_dict['tags'] = item_tags
            if 'item_type' in item_dict and 'type' not in item_dict:
                item_dict['type'] = item_dict['item_type']
            try:
                media_items_objects.append(models.MediaItem.from_dict(item_dict))
            except ValueError as e:
                print(f"Error reconstructing media item during search: {e}. Skipping item ID: {item_dict.get('media_item_id')}")
    except sqlite3.Error as e:
        print(f"Database error in search_media: {e}")
    finally:
        if conn: conn.close()
    return media_items_objects

def get_media_items_by_ids(ids: list[str]) -> list[models.MediaItem]:
    if not ids: return []
    media_items_objects = []
    conn = None
    try:
        conn = db.get_db_connection()
        cursor = conn.cursor()
        placeholders = ','.join('?' for _ in ids)
        sql = f"SELECT * FROM MediaItems WHERE media_item_id IN ({placeholders}) ORDER BY created_at DESC"
        cursor.execute(sql, tuple(ids))
        rows = cursor.fetchall()
        for row_data in rows:
            item_dict = dict(row_data)
            item_tags = get_tags_for_media_item(item_dict['media_item_id'], cursor)
            item_dict['tags'] = item_tags
            if 'item_type' in item_dict and 'type' not in item_dict:
                item_dict['type'] = item_dict['item_type']
            try:
                media_items_objects.append(models.MediaItem.from_dict(item_dict))
            except ValueError as e:
                print(f"Error reconstructing media item in get_media_items_by_ids: {e}. Skipping item ID: {item_dict.get('media_item_id')}")
    except sqlite3.Error as e:
        print(f"Database error in get_media_items_by_ids: {e}")
    finally:
        if conn: conn.close()
    return media_items_objects

async def download_selected_media(selected_ids: list[str], download_path: str) -> list[str]:
    if not selected_ids: return []
    media_items_to_download = get_media_items_by_ids(selected_ids)
    if not media_items_to_download: return []
    await aios.makedirs(download_path, exist_ok=True)
    downloaded_file_paths = []
    link_file_data = []
    for item in media_items_to_download:
        if isinstance(item, (models.VideoItem, models.ImageItem)):
            # Filepath in DB is relative to MEDIA_FILES_BASE_PATH
            source_file_abs_path = os.path.join(MEDIA_FILES_BASE_PATH, item.filepath) if item.filepath else None
            if source_file_abs_path and await aios.path.exists(source_file_abs_path):
                try:
                    base_filename = os.path.basename(item.filepath)
                    destination_path = os.path.join(download_path, base_filename)
                    async with aiofiles.open(source_file_abs_path, 'rb') as src_f:
                        async with aiofiles.open(destination_path, 'wb') as dest_f:
                            while True:
                                chunk = await src_f.read(8192)
                                if not chunk: break
                                await dest_f.write(chunk)
                    downloaded_file_paths.append(destination_path)
                except Exception as e:
                    print(f"Error copying file {source_file_abs_path} for item ID {item.id}: {e}")
            else:
                print(f"Filepath for item ID {item.id} not found or invalid: {source_file_abs_path}")
        elif isinstance(item, models.LinkItem):
            if hasattr(item, 'url') and item.url:
                tags_str = f"Tags: {', '.join(sorted(item.tags))}" if item.tags else "Tags: None" # Sort tags for consistent output
                link_file_data.append(f"Title: {item.title}\nURL: {item.url}\n{tags_str}\n")
            else:
                print(f"URL for item ID {item.id} not found or None.")
    if link_file_data:
        links_file_path = os.path.join(download_path, "downloaded_links.txt")
        try:
            async with aiofiles.open(links_file_path, 'w', encoding='utf-8') as f:
                await f.write("\n---\n".join(link_file_data))
            downloaded_file_paths.append(links_file_path)
        except Exception as e:
            print(f"Error writing links file to {links_file_path}: {e}")
    return downloaded_file_paths

def share_media_by_email(selected_ids: list[str], recipient_email: str) -> str:
    items = get_media_items_by_ids(selected_ids)
    if not items:
        return f"No media items found for IDs: {selected_ids}."
    items_details = []
    for item in items:
        details = f"ID: {item.id}, Title: {item.title}"
        if item.tags:
            details += f", Tags: {', '.join(sorted(item.tags))}" # Sort tags
        items_details.append(details)
    message = (
        f"Attempting to share {len(items)} media item(s) to {recipient_email}:\n" +
        "\n".join(items_details) +
        "\nEmail functionality is not fully implemented in this backend module."
    )
    print(message)
    return f"Placeholder: Email sharing process initiated for {len(items)} items to {recipient_email}."

def share_media_by_whatsapp(selected_ids: list[str], recipient_phone: str) -> str:
    items = get_media_items_by_ids(selected_ids)
    if not items:
        return f"No media items found for IDs: {selected_ids}."
    items_details = []
    for item in items:
        details = f"ID: {item.id}, Title: {item.title}"
        if item.tags:
            details += f", Tags: {', '.join(sorted(item.tags))}" # Sort tags
        items_details.append(details)
    message = (
        f"Attempting to share {len(items)} media item(s) to WhatsApp user {recipient_phone}:\n" +
        "\n".join(items_details) +
        "\nWhatsApp functionality is not fully implemented and may require specific API integrations."
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
