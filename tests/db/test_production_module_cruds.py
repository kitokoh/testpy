import unittest
import sqlite3
import os
import sys
from datetime import datetime, timedelta

# Add the project root to sys.path to allow imports from db and other modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from db import db_config
from db.schema import initialize_database
from db.cruds import projects_crud, tasks_crud, status_settings_crud, team_members_crud, clients_crud

class TestProductionModuleCRUDS(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Set up an in-memory database for all tests in this class.
        This is called once before any tests are run.
        """
        cls.original_db_path = db_config.DATABASE_PATH
        db_config.DATABASE_PATH = ":memory:"
        # print(f"Testing with DB: {db_config.DATABASE_PATH}")

        # Initialize schema
        conn = sqlite3.connect(db_config.DATABASE_PATH)
        initialize_database() # This function now uses db_config.DATABASE_PATH internally
        conn.close()

    @classmethod
    def tearDownClass(cls):
        """
        Restore the original database path after all tests in this class.
        """
        db_config.DATABASE_PATH = cls.original_db_path
        # print(f"Restored DB path to: {db_config.DATABASE_PATH}")

    def setUp(self):
        """
        Called before each test method.
        Ensures a clean database state for each test by re-initializing.
        Alternatively, could use transactions and rollback, but re-init is simpler for :memory:.
        """
        # Each test gets a fresh in-memory DB by re-initializing the schema
        # For :memory: dbs, the db is gone when connection is closed.
        # So, we need a connection that persists for the test, or re-init schema for each test.
        self.conn = sqlite3.connect(db_config.DATABASE_PATH)
        self.conn.row_factory = sqlite3.Row # For dict-like access to rows

        # Re-initialize schema for a clean slate if tables might be modified by tests.
        # If initialize_database() is idempotent (uses IF NOT EXISTS), this is safe.
        initialize_database()

        # Seed necessary data
        self._seed_status_settings()
        self._seed_team_members()
        self._seed_clients()


    def tearDown(self):
        """
        Called after each test method.
        Closes the database connection.
        """
        if self.conn:
            self.conn.close()

    def _seed_status_settings(self):
        # Common Project Statuses
        status_settings_crud.add_status_setting({'status_name': 'Planning', 'status_type': 'Project', 'color_hex': '#F1C40F'}, conn=self.conn)
        status_settings_crud.add_status_setting({'status_name': 'Project In Progress', 'status_type': 'Project', 'color_hex': '#3498DB'}, conn=self.conn)
        status_settings_crud.add_status_setting({'status_name': 'Project Completed', 'status_type': 'Project', 'color_hex': '#2ECC71', 'is_completion_status': True}, conn=self.conn)

        # Common Task Statuses
        status_settings_crud.add_status_setting({'status_name': 'To Do', 'status_type': 'Task', 'color_hex': '#E74C3C'}, conn=self.conn)
        status_settings_crud.add_status_setting({'status_name': 'Task In Progress', 'status_type': 'Task', 'color_hex': '#F39C12'}, conn=self.conn)
        status_settings_crud.add_status_setting({'status_name': 'Task Completed', 'status_type': 'Task', 'color_hex': '#27AE60', 'is_completion_status': True}, conn=self.conn)
        status_settings_crud.add_status_setting({'status_name': 'Archived Task', 'status_type': 'Task', 'color_hex': '#BDC3C7', 'is_archival_status': True}, conn=self.conn)
        # Add more statuses if your tests require them, e.g., 'On Hold', 'Cancelled'
        status_settings_crud.add_status_setting({'status_name': 'Project On Hold', 'status_type': 'Project', 'color_hex': '#7F8C8D'}, conn=self.conn)


    def _seed_team_members(self):
        tm1_data = {'full_name': 'Prod Manager Alice', 'email': f'alice.{datetime.now().strftime("%Y%m%d%H%M%S%f")}@example.com', 'role_or_title': 'Production Manager'}
        tm2_data = {'full_name': 'Worker Bob', 'email': f'bob.{datetime.now().strftime("%Y%m%d%H%M%S%f")}@example.com', 'role_or_title': 'Technician'}

        # Store created team member IDs if needed for specific tests
        self.tm_alice_id = team_members_crud.add_team_member(tm1_data, conn=self.conn)
        self.tm_bob_id = team_members_crud.add_team_member(tm2_data, conn=self.conn)

        self.assertIsNotNone(self.tm_alice_id, "Failed to seed team member Alice")
        self.assertIsNotNone(self.tm_bob_id, "Failed to seed team member Bob")


    def _seed_clients(self):
        client_data = {'client_name': 'Test Client Corp',
                       'project_identifier': 'TCC',
                       'default_base_folder_path': f'/tmp/tcc_{datetime.now().strftime("%Y%m%d%H%M%S%f")}'} # Ensure unique path

        self.client_id = clients_crud.add_client(client_data, conn=self.conn)
        self.assertIsNotNone(self.client_id, "Failed to seed client")


    # --- Tests for projects_crud.py (Production Orders) ---

    def test_add_production_order(self):
        # Get a status_id for 'Planning'
        planning_status = status_settings_crud.get_status_setting_by_name("Planning", "Project", conn=self.conn)
        self.assertIsNotNone(planning_status, "Planning status not found for project.")
        planning_status_id = planning_status['status_id']

        # Get a manager_id (assuming first team member)
        all_members = team_members_crud.get_all_team_members(conn=self.conn)
        self.assertTrue(all_members, "No team members available to assign as manager.")
        manager_id = all_members[0]['team_member_id']

        prod_order_data = {
            'project_name': 'PO-001',
            'project_type': 'PRODUCTION',
            'description': 'Production order for 100 widgets.',
            'status_id': planning_status_id,
            'manager_team_member_id': manager_id,
            'start_date': datetime.now().strftime('%Y-%m-%d'),
            'deadline_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'priority': 1 # Medium
        }
        project_id = projects_crud.add_project(prod_order_data, conn=self.conn)
        self.assertIsNotNone(project_id, "add_project should return a project_id for production order.")

        retrieved_order = projects_crud.get_project_by_id(project_id, conn=self.conn)
        self.assertIsNotNone(retrieved_order, "Failed to retrieve production order after adding.")
        self.assertEqual(retrieved_order['project_type'], 'PRODUCTION')
        self.assertEqual(retrieved_order['project_name'], 'PO-001')
        self.assertEqual(retrieved_order['status_id'], planning_status_id)
        self.assertEqual(retrieved_order['manager_team_member_id'], manager_id)

    def test_get_all_projects_with_production_filter(self):
        planning_status = status_settings_crud.get_status_setting_by_name("Planning", "Project", conn=self.conn)
        manager = team_members_crud.get_all_team_members(conn=self.conn)[0]

        # Add a standard project
        std_project_data = {
            'project_name': 'Standard Project Alpha',
            'project_type': 'STANDARD',
            'status_id': planning_status['status_id'],
            'manager_team_member_id': manager['team_member_id']
        }
        projects_crud.add_project(std_project_data, conn=self.conn)

        # Add a production order
        prod_order_data = {
            'project_name': 'PO-002',
            'project_type': 'PRODUCTION',
            'status_id': planning_status['status_id'],
            'manager_team_member_id': manager['team_member_id']
        }
        projects_crud.add_project(prod_order_data, conn=self.conn)

        # Test filter for PRODUCTION
        production_orders = projects_crud.get_all_projects(filters={'project_type': 'PRODUCTION'}, conn=self.conn)
        self.assertEqual(len(production_orders), 1, "Should retrieve only one production order.")
        self.assertEqual(production_orders[0]['project_name'], 'PO-002')

        # Test filter for STANDARD
        standard_projects = projects_crud.get_all_projects(filters={'project_type': 'STANDARD'}, conn=self.conn)
        self.assertEqual(len(standard_projects), 1, "Should retrieve only one standard project.")
        self.assertEqual(standard_projects[0]['project_name'], 'Standard Project Alpha')

        # Test getting all (no type filter)
        all_projects_list = projects_crud.get_all_projects(conn=self.conn)
        self.assertEqual(len(all_projects_list), 2, "Should retrieve all projects when no type filter is applied.")


    def test_update_production_order(self):
        planning_status = status_settings_crud.get_status_setting_by_name("Planning", "Project", conn=self.conn)
        inprogress_status = status_settings_crud.get_status_setting_by_name("Project In Progress", "Project", conn=self.conn)
        manager = team_members_crud.get_all_team_members(conn=self.conn)[0]

        prod_order_data = {
            'project_name': 'PO-003',
            'project_type': 'PRODUCTION',
            'description': 'Initial description.',
            'status_id': planning_status['status_id'],
            'manager_team_member_id': manager['team_member_id']
        }
        project_id = projects_crud.add_project(prod_order_data, conn=self.conn)
        self.assertIsNotNone(project_id)

        update_data = {
            'project_name': 'PO-003-Updated',
            'description': 'Updated description.',
            'status_id': inprogress_status['status_id'],
            'priority': 2 # High
        }
        success = projects_crud.update_project(project_id, update_data, conn=self.conn)
        self.assertTrue(success, "Update project should return True on success.")

        updated_order = projects_crud.get_project_by_id(project_id, conn=self.conn)
        self.assertIsNotNone(updated_order)
        self.assertEqual(updated_order['project_name'], 'PO-003-Updated')
        self.assertEqual(updated_order['description'], 'Updated description.')
        self.assertEqual(updated_order['status_id'], inprogress_status['status_id'])
        self.assertEqual(updated_order['priority'], 2)
        self.assertEqual(updated_order['project_type'], 'PRODUCTION', "Project type should not change on update.")

    def test_delete_production_order_cascades_tasks(self):
        planning_status = status_settings_crud.get_status_setting_by_name("Planning", "Project", conn=self.conn)
        manager = team_members_crud.get_all_team_members(conn=self.conn)[0]
        todo_task_status = status_settings_crud.get_status_setting_by_name("To Do", "Task", conn=self.conn)

        prod_order_data = {
            'project_name': 'PO-004-Cascading',
            'project_type': 'PRODUCTION',
            'status_id': planning_status['status_id'],
            'manager_team_member_id': manager['team_member_id']
        }
        project_id = projects_crud.add_project(prod_order_data, conn=self.conn)
        self.assertIsNotNone(project_id)

        # Add tasks (steps) to this production order
        task1_data = {'project_id': project_id, 'task_name': 'Step 1', 'sequence_order': 1, 'status_id': todo_task_status['status_id']}
        task2_data = {'project_id': project_id, 'task_name': 'Step 2', 'sequence_order': 2, 'status_id': todo_task_status['status_id']}
        tasks_crud.add_task(task1_data, conn=self.conn)
        tasks_crud.add_task(task2_data, conn=self.conn)

        tasks_before_delete = tasks_crud.get_tasks_by_project_id(project_id, conn=self.conn)
        self.assertEqual(len(tasks_before_delete), 2, "Should have 2 tasks before deleting the project.")

        # Delete the production order
        success = projects_crud.delete_project(project_id, conn=self.conn)
        self.assertTrue(success, "delete_project should return True on successful deletion.")

        # Assert project is deleted
        self.assertIsNone(projects_crud.get_project_by_id(project_id, conn=self.conn), "Production order should be deleted.")

        # Assert tasks associated with the project are also deleted (due to ON DELETE CASCADE)
        tasks_after_delete = tasks_crud.get_tasks_by_project_id(project_id, conn=self.conn)
        self.assertEqual(len(tasks_after_delete), 0, "Tasks (steps) should be deleted by cascade when production order is deleted.")

    # --- Tests for tasks_crud.py (Production Steps) ---

    def _create_sample_production_order(self, name_suffix=""):
        """Helper to create a production order for task tests."""
        planning_status = status_settings_crud.get_status_setting_by_name("Planning", "Project", conn=self.conn)
        manager = team_members_crud.get_all_team_members(conn=self.conn)[0]
        po_data = {
            'project_name': f'PO-For-Tasks{name_suffix}',
            'project_type': 'PRODUCTION',
            'status_id': planning_status['status_id'],
            'manager_team_member_id': manager['team_member_id']
        }
        po_id = projects_crud.add_project(po_data, conn=self.conn)
        self.assertIsNotNone(po_id)
        return po_id

    def test_add_production_step(self):
        po_id = self._create_sample_production_order()
        todo_status = status_settings_crud.get_status_setting_by_name("To Do", "Task", conn=self.conn)

        step_data = {
            'project_id': po_id,
            'task_name': 'Design Widget',
            'description': 'Detailed design of the new widget.',
            'status_id': todo_status['status_id'],
            'priority': 1, # Medium
            'sequence_order': 1,
            'estimated_duration_hours': 10.5
        }
        step_id = tasks_crud.add_task(step_data, conn=self.conn)
        self.assertIsNotNone(step_id, "add_task should return a task_id for the production step.")

        retrieved_step = tasks_crud.get_task_by_id(step_id, conn=self.conn)
        self.assertIsNotNone(retrieved_step)
        self.assertEqual(retrieved_step['task_name'], 'Design Widget')
        self.assertEqual(retrieved_step['project_id'], po_id)
        self.assertEqual(retrieved_step['sequence_order'], 1)
        self.assertEqual(retrieved_step['estimated_duration_hours'], 10.5)

    def test_get_steps_for_production_order_ordered(self):
        po_id = self._create_sample_production_order()
        todo_status_id = status_settings_crud.get_status_setting_by_name("To Do", "Task", conn=self.conn)['status_id']

        step1_data = {'project_id': po_id, 'task_name': 'Step Alpha', 'sequence_order': 2, 'status_id': todo_status_id}
        step2_data = {'project_id': po_id, 'task_name': 'Step Beta', 'sequence_order': 1, 'status_id': todo_status_id}
        step3_data = {'project_id': po_id, 'task_name': 'Step Gamma', 'sequence_order': 3, 'status_id': todo_status_id}
        tasks_crud.add_task(step1_data, conn=self.conn)
        tasks_crud.add_task(step2_data, conn=self.conn)
        tasks_crud.add_task(step3_data, conn=self.conn)

        ordered_steps = tasks_crud.get_tasks_by_project_id_ordered_by_sequence(po_id, conn=self.conn)
        self.assertEqual(len(ordered_steps), 3)
        self.assertEqual(ordered_steps[0]['task_name'], 'Step Beta') # seq 1
        self.assertEqual(ordered_steps[1]['task_name'], 'Step Alpha') # seq 2
        self.assertEqual(ordered_steps[2]['task_name'], 'Step Gamma') # seq 3

    def test_update_production_step(self):
        po_id = self._create_sample_production_order()
        todo_status_id = status_settings_crud.get_status_setting_by_name("To Do", "Task", conn=self.conn)['status_id']
        inprogress_status_id = status_settings_crud.get_status_setting_by_name("Task In Progress", "Task", conn=self.conn)['status_id']
        assignee_bob_id = self.tm_bob_id

        step_data = {'project_id': po_id, 'task_name': 'Initial Step Name', 'sequence_order': 1, 'status_id': todo_status_id}
        step_id = tasks_crud.add_task(step_data, conn=self.conn)
        self.assertIsNotNone(step_id)

        update_data = {
            'task_name': 'Updated Step Name',
            'description': 'Now with more details.',
            'status_id': inprogress_status_id,
            'priority': 2, # High
            'assignee_team_member_id': assignee_bob_id,
            'due_date': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
            'sequence_order': 5
        }
        success = tasks_crud.update_task(step_id, update_data, conn=self.conn)
        self.assertTrue(success)

        updated_step = tasks_crud.get_task_by_id(step_id, conn=self.conn)
        self.assertEqual(updated_step['task_name'], 'Updated Step Name')
        self.assertEqual(updated_step['description'], 'Now with more details.')
        self.assertEqual(updated_step['status_id'], inprogress_status_id)
        self.assertEqual(updated_step['priority'], 2)
        self.assertEqual(updated_step['assignee_team_member_id'], assignee_bob_id)
        self.assertIsNotNone(updated_step['due_date'])
        self.assertEqual(updated_step['sequence_order'], 5)

    def test_delete_production_step(self):
        po_id = self._create_sample_production_order()
        todo_status_id = status_settings_crud.get_status_setting_by_name("To Do", "Task", conn=self.conn)['status_id']
        step_data = {'project_id': po_id, 'task_name': 'Step To Delete', 'sequence_order': 1, 'status_id': todo_status_id}
        step_id = tasks_crud.add_task(step_data, conn=self.conn)
        self.assertIsNotNone(step_id)

        success = tasks_crud.delete_task(step_id, conn=self.conn)
        self.assertTrue(success)
        self.assertIsNone(tasks_crud.get_task_by_id(step_id, conn=self.conn))

    def test_task_dependencies_for_steps(self):
        po_id = self._create_sample_production_order()
        todo_status_id = status_settings_crud.get_status_setting_by_name("To Do", "Task", conn=self.conn)['status_id']

        step1_id = tasks_crud.add_task({'project_id': po_id, 'task_name': 'Predecessor Step', 'sequence_order': 1, 'status_id': todo_status_id}, conn=self.conn)
        step2_id = tasks_crud.add_task({'project_id': po_id, 'task_name': 'Successor Step', 'sequence_order': 2, 'status_id': todo_status_id}, conn=self.conn)
        self.assertIsNotNone(step1_id)
        self.assertIsNotNone(step2_id)

        dep_id = tasks_crud.add_task_dependency({'task_id': step2_id, 'predecessor_task_id': step1_id}, conn=self.conn)
        self.assertIsNotNone(dep_id)

        predecessors = tasks_crud.get_predecessor_tasks(step2_id, conn=self.conn)
        self.assertEqual(len(predecessors), 1)
        self.assertEqual(predecessors[0]['task_id'], step1_id)

        # Note: get_successor_tasks was a bonus, if it's not in tasks_crud, this part can be removed or adapted
        if hasattr(tasks_crud, 'get_successor_tasks'):
            successors = tasks_crud.get_successor_tasks(step1_id, conn=self.conn)
            self.assertEqual(len(successors), 1)
            self.assertEqual(successors[0]['task_id'], step2_id)

        remove_success = tasks_crud.remove_task_dependency(step2_id, step1_id, conn=self.conn)
        self.assertTrue(remove_success)
        self.assertEqual(len(tasks_crud.get_predecessor_tasks(step2_id, conn=self.conn)), 0)

    def test_get_tasks_by_assignee_id_for_steps(self):
        po_id = self._create_sample_production_order()
        assignee_bob_id = self.tm_bob_id # Seeded team member

        todo_status_id = status_settings_crud.get_status_setting_by_name("To Do", "Task", conn=self.conn)['status_id']
        completed_task_status_id = status_settings_crud.get_status_setting_by_name("Task Completed", "Task", conn=self.conn)['status_id']

        step1_data = {'project_id': po_id, 'task_name': 'Bobs Active Step', 'assignee_team_member_id': assignee_bob_id, 'status_id': todo_status_id}
        step2_data = {'project_id': po_id, 'task_name': 'Bobs Completed Step', 'assignee_team_member_id': assignee_bob_id, 'status_id': completed_task_status_id}

        step1_id = tasks_crud.add_task(step1_data, conn=self.conn)
        step2_id = tasks_crud.add_task(step2_data, conn=self.conn)

        # Test active_only = False (default)
        bob_all_tasks = tasks_crud.get_tasks_by_assignee_id(assignee_bob_id, conn=self.conn)
        self.assertEqual(len(bob_all_tasks), 2)

        # Test active_only = True
        bob_active_tasks = tasks_crud.get_tasks_by_assignee_id(assignee_bob_id, active_only=True, conn=self.conn)
        self.assertEqual(len(bob_active_tasks), 1)
        self.assertEqual(bob_active_tasks[0]['task_id'], step1_id)


if __name__ == '__main__':
    unittest.main()
