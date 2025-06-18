from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, validator
from fastapi import APIRouter

# Initialize API Router
router = APIRouter(
    prefix="/reports",
    tags=["Reports Management"],
    responses={404: {"description": "Not found"}},
)

# --- ReportConfigField Models ---

class ReportConfigFieldBase(BaseModel):
    field_name: str
    display_name: Optional[str] = None
    sort_order: int = 0  # Changed to non-optional with default as per typical usage
    sort_direction: Optional[str] = None # e.g., 'ASC', 'DESC'
    group_by_priority: int = 0 # Changed to non-optional with default

    @validator('sort_direction', always=True)
    def validate_sort_direction(cls, v):
        if v is not None and v.upper() not in ['ASC', 'DESC']:
            raise ValueError('sort_direction must be "ASC" or "DESC"')
        if v is not None:
            return v.upper()
        return v

class ReportConfigFieldCreate(ReportConfigFieldBase):
    pass

class ReportConfigField(ReportConfigFieldBase):
    report_config_field_id: int

    model_config = ConfigDict(from_attributes=True)


# --- ReportConfigFilter Models ---

class ReportConfigFilterBase(BaseModel):
    field_name: str
    operator: str  # e.g., '=', 'LIKE', 'BETWEEN', 'IN', '>', '<', '!='
    filter_value_1: Optional[str] = None
    filter_value_2: Optional[str] = None  # For 'BETWEEN' operator primarily
    logical_group: str = 'AND' # Changed to non-optional with default

    @validator('logical_group', always=True)
    def validate_logical_group(cls, v):
        if v.upper() not in ['AND', 'OR']:
            raise ValueError('logical_group must be "AND" or "OR"')
        return v.upper()

    @validator('filter_value_2', always=True)
    def validate_filter_value_2(cls, v, values):
        operator = values.get('operator', '').upper()
        if operator == 'BETWEEN' and v is None:
            raise ValueError('filter_value_2 is required for BETWEEN operator')
        if operator != 'BETWEEN' and v is not None:
            # Could raise error or just ignore/nullify filter_value_2
            # For now, let's be permissive, but a stricter validation might be:
            # raise ValueError('filter_value_2 should only be provided for BETWEEN operator')
            pass
        return v

class ReportConfigFilterCreate(ReportConfigFilterBase):
    pass

class ReportConfigFilter(ReportConfigFilterBase):
    report_config_filter_id: int

    model_config = ConfigDict(from_attributes=True)


# --- ReportConfiguration Models ---

class ReportConfigurationBase(BaseModel):
    report_name: str
    description: Optional[str] = None
    target_entity: str  # e.g., 'CompanyAssets', 'AssetAssignments', 'Clients'
    output_format: str  # e.g., 'json', 'csv_summary', 'pdf_detail'

    @validator('output_format')
    def validate_output_format(cls, v):
        # Example validation, expand as needed
        allowed_formats = ['JSON', 'CSV_SUMMARY', 'PDF_DETAIL', 'CSV', 'PDF']
        if v.upper() not in allowed_formats:
            raise ValueError(f"output_format must be one of {allowed_formats}")
        return v.upper()


class ReportConfigurationCreate(ReportConfigurationBase):
    fields: List[ReportConfigFieldCreate]
    filters: List[ReportConfigFilterCreate]


class ReportConfigurationUpdate(BaseModel):
    report_name: Optional[str] = None
    description: Optional[str] = None
    target_entity: Optional[str] = None
    output_format: Optional[str] = None
    fields: Optional[List[ReportConfigFieldCreate]] = None  # If provided, replaces all existing fields
    filters: Optional[List[ReportConfigFilterCreate]] = None # If provided, replaces all existing filters

    @validator('output_format', always=True)
    def validate_output_format_update(cls, v):
        if v is not None:
            allowed_formats = ['JSON', 'CSV_SUMMARY', 'PDF_DETAIL', 'CSV', 'PDF']
            if v.upper() not in allowed_formats:
                raise ValueError(f"output_format must be one of {allowed_formats}")
            return v.upper()
        return v


