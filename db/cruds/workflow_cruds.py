import sqlite3
import uuid
from datetime import datetime, timezone
import logging
from .generic_crud import GenericCRUD, _manage_conn, get_db_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class WorkflowsCRUD(GenericCRUD):
    def __init__(self, db_path=None):
        super().__init__(table_name="Workflows", id_column="workflow_id", db_path=db_path)

    @_manage_conn
    def add_workflow(self, data, conn=None, cursor=None):
        workflow_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        required_fields = ['name']
        if not all(field in data for field in required_fields):
            logging.error("Missing required fields for adding workflow.")
            return {'success': False, 'error': 'Missing required fields'}

        try:
            cursor.execute(f"""
                INSERT INTO {self.table_name}
                (workflow_id, name, description, is_default, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                workflow_id,
                data['name'],
                data.get('description'),
                data.get('is_default', 0),
                now,
                now
            ))
            conn.commit()
            logging.info(f"Workflow '{data['name']}' added with ID: {workflow_id}")
            return {'success': True, 'id': workflow_id, 'data': self.get_by_id(workflow_id, conn=conn, cursor=cursor)}
        except sqlite3.Error as e:
            logging.error(f"Error adding workflow '{data.get('name')}': {e}")
            conn.rollback()
            return {'success': False, 'error': str(e)}

    @_manage_conn
    def get_workflow_by_id(self, workflow_id, conn=None, cursor=None):
        return self.get_by_id(workflow_id, conn=conn, cursor=cursor)

    @_manage_conn
    def get_all_workflows(self, filters=None, conn=None, cursor=None):
        query = f"SELECT * FROM {self.table_name}"
        params = []
        if filters:
            conditions = []
            for key, value in filters.items():
                if key == "name": # Example filter
                    conditions.append(f"name LIKE ?")
                    params.append(f"%{value}%")
                # Add other filterable columns here
            if conditions:
                query += " WHERE " + " AND ".join(conditions)

        try:
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Error getting all workflows: {e}")
            return []

    @_manage_conn
    def update_workflow(self, workflow_id, data, conn=None, cursor=None):
        data['updated_at'] = datetime.now(timezone.utc).isoformat()
        return self.update(workflow_id, data, conn=conn, cursor=cursor)

    @_manage_conn
    def delete_workflow(self, workflow_id, conn=None, cursor=None):
        # Schema has ON DELETE CASCADE for WorkflowStates and WorkflowTransitions
        # So a direct delete here will cascade.
        return self.delete(workflow_id, conn=conn, cursor=cursor)

    @_manage_conn
    def set_default_workflow(self, workflow_id, conn=None, cursor=None):
        try:
            # First, set all other workflows to not be default
            cursor.execute(f"UPDATE {self.table_name} SET is_default = 0 WHERE workflow_id != ?", (workflow_id,))
            # Then, set the specified workflow as default
            cursor.execute(f"UPDATE {self.table_name} SET is_default = 1, updated_at = ? WHERE workflow_id = ?",
                           (datetime.now(timezone.utc).isoformat(), workflow_id))
            conn.commit()
            if cursor.rowcount > 0:
                logging.info(f"Workflow {workflow_id} set as default.")
                return {'success': True, 'message': f"Workflow {workflow_id} set as default."}
            else:
                logging.warning(f"Workflow {workflow_id} not found to set as default.")
                return {'success': False, 'error': "Workflow not found."}
        except sqlite3.Error as e:
            logging.error(f"Error setting default workflow {workflow_id}: {e}")
            conn.rollback()
            return {'success': False, 'error': str(e)}

    @_manage_conn
    def get_default_workflow(self, conn=None, cursor=None):
        try:
            cursor.execute(f"SELECT * FROM {self.table_name} WHERE is_default = 1 LIMIT 1")
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logging.error(f"Error getting default workflow: {e}")
            return None


class WorkflowStatesCRUD(GenericCRUD):
    def __init__(self, db_path=None):
        super().__init__(table_name="WorkflowStates", id_column="workflow_state_id", db_path=db_path)

    @_manage_conn
    def add_workflow_state(self, data, conn=None, cursor=None):
        workflow_state_id = str(uuid.uuid4())

        required_fields = ['workflow_id', 'status_id', 'name']
        if not all(field in data for field in required_fields):
            logging.error("Missing required fields for adding workflow state.")
            return {'success': False, 'error': 'Missing required fields'}

        try:
            cursor.execute(f"""
                INSERT INTO {self.table_name}
                (workflow_state_id, workflow_id, status_id, name, description,
                 order_in_workflow, is_start_state, is_end_state)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                workflow_state_id,
                data['workflow_id'],
                data['status_id'],
                data['name'],
                data.get('description'),
                data.get('order_in_workflow'),
                data.get('is_start_state', 0),
                data.get('is_end_state', 0)
            ))
            conn.commit()
            logging.info(f"Workflow state '{data['name']}' added with ID: {workflow_state_id} for workflow {data['workflow_id']}")
            return {'success': True, 'id': workflow_state_id, 'data': self.get_by_id(workflow_state_id, conn=conn, cursor=cursor)}
        except sqlite3.Error as e:
            logging.error(f"Error adding workflow state '{data.get('name')}': {e}")
            conn.rollback()
            return {'success': False, 'error': str(e)}

    @_manage_conn
    def get_workflow_state_by_id(self, workflow_state_id, conn=None, cursor=None):
        return self.get_by_id(workflow_state_id, conn=conn, cursor=cursor)

    @_manage_conn
    def get_workflow_states_for_workflow(self, workflow_id, conn=None, cursor=None):
        try:
            cursor.execute(f"SELECT * FROM {self.table_name} WHERE workflow_id = ? ORDER BY order_in_workflow ASC", (workflow_id,))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Error getting workflow states for workflow {workflow_id}: {e}")
            return []

    @_manage_conn
    def update_workflow_state(self, workflow_state_id, data, conn=None, cursor=None):
        # No 'updated_at' column in WorkflowStates table per schema
        return self.update(workflow_state_id, data, conn=conn, cursor=cursor)

    @_manage_conn
    def delete_workflow_state(self, workflow_state_id, conn=None, cursor=None):
        # Hard delete
        return self.delete(workflow_state_id, conn=conn, cursor=cursor)


