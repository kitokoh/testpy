import unittest
from unittest.mock import MagicMock, patch

# Assuming the path to your templates_crud module
# Adjust if your project structure is different
from db.cruds.templates_crud import get_all_templates

# Mock the _manage_conn decorator for testing CRUD functions in isolation
# This avoids needing a real DB connection for these unit tests.
# The decorator normally handles the connection. We'll make it a pass-through.
def mock_decorator(func):
    def wrapper(*args, **kwargs):
        # If 'conn' is expected by the function, add a mock connection
        if 'conn' not in kwargs:
            kwargs['conn'] = MagicMock()
        return func(*args, **kwargs)
    return wrapper

# Apply the mock decorator to the functions in the module to be tested.
# This needs to be done before the tests run.
# One way is to patch it globally for the test module.
# For simplicity here, if templates_crud.py uses @_manage_conn, we assume it's patched
# or we design tests to provide the 'conn' argument.
# The functions in templates_crud.py are defined with 'conn: sqlite3.Connection = None'
# and @_manage_conn injects it if None. So, providing 'conn' in tests is an option.

class TestGetAllTemplates(unittest.TestCase):

    def setUp(self):
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor

    def test_get_all_templates_no_filters(self):
        """Test get_all_templates with no filters, expecting all templates."""
        mock_data = [
            {'template_id': 1, 'template_name': 'Test 1', 'category_id': 1, 'template_type': 'typeA', 'language_code': 'en', 'client_id': None},
            {'template_id': 2, 'template_name': 'Test 2', 'category_id': 2, 'template_type': 'typeB', 'language_code': 'fr', 'client_id': 'client1'},
        ]
        self.mock_cursor.fetchall.return_value = mock_data

        # Convert list of dicts to list of MagicMock rows for dict(row)
        mock_rows = []
        if mock_data:
            # Create a mock that behaves like a row for dict(row)
            for d in mock_data:
                row_mock = MagicMock()
                row_mock.keys.return_value = d.keys()
                # __getitem__ allows dict(row_mock) to work
                row_mock.__getitem__.side_effect = lambda key, _d=d: _d[key]
                mock_rows.append(row_mock)
        self.mock_cursor.fetchall.return_value = mock_rows


        result = get_all_templates(conn=self.mock_conn)

        self.mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM Templates ORDER BY client_id, category_id, template_name, language_code",
            tuple()
        )
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['template_name'], 'Test 1')

    def test_get_all_templates_with_category_id_filter(self):
        """Test filtering by category_id."""
        category_to_filter = 1
        # fetchall should only return items matching the category
        mock_data = [
            {'template_id': 1, 'template_name': 'Doc Template', 'category_id': category_to_filter, 'template_type': 'typeA', 'language_code': 'en', 'client_id': None},
        ]
        mock_rows = []
        if mock_data:
            for d in mock_data:
                row_mock = MagicMock()
                row_mock.keys.return_value = d.keys()
                row_mock.__getitem__.side_effect = lambda key, _d=d: _d[key]
                mock_rows.append(row_mock)
        self.mock_cursor.fetchall.return_value = mock_rows

        result = get_all_templates(category_id_filter=category_to_filter, conn=self.mock_conn)

        expected_sql = "SELECT * FROM Templates WHERE category_id = ? ORDER BY client_id, category_id, template_name, language_code"
        self.mock_cursor.execute.assert_called_once_with(expected_sql, (category_to_filter,))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['category_id'], category_to_filter)

    def test_get_all_templates_with_template_type_filter_list(self):
        """Test filtering by a list of template_types."""
        types_to_filter = ['typeA', 'typeC']
        mock_data = [
            {'template_id': 1, 'template_name': 'Type A Template', 'category_id': 1, 'template_type': 'typeA', 'language_code': 'en', 'client_id': None},
            {'template_id': 3, 'template_name': 'Type C Template', 'category_id': 1, 'template_type': 'typeC', 'language_code': 'en', 'client_id': None},
        ]
        mock_rows = []
        if mock_data:
            for d in mock_data:
                row_mock = MagicMock()
                row_mock.keys.return_value = d.keys()
                row_mock.__getitem__.side_effect = lambda key, _d=d: _d[key]
                mock_rows.append(row_mock)
        self.mock_cursor.fetchall.return_value = mock_rows

        result = get_all_templates(template_type_filter_list=types_to_filter, conn=self.mock_conn)

        expected_sql = "SELECT * FROM Templates WHERE template_type IN (?,?) ORDER BY client_id, category_id, template_name, language_code"
        self.mock_cursor.execute.assert_called_once_with(expected_sql, tuple(types_to_filter))
        self.assertEqual(len(result), 2)
        self.assertTrue(all(t['template_type'] in types_to_filter for t in result))

    def test_get_all_templates_with_single_template_type_filter(self):
        """Test filtering by a single template_type when list is not provided."""
        type_to_filter = 'typeB'
        mock_data = [
            {'template_id': 2, 'template_name': 'Type B Template', 'category_id': 2, 'template_type': 'typeB', 'language_code': 'fr', 'client_id': 'client1'},
        ]
        mock_rows = []
        if mock_data:
            for d in mock_data:
                row_mock = MagicMock()
                row_mock.keys.return_value = d.keys()
                row_mock.__getitem__.side_effect = lambda key, _d=d: _d[key]
                mock_rows.append(row_mock)
        self.mock_cursor.fetchall.return_value = mock_rows

        result = get_all_templates(template_type_filter=type_to_filter, conn=self.mock_conn)

        expected_sql = "SELECT * FROM Templates WHERE template_type = ? ORDER BY client_id, category_id, template_name, language_code"
        self.mock_cursor.execute.assert_called_once_with(expected_sql, (type_to_filter,))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['template_type'], type_to_filter)

    def test_get_all_templates_type_list_takes_precedence(self):
        """Test template_type_filter_list takes precedence over template_type_filter."""
        list_types = ['typeA']
        single_type = 'typeB' # This should be ignored
        mock_data = [
            {'template_id': 1, 'template_name': 'Type A Template', 'category_id': 1, 'template_type': 'typeA', 'language_code': 'en', 'client_id': None},
        ]
        mock_rows = []
        if mock_data:
            for d in mock_data:
                row_mock = MagicMock()
                row_mock.keys.return_value = d.keys()
                row_mock.__getitem__.side_effect = lambda key, _d=d: _d[key]
                mock_rows.append(row_mock)
        self.mock_cursor.fetchall.return_value = mock_rows

        result = get_all_templates(template_type_filter_list=list_types, template_type_filter=single_type, conn=self.mock_conn)

        expected_sql = "SELECT * FROM Templates WHERE template_type IN (?) ORDER BY client_id, category_id, template_name, language_code"
        self.mock_cursor.execute.assert_called_once_with(expected_sql, tuple(list_types))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['template_type'], 'typeA')


    def test_get_all_templates_combination_of_filters(self):
        """Test combination of category_id_filter and template_type_filter_list."""
        category_to_filter = 1
        types_to_filter = ['typeA', 'typeC']
        lang_to_filter = 'en'

        mock_data = [
            {'template_id': 1, 'template_name': 'Combo Template', 'category_id': 1, 'template_type': 'typeA', 'language_code': 'en', 'client_id': None},
        ]
        mock_rows = []
        if mock_data:
            for d in mock_data:
                row_mock = MagicMock()
                row_mock.keys.return_value = d.keys()
                row_mock.__getitem__.side_effect = lambda key, _d=d: _d[key]
                mock_rows.append(row_mock)
        self.mock_cursor.fetchall.return_value = mock_rows

        result = get_all_templates(
            category_id_filter=category_to_filter,
            template_type_filter_list=types_to_filter,
            language_code_filter=lang_to_filter,
            conn=self.mock_conn
        )

        expected_sql = "SELECT * FROM Templates WHERE template_type IN (?,?) AND language_code = ? AND category_id = ? ORDER BY client_id, category_id, template_name, language_code"
        # Order of params matters for the tuple
        expected_params = tuple(types_to_filter + [lang_to_filter, category_to_filter])
        self.mock_cursor.execute.assert_called_once_with(expected_sql, expected_params)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['template_name'], 'Combo Template')

    def test_get_all_templates_empty_type_list(self):
        """Test that an empty template_type_filter_list is ignored."""
        # This should behave as if no type filter was applied, or use template_type_filter if provided
        # Current logic: if list is empty, it's ignored, and template_type_filter (if any) is used.

        # Scenario 1: Empty list, no single type filter
        self.mock_cursor.reset_mock()
        self.mock_cursor.fetchall.return_value = []
        get_all_templates(template_type_filter_list=[], conn=self.mock_conn)
        self.mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM Templates ORDER BY client_id, category_id, template_name, language_code", tuple())

        # Scenario 2: Empty list, but single type filter is present
        self.mock_cursor.reset_mock()
        self.mock_cursor.fetchall.return_value = []
        type_to_filter = "typeX"
        get_all_templates(template_type_filter_list=[], template_type_filter=type_to_filter, conn=self.mock_conn)
        expected_sql = "SELECT * FROM Templates WHERE template_type = ? ORDER BY client_id, category_id, template_name, language_code"
        self.mock_cursor.execute.assert_called_once_with(expected_sql, (type_to_filter,))


if __name__ == '__main__':
    unittest.main()