class ReportConfiguration(ReportConfigurationBase):
    report_config_id: str # UUID
    created_by_user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_system_report: bool = False
    fields: List[ReportConfigField]
    filters: List[ReportConfigFilter]

    model_config = ConfigDict(from_attributes=True)


class ReportConfigurationMinimal(ReportConfigurationBase): # For list responses
    report_config_id: str # UUID
    created_by_user_id: Optional[str] = None
    # created_at: datetime # Typically included in list views
    # updated_at: datetime # Typically included in list views
    is_system_report: bool = False

    model_config = ConfigDict(from_attributes=True)


# --- Report Configuration API Endpoints ---

from ..db.cruds.report_configurations_crud import report_configurations_crud
from ..models.user_models import User as UserModelFromApi # Ensure consistency with other API files
from .auth import get_current_active_user
from fastapi import HTTPException, status, Response
import sqlite3 # For catching specific DB errors like IntegrityError

@router.post("/configurations/", response_model=ReportConfiguration, status_code=status.HTTP_201_CREATED)
async def create_report_configuration(
    report_in: ReportConfigurationCreate,
    current_user: UserModelFromApi = Depends(get_current_active_user)
):
    """
    Create a new report configuration.
    - `report_name`: Unique name for the report.
    - `description`: Optional description.
    - `target_entity`: The main data entity for the report (e.g., 'CompanyAssets').
    - `output_format`: Desired output format (e.g., 'JSON', 'CSV_SUMMARY').
    - `fields`: List of fields to include in the report, with display settings.
    - `filters`: List of filters to apply to the report data.
    """
    config_data_dict = report_in.model_dump(exclude={"fields", "filters"})
    config_data_dict["created_by_user_id"] = current_user.user_id

    fields_data_list = [field.model_dump() for field in report_in.fields]
    filters_data_list = [f.model_dump() for f in report_in.filters]

    try:
        report_config_id = report_configurations_crud.add_report_configuration(
            config_data=config_data_dict,
            fields_data=fields_data_list,
            filters_data=filters_data_list
        )
        if not report_config_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create report configuration due to invalid input or pre-check failure.")
    except sqlite3.IntegrityError as e:
        if "reportconfigurations.report_name" in str(e).lower() and "unique constraint failed" in str(e).lower() :
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"A report configuration with the name '{report_in.report_name}' already exists.")
        # logger.error(f"Database integrity error creating report configuration: {e}", exc_info=True) # Add logger
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database integrity error during creation.")
    except Exception as e:
        # logger.error(f"Unexpected error creating report configuration: {e}", exc_info=True) # Add logger
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

    created_config = report_configurations_crud.get_report_configuration_by_id(report_config_id)
    if not created_config:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Report configuration created but could not be retrieved.")

    return ReportConfiguration.model_validate(created_config)


@router.get("/configurations/", response_model=List[ReportConfigurationMinimal])
async def list_report_configurations(
    include_system_reports: bool = True,
    current_user: UserModelFromApi = Depends(get_current_active_user)
):
    """
    List report configurations.
    Shows system reports and/or reports created by the current user.
    - `include_system_reports`: Set to false to hide system-defined reports if desired by user.
    """
    user_id_to_filter = current_user.user_id
    # Example: Basic role check to allow admins to see all non-system reports
    # if current_user.role in ["admin", "super_admin"]: # Adapt role names as per your User model/auth system
    #    user_id_to_filter = None # CRUD method should interpret None user_id as "all non-system" when include_system_reports is False

    configs_db = report_configurations_crud.get_all_report_configurations(
        user_id=user_id_to_filter,
        include_system_reports=include_system_reports
    )
    return [ReportConfigurationMinimal.model_validate(config) for config in configs_db]