class WorkflowTransitionsCRUD(GenericCRUD):
    def __init__(self, db_path=None):
        super().__init__(table_name="WorkflowTransitions", id_column="transition_id", db_path=db_path)

    @_manage_conn
    def add_workflow_transition(self, data, conn=None, cursor=None):
        transition_id = str(uuid.uuid4())

        required_fields = ['workflow_id', 'from_workflow_state_id', 'to_workflow_state_id', 'name']
        if not all(field in data for field in required_fields):
            logging.error("Missing required fields for adding workflow transition.")
            return {'success': False, 'error': 'Missing required fields'}

        try:
            cursor.execute(f"""
                INSERT INTO {self.table_name}
                (transition_id, workflow_id, from_workflow_state_id, to_workflow_state_id, name, description)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                transition_id,
                data['workflow_id'],
                data['from_workflow_state_id'],
                data['to_workflow_state_id'],
                data['name'],
                data.get('description')
            ))
            conn.commit()
            logging.info(f"Workflow transition '{data['name']}' added with ID: {transition_id}")
            return {'success': True, 'id': transition_id, 'data': self.get_by_id(transition_id, conn=conn, cursor=cursor)}
        except sqlite3.Error as e:
            logging.error(f"Error adding workflow transition '{data.get('name')}': {e}")
            conn.rollback()
            return {'success': False, 'error': str(e)}

    @_manage_conn
    def get_workflow_transition_by_id(self, transition_id, conn=None, cursor=None):
        return self.get_by_id(transition_id, conn=conn, cursor=cursor)

    @_manage_conn
    def get_transitions_for_workflow(self, workflow_id, conn=None, cursor=None):
        try:
            cursor.execute(f"SELECT * FROM {self.table_name} WHERE workflow_id = ?", (workflow_id,))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Error getting transitions for workflow {workflow_id}: {e}")
            return []

    @_manage_conn
    def get_transitions_from_state(self, from_workflow_state_id, conn=None, cursor=None):
        try:
            cursor.execute(f"SELECT * FROM {self.table_name} WHERE from_workflow_state_id = ?", (from_workflow_state_id,))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Error getting transitions from state {from_workflow_state_id}: {e}")
            return []

    @_manage_conn
    def get_transitions_to_state(self, to_workflow_state_id, conn=None, cursor=None):
        try:
            cursor.execute(f"SELECT * FROM {self.table_name} WHERE to_workflow_state_id = ?", (to_workflow_state_id,))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Error getting transitions to state {to_workflow_state_id}: {e}")
            return []

    @_manage_conn
    def update_workflow_transition(self, transition_id, data, conn=None, cursor=None):
        # No 'updated_at' column in WorkflowTransitions table per schema
        return self.update(transition_id, data, conn=conn, cursor=cursor)

    @_manage_conn
    def delete_workflow_transition(self, transition_id, conn=None, cursor=None):
        # Hard delete
        return self.delete(transition_id, conn=conn, cursor=cursor)


# Instantiate CRUD classes
# db_path can be configured here or through config.py if GenericCRUD is enhanced to use it
workflows_crud = WorkflowsCRUD()
workflow_states_crud = WorkflowStatesCRUD()
workflow_transitions_crud = WorkflowTransitionsCRUD()

__all__ = [
    'WorkflowsCRUD',
    'WorkflowStatesCRUD',
    'WorkflowTransitionsCRUD',
    'workflows_crud',
    'workflow_states_crud',
    'workflow_transitions_crud'
]
