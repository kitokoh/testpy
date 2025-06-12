import os
import shutil
import uuid
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any
from . import models
import db

import asyncio
import aiofiles
import aiofiles.os as aios

from PIL import Image, ExifTags # Added ExifTags
import cv2

from config import MEDIA_FILES_BASE_PATH, DEFAULT_DOWNLOAD_PATH

THUMBNAIL_SIZE = (128, 128)
THUMBNAIL_DIR_NAME = ".thumbnails"

# --- Metadata Extraction Helpers ---
def _extract_image_metadata(source_path: str) -> dict:
    metadata = {'type': 'image'}
    try:
        img = Image.open(source_path)
        metadata['width'] = img.width
        metadata['height'] = img.height
        metadata['format'] = img.format
        metadata['mode'] = img.mode

        exif_data_raw = img.getexif() # getexif() is preferred
        if exif_data_raw:
            exif_data_processed = {}
            for tag_id, value in exif_data_raw.items():
                tag_name = ExifTags.TAGS.get(tag_id, tag_id)

                # Handle bytes values by trying to decode or representing as string
                if isinstance(value, bytes):
                    try:
                        value = value.decode('utf-8', errors='replace')
                    except UnicodeDecodeError:
                        value = str(value) # Fallback for non-decodable bytes

                if tag_name == 'GPSInfo':
                    # Store raw GPSInfo dict; further processing can be done by consumer
                    gps_info_processed = {}
                    if isinstance(value, dict):
                        for gps_tag_id, gps_value in value.items():
                            gps_tag_name = ExifTags.GPSTAGS.get(gps_tag_id, gps_tag_id)
                            gps_info_processed[gps_tag_name] = str(gps_value) # Convert to string for simplicity
                    exif_data_processed[str(tag_name)] = gps_info_processed
                elif isinstance(tag_name, str): # Ensure tag_name is a string key
                     # Limit value length to avoid overly large JSON strings
                    if isinstance(value, str) and len(value) > 256:
                        value = value[:253] + "..."
                    exif_data_processed[tag_name] = value
                else: # If tag_name is still an int (unknown tag)
                    exif_data_processed[str(tag_name)] = str(value)


            if exif_data_processed: # Add only if there's something to add
                 metadata['exif'] = exif_data_processed
        img.close()
    except FileNotFoundError:
        print(f"Error: Image file not found at {source_path} for metadata extraction.")
        metadata['error'] = "File not found"
    except Exception as e:
        print(f"Error extracting image metadata for {source_path}: {e}")
        metadata['error'] = str(e)
    return metadata

def _extract_video_metadata(source_path: str) -> dict:
    metadata = {'type': 'video'}
    cap = None
    try:
        cap = cv2.VideoCapture(source_path)
        if not cap.isOpened():
            print(f"Error: Could not open video file {source_path} for metadata extraction.")
            metadata['error'] = "Could not open video file"
            return metadata

        metadata['width'] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        metadata['height'] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        metadata['fps'] = fps
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        metadata['frame_count'] = frame_count
        if fps > 0:
            metadata['duration_seconds'] = frame_count / fps
        else:
            metadata['duration_seconds'] = 0

        # FourCC code
        fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
        fourcc_str = "".join([chr((fourcc_int >> 8 * i) & 0xFF) for i in range(4)])
        metadata['fourcc'] = fourcc_str.strip()

    except Exception as e:
        print(f"Error extracting video metadata for {source_path}: {e}")
        metadata['error'] = str(e)
    finally:
        if cap:
            cap.release()
    return metadata

# --- Core Operations ---
def _generate_id() -> str:
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
    try:
        img = Image.open(source_path)
        img.thumbnail(size)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(thumb_dest_path, "JPEG")
        return True
    except Exception as e:
        print(f"Pillow: Error generating image thumbnail for {source_path}: {e}")
        return False

async def _generate_image_thumbnail(source_media_path: str, media_item_id: str) -> str | None:
    thumb_dir = os.path.join(MEDIA_FILES_BASE_PATH, THUMBNAIL_DIR_NAME)
    await aios.makedirs(thumb_dir, exist_ok=True)
    thumb_filename = f"{media_item_id}.jpg"
    thumb_dest_path_abs = os.path.join(thumb_dir, thumb_filename)
    loop = asyncio.get_event_loop()
    success = await loop.run_in_executor(None, _blocking_pil_image_thumbnail, source_media_path, thumb_dest_path_abs, THUMBNAIL_SIZE)
    if success:
        return os.path.join(THUMBNAIL_DIR_NAME, thumb_filename)
    return None