@router.get("/configurations/{config_id}", response_model=ReportConfiguration)
async def get_report_configuration(
    config_id: str,
    current_user: UserModelFromApi = Depends(get_current_active_user)
):
    """
    Get a specific report configuration by its ID.
    Users can access system reports or their own created reports.
    - `config_id`: UUID of the report configuration.
    """
    config_db = report_configurations_crud.get_report_configuration_by_id(config_id)
    if not config_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report configuration not found.")

    is_system_report = config_db.get("is_system_report", False)
    created_by = config_db.get("created_by_user_id")

    # Ownership/Access Check
    # Allow if system report OR user is creator OR user is admin (example)
    is_authorized = is_system_report or (created_by == current_user.user_id)
    # if not is_authorized and current_user.role in ["admin", "super_admin"]: # Example admin override
    #    is_authorized = True

    if not is_authorized:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this report configuration.")

    return ReportConfiguration.model_validate(config_db)


@router.put("/configurations/{config_id}", response_model=ReportConfiguration)
async def update_report_configuration(
    config_id: str,
    report_update_in: ReportConfigurationUpdate,
    current_user: UserModelFromApi = Depends(get_current_active_user)
):
    """
    Update an existing report configuration.
    Only non-system reports created by the user can be updated (unless user is admin).
    - `config_id`: UUID of the report configuration to update.
    """
    existing_config = report_configurations_crud.get_report_configuration_by_id(config_id)
    if not existing_config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report configuration not found.")

    if existing_config.get("is_system_report"):
        # Potentially allow admins to update system reports if needed, with specific logic
        # if current_user.role not in ["super_admin"]: # Example role check
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="System reports cannot be modified by this action.")

    if existing_config.get("created_by_user_id") != current_user.user_id:
        # if current_user.role not in ["admin", "super_admin"]: # Example admin override
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this report configuration.")

    config_data_dict = report_update_in.model_dump(exclude={"fields", "filters"}, exclude_unset=True)
    fields_data_list = [field.model_dump() for field in report_update_in.fields] if report_update_in.fields is not None else None
    filters_data_list = [f.model_dump() for f in report_update_in.filters] if report_update_in.filters is not None else None

    if not config_data_dict and fields_data_list is None and filters_data_list is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided.")

    try:
        updated = report_configurations_crud.update_report_configuration(
            report_config_id=config_id,
            config_data=config_data_dict if config_data_dict else None,
            fields_data=fields_data_list,
            filters_data=filters_data_list
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update report configuration.")
    except sqlite3.IntegrityError as e:
        if "reportconfigurations.report_name" in str(e).lower() and "unique constraint failed" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"A report configuration with the name '{report_update_in.report_name}' already exists.")
        # logger.error(f"Database integrity error updating report configuration: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database integrity error during update.")
    except Exception as e:
        # logger.error(f"Unexpected error updating report configuration: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during update.")

    updated_config = report_configurations_crud.get_report_configuration_by_id(config_id)
    if not updated_config:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report configuration updated but could not be retrieved.")

    return ReportConfiguration.model_validate(updated_config)


@router.delete("/configurations/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report_configuration(
    config_id: str,
    current_user: UserModelFromApi = Depends(get_current_active_user)
):
    """
    Delete a report configuration.
    Only non-system reports created by the user can be deleted (unless user is admin).
    - `config_id`: UUID of the report configuration to delete.
    """
    existing_config = report_configurations_crud.get_report_configuration_by_id(config_id)
    if not existing_config:
        # Return 204 if already deleted or never existed, for idempotency.
        # Alternatively, raise 404 if strict "must exist to be deleted" is required.
        return Response(status_code=status.HTTP_204_NO_CONTENT)


    if existing_config.get("is_system_report"):
        # if current_user.role not in ["super_admin"]: # Example role check
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="System reports cannot be deleted.")

    if existing_config.get("created_by_user_id") != current_user.user_id:
        # if current_user.role not in ["admin", "super_admin"]: # Example admin override
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this report configuration.")

    deleted = report_configurations_crud.delete_report_configuration(config_id)
    if not deleted:
        # This implies it existed moments ago but couldn't be deleted now.
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete report configuration.")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


