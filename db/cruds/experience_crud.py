import sqlite3
import uuid
from db.connection import get_db_connection

# --- Experiences Table CRUD Functions ---

def add_experience(experience_data: dict, conn=None) -> str | None:
    """
    Inserts a new experience into the Experiences table.
    Returns the new experience_id or None if insertion fails.
    """
    db = conn if conn else get_db_connection()
    cursor = db.cursor()
    experience_id = str(uuid.uuid4())
    try:
        cursor.execute("""
            INSERT INTO Experiences (experience_id, title, description, experience_date, type, user_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            experience_id,
            experience_data.get('title'),
            experience_data.get('description'),
            experience_data.get('experience_date'),
            experience_data.get('type'),
            experience_data.get('user_id')
        ))
        db.commit()
        return experience_id
    except sqlite3.Error as e:
        print(f"Error adding experience: {e}")
        if not conn: # Only rollback if we opened the connection
            db.rollback()
        return None
    finally:
        if not conn: # Only close if we opened the connection
            db.close()

def get_experience_by_id(experience_id: str, conn=None) -> dict | None:
    """
    Fetches an experience by its ID.
    Returns a dictionary representing the experience or None if not found.
    """
    db = conn if conn else get_db_connection()
    db.row_factory = sqlite3.Row
    cursor = db.cursor()
    try:
        cursor.execute("SELECT * FROM Experiences WHERE experience_id = ?", (experience_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Error fetching experience by ID: {e}")
        return None
    finally:
        if not conn:
            db.close()

def get_all_experiences(filters: dict = None, limit: int = None, offset: int = 0, conn=None) -> list[dict]:
    """
    Fetches all experiences, with optional filters, limit, and offset.
    """
    db = conn if conn else get_db_connection()
    db.row_factory = sqlite3.Row
    cursor = db.cursor()

    query = "SELECT * FROM Experiences"
    params = []

    if filters:
        conditions = []
        for key, value in filters.items():
            if value is not None:
                conditions.append(f"{key} = ?")
                params.append(value)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY created_at DESC" # Default ordering

    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)
    if offset is not None and offset > 0:
        query += " OFFSET ?"
        params.append(offset)

    try:
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Error fetching all experiences: {e}")
        return []
    finally:
        if not conn:
            db.close()

def update_experience(experience_id: str, update_data: dict, conn=None) -> bool:
    """
    Updates an existing experience.
    Returns True on success, False otherwise.
    """
    db = conn if conn else get_db_connection()
    cursor = db.cursor()

    fields = []
    params = []
    for key, value in update_data.items():
        fields.append(f"{key} = ?")
        params.append(value)

    if not fields:
        return False # No fields to update

    params.append(experience_id)
    query = f"UPDATE Experiences SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE experience_id = ?"

    try:
        cursor.execute(query, params)
        db.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error updating experience: {e}")
        if not conn:
            db.rollback()
        return False
    finally:
        if not conn:
            db.close()

def delete_experience(experience_id: str, conn=None) -> bool:
    """
    Deletes an experience.
    Returns True on success, False otherwise.
    """
    db = conn if conn else get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM Experiences WHERE experience_id = ?", (experience_id,))
        db.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error deleting experience: {e}")
        if not conn:
            db.rollback()
        return False
    finally:
        if not conn:
            db.close()

# --- ExperienceRelatedEntities Table CRUD Functions ---

def add_experience_related_entity(experience_id: str, entity_type: str, entity_id: str, conn=None) -> int | None:
    """
    Links an entity to an experience.
    Returns the new experience_related_entity_id or None if insertion fails.
    """
    db = conn if conn else get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("""
            INSERT INTO ExperienceRelatedEntities (experience_id, entity_type, entity_id)
            VALUES (?, ?, ?)
        """, (experience_id, entity_type, entity_id))
        db.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Error adding experience related entity: {e}")
        if not conn:
            db.rollback()
        return None
    finally:
        if not conn:
            db.close()

def get_related_entities_for_experience(experience_id: str, conn=None) -> list[dict]:
    """
    Fetches all entities related to an experience.
    """
    db = conn if conn else get_db_connection()
    db.row_factory = sqlite3.Row
    cursor = db.cursor()
    try:
        cursor.execute("SELECT * FROM ExperienceRelatedEntities WHERE experience_id = ?", (experience_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Error fetching related entities for experience: {e}")
        return []
    finally:
        if not conn:
            db.close()

def remove_experience_related_entity(experience_related_entity_id: int, conn=None) -> bool:
    """
    Removes a specific link by its own ID.
    Returns True on success, False otherwise.
    """
    db = conn if conn else get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM ExperienceRelatedEntities WHERE experience_related_entity_id = ?", (experience_related_entity_id,))
        db.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error removing experience related entity: {e}")
        if not conn:
            db.rollback()
        return False
    finally:
        if not conn:
            db.close()

def remove_all_related_entities_for_experience(experience_id: str, conn=None) -> bool:
    """
    Removes all entity links for an experience.
    Returns True on success, False otherwise.
    """
    db = conn if conn else get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM ExperienceRelatedEntities WHERE experience_id = ?", (experience_id,))
        db.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error removing all related entities for experience: {e}")
        if not conn:
            db.rollback()
        return False
    finally:
        if not conn:
            db.close()

# --- ExperienceMedia Table CRUD Functions ---

def add_experience_media(experience_id: str, media_item_id: str, conn=None) -> int | None:
    """
    Links a media item to an experience.
    Returns the new experience_media_id or None if insertion fails.
    """
    db = conn if conn else get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("""
            INSERT INTO ExperienceMedia (experience_id, media_item_id)
            VALUES (?, ?)
        """, (experience_id, media_item_id))
        db.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Error adding experience media: {e}")
        if not conn:
            db.rollback()
        return None
    finally:
        if not conn:
            db.close()

def get_media_for_experience(experience_id: str, conn=None) -> list[dict]:
    """
    Fetches all media items linked to an experience.
    """
    db = conn if conn else get_db_connection()
    db.row_factory = sqlite3.Row
    cursor = db.cursor()
    try:
        # This query could be enhanced to join with MediaItems table to get media details
        cursor.execute("""
            SELECT em.experience_media_id, em.experience_id, em.media_item_id, mi.title as media_title, mi.filepath as media_filepath, mi.item_type as media_type
            FROM ExperienceMedia em
            JOIN MediaItems mi ON em.media_item_id = mi.media_item_id
            WHERE em.experience_id = ?
        """, (experience_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Error fetching media for experience: {e}")
        return []
    finally:
        if not conn:
            db.close()

def remove_experience_media(experience_media_id: int, conn=None) -> bool:
    """
    Removes a specific media link by its own ID.
    Returns True on success, False otherwise.
    """
    db = conn if conn else get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM ExperienceMedia WHERE experience_media_id = ?", (experience_media_id,))
        db.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error removing experience media: {e}")
        if not conn:
            db.rollback()
        return False
    finally:
        if not conn:
            db.close()

def remove_all_media_for_experience(experience_id: str, conn=None) -> bool:
    """
    Removes all media links for an experience.
    Returns True on success, False otherwise.
    """
    db = conn if conn else get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM ExperienceMedia WHERE experience_id = ?", (experience_id,))
        db.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error removing all media for experience: {e}")
        if not conn:
            db.rollback()
        return False
    finally:
        if not conn:
            db.close()

# --- ExperienceTags Table CRUD Functions ---

def add_experience_tag(experience_id: str, tag_id: int, conn=None) -> int | None:
    """
    Adds a tag to an experience.
    Returns the new experience_tag_id or None if insertion fails.
    """
    db = conn if conn else get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("""
            INSERT INTO ExperienceTags (experience_id, tag_id)
            VALUES (?, ?)
        """, (experience_id, tag_id))
        db.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Error adding experience tag: {e}")
        if not conn:
            db.rollback()
        return None
    finally:
        if not conn:
            db.close()

def get_tags_for_experience(experience_id: str, conn=None) -> list[dict]:
    """
    Fetches all tags for an experience.
    Joins with the Tags table to get tag names.
    """
    db = conn if conn else get_db_connection()
    db.row_factory = sqlite3.Row
    cursor = db.cursor()
    try:
        cursor.execute("""
            SELECT et.experience_tag_id, et.experience_id, et.tag_id, t.tag_name
            FROM ExperienceTags et
            JOIN Tags t ON et.tag_id = t.tag_id
            WHERE et.experience_id = ?
        """, (experience_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Error fetching tags for experience: {e}")
        return []
    finally:
        if not conn:
            db.close()

def remove_experience_tag_link(experience_id: str, tag_id: int, conn=None) -> bool:
    """
    Removes a specific tag link by experience_id and tag_id.
    Returns True on success, False otherwise.
    """
    db = conn if conn else get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM ExperienceTags WHERE experience_id = ? AND tag_id = ?", (experience_id, tag_id))
        db.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error removing experience tag link: {e}")
        if not conn:
            db.rollback()
        return False
    finally:
        if not conn:
            db.close()

def remove_all_tags_for_experience(experience_id: str, conn=None) -> bool:
    """
    Removes all tag links for an experience.
    Returns True on success, False otherwise.
    """
    db = conn if conn else get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM ExperienceTags WHERE experience_id = ?", (experience_id,))
        db.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error removing all tags for experience: {e}")
        if not conn:
            db.rollback()
        return False
    finally:
        if not conn:
            db.close()
