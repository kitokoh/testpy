import sqlite3
import uuid
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional, Any

from .generic_crud import GenericCRUD, _manage_conn
from ..utils import get_db_connection # Assuming get_db_connection is in ..utils

# Configure logging
logger = logging.getLogger(__name__)

class MoneyTransferAgentsCRUD(GenericCRUD):
    """
    Manages CRUD operations for MoneyTransferAgents.
    """
    def __init__(self):
        super().__init__(table_name="MoneyTransferAgents", primary_key="agent_id")

    @_manage_conn
    def add_money_transfer_agent(self, data: Dict[str, Any], conn: sqlite3.Connection = None) -> Dict[str, Any]:
        """
        Adds a new money transfer agent to the database.

        Args:
            data (dict): A dictionary containing agent details:
                         'name' (TEXT NOT NULL),
                         'agent_type' (TEXT CHECK(agent_type IN ('Bank', 'Individual Agent', 'Other')) NOT NULL),
                         'phone_number' (TEXT, optional),
                         'email' (TEXT, optional),
                         'country_id' (TEXT, optional, FK to Countries),
                         'city_id' (TEXT, optional, FK to Cities).
            conn (sqlite3.Connection, optional): Database connection. Managed by decorator.

        Returns:
            dict: {'success': True, 'agent_id': new_id} or {'success': False, 'error': 'message'}.
        """
        required_fields = ['name', 'agent_type']
        for field in required_fields:
            if not data.get(field):
                logger.error(f"Missing required field: {field} in add_money_transfer_agent")
                return {'success': False, 'error': f"Missing required field: {field}"}

        if data['agent_type'] not in ('Bank', 'Individual Agent', 'Other'):
            logger.error(f"Invalid agent_type: {data['agent_type']}")
            return {'success': False, 'error': f"Invalid agent_type: {data['agent_type']}. Must be 'Bank', 'Individual Agent', or 'Other'."}

        agent_id = str(uuid.uuid4())
        now_utc = datetime.now(timezone.utc).isoformat()

        sql = """
            INSERT INTO MoneyTransferAgents (
                agent_id, name, agent_type, phone_number, email,
                country_id, city_id, created_at, updated_at, is_deleted
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            agent_id,
            data['name'],
            data['agent_type'],
            data.get('phone_number'),
            data.get('email'),
            data.get('country_id'),
            data.get('city_id'),
            now_utc,
            now_utc,
            0  # is_deleted
        )
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return {'success': True, 'agent_id': agent_id}
        except sqlite3.IntegrityError as e: # Catch foreign key or check constraint violations
            logger.error(f"Database integrity error adding money transfer agent '{data.get('name')}': {e}")
            return {'success': False, 'error': f"Database integrity error: {e}"}
        except sqlite3.Error as e:
            logger.error(f"Failed to add money transfer agent '{data.get('name')}': {e}")
            return {'success': False, 'error': str(e)}

    @_manage_conn
    def get_money_transfer_agent_by_id(self, agent_id: str, conn: sqlite3.Connection = None, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        """
        Fetches a money transfer agent by its agent_id.

        Args:
            agent_id (str): The UUID of the agent to fetch.
            conn (sqlite3.Connection, optional): Database connection.
            include_deleted (bool, optional): If True, includes soft-deleted agents. Defaults to False.

        Returns:
            dict | None: A dictionary representing the agent if found, otherwise None.
        """
        query = f"SELECT * FROM {self.table_name} WHERE {self.primary_key} = ?"
        params = [agent_id]
        if not include_deleted:
            query += " AND (is_deleted = 0 OR is_deleted IS NULL)"

        try:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error fetching agent by ID '{agent_id}': {e}")
            return None

    @_manage_conn
    def get_all_money_transfer_agents(self, filters: Optional[Dict[str, Any]] = None, conn: sqlite3.Connection = None, include_deleted: bool = False, limit: Optional[int] = None, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Fetches all money transfer agents, with optional filtering and pagination.

        Args:
            filters (dict, optional): Filters like {'agent_type': 'Bank', 'country_id': 'uuid'}.
            conn (sqlite3.Connection, optional): Database connection.
            include_deleted (bool, optional): If True, includes soft-deleted agents. Defaults to False.
            limit (int, optional): Max number of records.
            offset (int, optional): Records to skip.

        Returns:
            list[dict]: A list of agent dictionaries.
        """
        query = f"SELECT * FROM {self.table_name}"
        q_params = []
        conditions = []

        if not include_deleted:
            conditions.append("(is_deleted = 0 OR is_deleted IS NULL)")

        if filters:
            valid_filters = ['agent_type', 'country_id', 'city_id', 'name']
            for key, value in filters.items():
                if key in valid_filters:
                    if value is not None:
                        if key == 'name': # Add LIKE for name search
                            conditions.append(f"{key} LIKE ?")
                            q_params.append(f"%{value}%")
                        else:
                            conditions.append(f"{key} = ?")
                            q_params.append(value)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY name ASC"  # Default ordering

        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            q_params.extend([limit, offset])

        try:
            cursor = conn.cursor()
            cursor.execute(query, tuple(q_params))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error fetching all money transfer agents with filters '{filters}': {e}")
            return []

    @_manage_conn
    def update_money_transfer_agent(self, agent_id: str, data: Dict[str, Any], conn: sqlite3.Connection = None) -> Dict[str, Any]:
        """
        Updates a money transfer agent's information.

        Args:
            agent_id (str): The UUID of the agent to update.
            data (dict): Dictionary with fields to update. Can include 'is_deleted' and 'deleted_at'.
            conn (sqlite3.Connection, optional): Database connection.

        Returns:
            dict: {'success': True, 'updated_count': count} or {'success': False, 'error': 'message'}.
        """
        if not agent_id:
            return {'success': False, 'error': "Agent ID is required for update."}
        if not data:
            return {'success': False, 'error': "No data provided for update."}

        now_utc = datetime.now(timezone.utc).isoformat()
        data['updated_at'] = now_utc

        # Handle soft delete fields explicitly
        if 'is_deleted' in data and data['is_deleted'] == 1 and 'deleted_at' not in data:
            data['deleted_at'] = now_utc
        elif 'is_deleted' in data and (data['is_deleted'] == 0 or data['is_deleted'] is None):
            data['deleted_at'] = None # Recovering the agent

        valid_cols = ['name', 'agent_type', 'phone_number', 'email', 'country_id', 'city_id',
                      'updated_at', 'is_deleted', 'deleted_at']

        if 'agent_type' in data and data['agent_type'] not in ('Bank', 'Individual Agent', 'Other'):
            logger.error(f"Invalid agent_type: {data['agent_type']} for agent {agent_id}")
            return {'success': False, 'error': f"Invalid agent_type: {data['agent_type']}. Must be 'Bank', 'Individual Agent', or 'Other'."}

        set_clauses = []
        params = []
        for col in valid_cols:
            if col in data:
                set_clauses.append(f"{col} = ?")
                params.append(data[col])

        if not set_clauses:
            return {'success': False, 'error': "No valid fields to update."}

        params.append(agent_id)
        sql = f"UPDATE {self.table_name} SET {', '.join(set_clauses)} WHERE {self.primary_key} = ?"

        try:
            cursor = conn.cursor()
            cursor.execute(sql, tuple(params))
            return {'success': cursor.rowcount > 0, 'updated_count': cursor.rowcount}
        except sqlite3.IntegrityError as e: # Catch foreign key or check constraint violations
             logger.error(f"Database integrity error updating money transfer agent '{agent_id}': {e}")
             return {'success': False, 'error': f"Database integrity error: {e}"}
        except sqlite3.Error as e:
            logger.error(f"Failed to update money transfer agent {agent_id}: {e}")
            return {'success': False, 'error': str(e)}

    @_manage_conn
    def delete_money_transfer_agent(self, agent_id: str, conn: sqlite3.Connection = None) -> Dict[str, Any]:
        """
        Soft deletes a money transfer agent.

        Args:
            agent_id (str): The UUID of the agent to soft delete.
            conn (sqlite3.Connection, optional): Database connection.

        Returns:
            dict: {'success': True, 'message': 'Agent soft deleted.'} or appropriate error.
        """
        if not agent_id:
            return {'success': False, 'error': "Agent ID is required for deletion."}

        now_utc = datetime.now(timezone.utc).isoformat()
        update_data = {'is_deleted': 1, 'deleted_at': now_utc}

        # Use the update method to perform soft delete for consistency
        # This also ensures updated_at is set.
        return self.update_money_transfer_agent(agent_id=agent_id, data=update_data, conn=conn)


# Instantiate for easy import
money_transfer_agents_crud = MoneyTransferAgentsCRUD()

# Functions to be exported for direct use
add_money_transfer_agent = money_transfer_agents_crud.add_money_transfer_agent
get_money_transfer_agent_by_id = money_transfer_agents_crud.get_money_transfer_agent_by_id
get_all_money_transfer_agents = money_transfer_agents_crud.get_all_money_transfer_agents
update_money_transfer_agent = money_transfer_agents_crud.update_money_transfer_agent
delete_money_transfer_agent = money_transfer_agents_crud.delete_money_transfer_agent # Soft delete

__all__ = [
    "add_money_transfer_agent",
    "get_money_transfer_agent_by_id",
    "get_all_money_transfer_agents",
    "update_money_transfer_agent",
    "delete_money_transfer_agent",
    "MoneyTransferAgentsCRUD" # Exporting class for type hinting or direct instantiation
]