if __name__ == "__main__": # pragma: no cover
    # Basic validation tests
    print("Validating ReportConfigField models...")

# --- Report Execution Models & Endpoint ---

from typing import Any # For ReportResults data_rows
from ..db.database_manager import get_db_connection # For direct DB access in report execution

class ReportResults(BaseModel):
    report_config: ReportConfiguration
    column_headers: List[str]
    data_rows: List[Dict[str, Any]]
    total_records: int
    limit: int
    offset: int

# Whitelist of allowed target entities and their actual table names
# This is crucial for security to prevent arbitrary table access.
# Expand this map as more entities become reportable.
ALLOWED_TARGET_ENTITIES_MAP = {
    "CompanyAssets": "CompanyAssets",
    "AssetAssignments": "AssetAssignments",
    # "Clients": "Clients", # Example for future
    # "Projects": "Projects", # Example for future
}


@router.get("/configurations/{config_id}/execute", response_model=ReportResults)
async def execute_report_configuration(
    config_id: str,
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    current_user: UserModelFromApi = Depends(get_current_active_user)
):
    """
    Execute a stored report configuration and retrieve data.
    - `config_id`: UUID of the report configuration to execute.
    - `limit`: Pagination limit for the data rows.
    - `offset`: Pagination offset for the data rows.
    """
    # 1. Fetch and authorize report configuration
    config_db = report_configurations_crud.get_report_configuration_by_id(config_id)
    if not config_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report configuration not found.")

    report_config_obj = ReportConfiguration.model_validate(config_db)

    is_system_report = report_config_obj.is_system_report
    created_by = report_config_obj.created_by_user_id

    is_authorized = is_system_report or (created_by == current_user.user_id)
    # Example admin override (adapt role names as needed)
    # if not is_authorized and current_user.role in ["admin", "super_admin"]:
    #     is_authorized = True

    if not is_authorized:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to execute this report configuration.")

    # 2. Validate target_entity
    target_table_name = ALLOWED_TARGET_ENTITIES_MAP.get(report_config_obj.target_entity)
    if not target_table_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid target entity '{report_config_obj.target_entity}' in report configuration.")

    # 3. Dynamically construct SQL query
    sql_select_fields = []
    column_headers = []

    # Ensure fields are ordered by their defined sort_order for header consistency if needed,
    # though SQL SELECT order doesn't strictly guarantee final output order without ORDER BY.
    # ReportConfigFields from DB are already sorted by sort_order, report_config_field_id.

    for field_config in report_config_obj.fields:
        # Basic sanitization/validation for field_name (e.g., ensure it's a valid identifier)
        # For now, trusting stored configuration. In a system where users define field_names freely,
        # this would need to be checked against a list of allowed fields for the target_entity.
        if not field_config.field_name.replace('_','').isalnum(): # Basic check for valid characters
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid field name '{field_config.field_name}' in report configuration.")
        sql_select_fields.append(f'"{field_config.field_name}"') # Quote to handle spaces or keywords, if any were allowed
        column_headers.append(field_config.display_name or field_config.field_name)

    if not sql_select_fields:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields configured for this report.")

    select_clause = f"SELECT {', '.join(sql_select_fields)} FROM \"{target_table_name}\"" # Quote table name

    # WHERE clause
    where_conditions = []
    query_params = []

    # Sort filters to process them in a predictable order, though logical_group handles actual combination.
    # Assuming filters from DB are already ordered if needed, or order doesn't impact AND/OR logic here.
    for i, filter_config in enumerate(report_config_obj.filters):
        if not filter_config.field_name.replace('_','').isalnum():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid filter field name '{filter_config.field_name}'.")

        condition_str = ""
        op = filter_config.operator.upper()

        # Whitelist operators and construct condition
        if op == "=": condition_str = f'"{filter_config.field_name}" = ?'
        elif op == "!=": condition_str = f'"{filter_config.field_name}" != ?'
        elif op == ">": condition_str = f'"{filter_config.field_name}" > ?'
        elif op == "<": condition_str = f'"{filter_config.field_name}" < ?'
        elif op == ">=": condition_str = f'"{filter_config.field_name}" >= ?'
        elif op == "<=": condition_str = f'"{filter_config.field_name}" <= ?'
        elif op == "LIKE":
            condition_str = f'"{filter_config.field_name}" LIKE ?'
            # Users should provide wildcards in filter_value_1 if needed, e.g., "%value%"
        elif op == "NOT LIKE":
             condition_str = f'"{filter_config.field_name}" NOT LIKE ?'
        elif op == "IN":
            # For IN, filter_value_1 should be a comma-separated list.
            # This requires special handling for parameterization.
            placeholders = ','.join(['?'] * len(filter_config.filter_value_1.split(',')))
            condition_str = f'"{filter_config.field_name}" IN ({placeholders})'
            query_params.extend(filter_config.filter_value_1.split(','))
        elif op == "NOT IN":
            placeholders = ','.join(['?'] * len(filter_config.filter_value_1.split(',')))
            condition_str = f'"{filter_config.field_name}" NOT IN ({placeholders})'
            query_params.extend(filter_config.filter_value_1.split(','))
        elif op == "BETWEEN":
            condition_str = f'"{filter_config.field_name}" BETWEEN ? AND ?'
            query_params.append(filter_config.filter_value_1)
            if filter_config.filter_value_2 is None:
                 raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Operator BETWEEN requires filter_value_2 for field '{filter_config.field_name}'.")
            query_params.append(filter_config.filter_value_2)
        elif op == "IS NULL": condition_str = f'"{filter_config.field_name}" IS NULL'
        elif op == "IS NOT NULL": condition_str = f'"{filter_config.field_name}" IS NOT NULL'
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported filter operator '{op}'.")

        if condition_str:
            if op not in ["IN", "NOT IN", "BETWEEN", "IS NULL", "IS NOT NULL"]: # These already added their params or don't need one
                query_params.append(filter_config.filter_value_1)

            if where_conditions: # Add logical operator if not the first condition
                # Note: this simple sequential AND/OR might not be powerful enough for complex grouped logic.
                # A more advanced system would parse a filter tree.
                where_conditions.append(filter_config.logical_group.upper())
            where_conditions.append(condition_str)

    where_clause = ""
    if where_conditions:
        where_clause = "WHERE " + " ".join(where_conditions) # Simple sequential joining

    # ORDER BY clause
    order_by_parts = []
    # Filter fields that have sort_order > 0 and sort them by sort_order
    sortable_fields = sorted([f for f in report_config_obj.fields if f.sort_order > 0], key=lambda x: x.sort_order)
    for field_config in sortable_fields:
        if not field_config.field_name.replace('_','').isalnum():
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid sort field name '{field_config.field_name}'.")
        direction = field_config.sort_direction.upper() if field_config.sort_direction and field_config.sort_direction.upper() in ["ASC", "DESC"] else "ASC"
        order_by_parts.append(f'"{field_config.field_name}" {direction}')

    order_by_clause = ""
    if order_by_parts:
        order_by_clause = "ORDER BY " + ", ".join(order_by_parts)

    # GROUP BY clause - Not implemented in this phase
    # group_by_clause = ""
    # grouped_fields = sorted([f for f in report_config_obj.fields if f.group_by_priority > 0], key=lambda x: x.group_by_priority)
    # if grouped_fields:
    #     group_by_parts = [f'"{f.field_name}"' for f in grouped_fields]
    #     group_by_clause = "GROUP BY " + ", ".join(group_by_parts)


    # LIMIT/OFFSET clauses
    limit_clause = f"LIMIT {int(limit)}" # Ensure limit is int
    offset_clause = f"OFFSET {int(offset)}" if offset > 0 else ""

    # Construct final queries
    data_query_sql = f"{select_clause} {where_clause} {order_by_clause} {limit_clause} {offset_clause}".strip()
    count_query_sql = f"SELECT COUNT(*) as total_records FROM \"{target_table_name}\" {where_clause}".strip()

    # 4. Execute queries
    data_rows = []
    total_records = 0

    db_conn = None
    try:
        db_conn = get_db_connection() # Using the project's db_path from config
        db_conn.row_factory = sqlite3.Row # Important for dict-like access
        cursor = db_conn.cursor()

        # Execute count query
        cursor.execute(count_query_sql, tuple(query_params)) # Params are for WHERE clause
        count_result = cursor.fetchone()
        if count_result:
            total_records = count_result['total_records']

        # Execute data query
        cursor.execute(data_query_sql, tuple(query_params)) # Params are for WHERE clause primarily
        fetched_rows = cursor.fetchall()
        data_rows = [dict(row) for row in fetched_rows]

    except sqlite3.Error as e:
        # logger.error(f"Error executing report query for config '{config_id}': {e}", exc_info=True)
        # logger.debug(f"Failed data query: {data_query_sql} with params: {query_params}")
        # logger.debug(f"Failed count query: {count_query_sql} with params: {query_params}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error executing report query: {str(e)}")
    finally:
        if db_conn:
            db_conn.close()

    # 5. Format and return results
    return ReportResults(
        report_config=report_config_obj,
        column_headers=column_headers,
        data_rows=data_rows,
        total_records=total_records,
        limit=limit,
        offset=offset
    )