def _blocking_cv2_video_thumbnail(source_path: str, thumb_dest_path: str, size: tuple[int, int]):
    cap = None
    try:
        cap = cv2.VideoCapture(source_path)
        if not cap.isOpened():
            print(f"OpenCV: Could not open video file: {source_path}")
            return False
        cap.set(cv2.CAP_PROP_POS_FRAMES, min(50, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) -1 ))
        ret, frame = cap.read()
        if not ret:
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
        if cap: cap.release()

async def _generate_video_thumbnail(source_media_path: str, media_item_id: str) -> str | None:
    thumb_dir = os.path.join(MEDIA_FILES_BASE_PATH, THUMBNAIL_DIR_NAME)
    await aios.makedirs(thumb_dir, exist_ok=True)
    thumb_filename = f"{media_item_id}.jpg"
    thumb_dest_path_abs = os.path.join(thumb_dir, thumb_filename)
    loop = asyncio.get_event_loop()
    success = await loop.run_in_executor(None, _blocking_cv2_video_thumbnail, source_media_path, thumb_dest_path_abs, THUMBNAIL_SIZE)
    if success:
        return os.path.join(THUMBNAIL_DIR_NAME, thumb_filename)
    return None

async def add_video(title: str, description: str, filepath: str, uploader_user_id: str, tags: List[str] | None = None, metadata: Dict[str, Any] | None = None) -> models.VideoItem:
    if not await aios.path.exists(filepath):
        raise FileNotFoundError(f"Video file not found: {filepath}")
    if not uploader_user_id:
        raise ValueError("uploader_user_id is mandatory to add media.")

    item_id = _generate_id()
    _, extension = os.path.splitext(filepath)
    new_filename = f"{item_id}{extension}"
    new_media_filepath_abs = os.path.join(MEDIA_FILES_BASE_PATH, new_filename)
    new_media_filepath_rel = new_filename

    await aios.makedirs(MEDIA_FILES_BASE_PATH, exist_ok=True)
    thumbnail_rel_path = None
    extracted_metadata = {}
    try:
        async with aiofiles.open(filepath, 'rb') as src_f:
            async with aiofiles.open(new_media_filepath_abs, 'wb') as dest_f:
                while True:
                    chunk = await src_f.read(8192)
                    if not chunk: break
                    await dest_f.write(chunk)

        thumbnail_rel_path = await _generate_video_thumbnail(new_media_filepath_abs, item_id)
        # Extract metadata after successful file copy
        extracted_metadata = _extract_video_metadata(new_media_filepath_abs)

    except Exception as e_copy:
        print(f"Error during async file copy/thumb for {filepath}: {e_copy}")
        if await aios.path.exists(new_media_filepath_abs):
            try: await aios.remove(new_media_filepath_abs)
            except OSError as oe: print(f"Error cleaning up file {new_media_filepath_abs}: {oe}")
        raise

    # Combine provided metadata with extracted metadata
    final_metadata = metadata if metadata is not None else {}
    final_metadata.update(extracted_metadata) # Extracted data (like dimensions) can augment or override

    video_item_model = models.VideoItem(id=item_id, title=title, description=description, filepath=new_media_filepath_rel, tags=tags, thumbnail_path=thumbnail_rel_path, metadata=final_metadata)

    conn = None
    try:
        conn = db.get_db_connection()
        cursor = conn.cursor()
        now_iso = datetime.utcnow().isoformat()
        metadata_json_str = json.dumps(video_item_model.metadata) if video_item_model.metadata else None

        cursor.execute(
            """INSERT INTO MediaItems (media_item_id, title, description, item_type, filepath, url, uploader_user_id, created_at, updated_at, thumbnail_path, metadata_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (video_item_model.id, video_item_model.title, video_item_model.description,
             video_item_model.item_type, video_item_model.filepath, None, uploader_user_id,
             now_iso, now_iso, video_item_model.thumbnail_path, metadata_json_str)
        )
        if video_item_model.tags:
            for tag_name in video_item_model.tags:
                tag_id = _get_or_create_tag_id(tag_name, cursor)
                cursor.execute("INSERT INTO MediaItemTags (media_item_id, tag_id) VALUES (?, ?)", (video_item_model.id, tag_id))
        conn.commit()
    except sqlite3.Error as e_db:
        if conn: conn.rollback()
        print(f"Database error in add_video: {e_db}")
        raise
    finally:
        if conn: conn.close()
    return video_item_model

async def add_image(title: str, description: str, filepath: str, uploader_user_id: str, tags: List[str] | None = None, metadata: Dict[str, Any] | None = None) -> models.ImageItem:
    if not await aios.path.exists(filepath):
        raise FileNotFoundError(f"Image file not found: {filepath}")
    if not uploader_user_id:
        raise ValueError("uploader_user_id is mandatory to add media.")

    item_id = _generate_id()
    _, extension = os.path.splitext(filepath)
    new_filename = f"{item_id}{extension}"
    new_media_filepath_abs = os.path.join(MEDIA_FILES_BASE_PATH, new_filename)
    new_media_filepath_rel = new_filename

    await aios.makedirs(MEDIA_FILES_BASE_PATH, exist_ok=True)
    thumbnail_rel_path = None
    extracted_metadata = {}
    try:
        async with aiofiles.open(filepath, 'rb') as src_f:
            async with aiofiles.open(new_media_filepath_abs, 'wb') as dest_f:
                while True:
                    chunk = await src_f.read(8192)
                    if not chunk: break
                    await dest_f.write(chunk)
        thumbnail_rel_path = await _generate_image_thumbnail(new_media_filepath_abs, item_id)
        extracted_metadata = _extract_image_metadata(new_media_filepath_abs)
    except Exception as e_copy:
        print(f"Error during async file copy/thumb for {filepath}: {e_copy}")
        if await aios.path.exists(new_media_filepath_abs):
            try: await aios.remove(new_media_filepath_abs)
            except OSError as oe: print(f"Error cleaning up file {new_media_filepath_abs}: {oe}")
        raise

    final_metadata = metadata if metadata is not None else {}
    final_metadata.update(extracted_metadata)

    image_item_model = models.ImageItem(id=item_id, title=title, description=description, filepath=new_media_filepath_rel, tags=tags, thumbnail_path=thumbnail_rel_path, metadata=final_metadata)

    conn = None
    try:
        conn = db.get_db_connection()
        cursor = conn.cursor()
        now_iso = datetime.utcnow().isoformat()
        metadata_json_str = json.dumps(image_item_model.metadata) if image_item_model.metadata else None

        cursor.execute(
            """INSERT INTO MediaItems (media_item_id, title, description, item_type, filepath, url, uploader_user_id, created_at, updated_at, thumbnail_path, metadata_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (image_item_model.id, image_item_model.title, image_item_model.description,
             image_item_model.item_type, image_item_model.filepath, None, uploader_user_id,
             now_iso, now_iso, image_item_model.thumbnail_path, metadata_json_str)
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

def add_link(title: str, description: str, url: str, uploader_user_id: str, tags: List[str] | None = None, metadata: Dict[str, Any] | None = None) -> models.LinkItem:
    if not uploader_user_id:
        raise ValueError("uploader_user_id is mandatory to add media.")
    item_id = _generate_id()
    # For links, metadata might include info fetched from the URL, but that's out of scope for auto-extraction here.
    final_metadata = metadata if metadata is not None else {}
    # No specific auto-extraction for links, so final_metadata is just user-provided metadata.
    link_item_model = models.LinkItem(id=item_id, title=title, description=description, url=url, tags=tags, thumbnail_path=None, metadata=final_metadata)
    conn = None
    try:
        conn = db.get_db_connection()
        cursor = conn.cursor()
        now_iso = datetime.utcnow().isoformat()
        metadata_json_str = json.dumps(link_item_model.metadata) if link_item_model.metadata else None
        cursor.execute(
            """INSERT INTO MediaItems (media_item_id, title, description, item_type, filepath, url, uploader_user_id, created_at, updated_at, thumbnail_path, metadata_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (link_item_model.id, link_item_model.title, link_item_model.description,
             link_item_model.item_type, None, link_item_model.url, uploader_user_id,
             now_iso, now_iso, None, metadata_json_str)
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
                tags_str = f"Tags: {', '.join(sorted(item.tags))}" if item.tags else "Tags: None"
                link_file_data.append(f"Title: {item.title}\nURL: {item.url}\n{tags_str}\nMetadata: {json.dumps(item.metadata)}\n")
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
        details = f"ID: {item.id}, Title: {item.title}, Type: {item.item_type}"
        if item.tags:
            details += f", Tags: {', '.join(sorted(item.tags))}" # Sort tags
        if item.metadata:
            details += f", Metadata: {json.dumps(item.metadata)}"
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
        details = f"ID: {item.id}, Title: {item.title}, Type: {item.item_type}"
        if item.tags:
            details += f", Tags: {', '.join(sorted(item.tags))}" # Sort tags
        if item.metadata:
            details += f", Metadata: {json.dumps(item.metadata)}"
        items_details.append(details)
    message = (
        f"Attempting to share {len(items)} media item(s) to WhatsApp user {recipient_phone}:\n" +
        "\n".join(items_details) +
        "\nWhatsApp functionality is not fully implemented and may require specific API integrations."
    )
    print(message)
    return f"Placeholder: WhatsApp sharing process initiated for {len(items)} items to {recipient_phone}."