if __name__ == "__main__": # pragma: no cover
    # Basic validation tests
    print("Validating ReportConfigField models...")
    field_create = ReportConfigFieldCreate(field_name="asset_name", display_name="Asset Name", sort_order=1, sort_direction="ASC")
    print(f"Field Create valid: {field_create}")
    field_resp = ReportConfigField(report_config_field_id=1, **field_create.model_dump())
    print(f"Field Response valid: {field_resp}")
    try:
        ReportConfigFieldCreate(field_name="status", sort_direction="INVALID")
    except ValueError as e:
        print(f"Field validation caught error (expected): {e}")

    print("\nValidating ReportConfigFilter models...")
    filter_create = ReportConfigFilterCreate(field_name="status", operator="=", filter_value_1="Active")
    print(f"Filter Create valid: {filter_create}")
    filter_resp = ReportConfigFilter(report_config_filter_id=1, **filter_create.model_dump())
    print(f"Filter Response valid: {filter_resp}")
    try:
        ReportConfigFilterCreate(field_name="date", operator="BETWEEN", filter_value_1="2023-01-01") # Missing filter_value_2
    except ValueError as e:
        print(f"Filter validation caught error for BETWEEN (expected): {e}")

    print("\nValidating ReportConfiguration models...")
    config_create = ReportConfigurationCreate(
        report_name="Active Assets Report",
        target_entity="CompanyAssets",
        output_format="CSV",
        fields=[field_create],
        filters=[filter_create]
    )
    print(f"Config Create valid: {config_create.report_name}")

    config_resp = ReportConfiguration(
        report_config_id=str(uuid.uuid4()),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        is_system_report=False,
        fields=[field_resp],
        filters=[filter_resp],
        **config_create.model_dump(exclude={"fields", "filters"}) # Exclude lists that have different types
    )
    print(f"Config Response valid: {config_resp.report_config_id}")

    config_minimal = ReportConfigurationMinimal(
        report_config_id=str(uuid.uuid4()),
        report_name="Minimal Asset List",
        target_entity="CompanyAssets",
        output_format="JSON",
        is_system_report=True
    )
    print(f"Config Minimal valid: {config_minimal.report_name}")

    print("\nAll basic model validations in reports.py seem OK.")

```
