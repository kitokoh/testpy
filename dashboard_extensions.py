# dashboard_extensions.py
"""
This module defines classes for managing extensions to the dashboard functionalities,
such as project templates.
"""

class ProjectTemplate:
    """
    Represents a project template, containing a name, description, and a list of predefined tasks.
    """
    def __init__(self, name, description, tasks):
        self.name = name
        self.description = description
        self.tasks = tasks # List of dictionaries, e.g., [{'name': 'Task 1', 'description': '...', 'priority': 1}, ...]

class ProjectTemplateManager:
    """
    Manages the available project templates, including loading default templates
    and providing methods to access them.
    """
    def __init__(self):
        self._templates = []
        self._load_default_templates()

    def _load_default_templates(self):
        # Template 1: Standard Factory Order
        sfo_tasks = [
            {'name': "Supplier Verification & Due Diligence", 'description': "Verify supplier credentials, certifications, and factory audit reports.", 'priority': 2}, # High priority
            {'name': "Product Specification Finalization", 'description': "Confirm all product specs, materials, and quality standards with supplier.", 'priority': 2},
            {'name': "Purchase Order (PO) Placement", 'description': "Issue formal PO to the supplier.", 'priority': 1}, # Medium
            {'name': "Production Kick-off & Monitoring", 'description': "Confirm production start and establish monitoring checkpoints.", 'priority': 1},
            {'name': "Pre-Shipment Quality Inspection (PSI)", 'description': "Arrange and conduct PSI. Review report.", 'priority': 2},
            {'name': "Logistics & Shipping Arrangement", 'description': "Book freight, confirm shipping documents (B/L, Packing List, Invoice).", 'priority': 1},
            {'name': "Customs Clearance (Import)", 'description': "Prepare and submit necessary documents for import customs clearance.", 'priority': 1},
            {'name': "Inland Transportation & Warehousing", 'description': "Arrange transportation from port to warehouse/client.", 'priority': 0}, # Low
            {'name': "Final Delivery & Goods Receipt", 'description': "Confirm goods received by client, obtain signed delivery note.", 'priority': 1},
            {'name': "Payment & Financial Reconciliation", 'description': "Process final payments and reconcile accounts.", 'priority': 1}
        ]
        self._templates.append(
            ProjectTemplate(
                name="Standard Factory Order (International Trade)",
                description="A standard template for sourcing and purchasing goods from an international factory.",
                tasks=sfo_tasks
            )
        )

        # Template 2: Simple Project
        simple_tasks = [
            {'name': "Project Initiation", 'description': "Define project scope and objectives.", 'priority': 1},
            {'name': "Planning Phase", 'description': "Develop project plan and schedule.", 'priority': 1},
            {'name': "Execution Phase", 'description': "Carry out project tasks.", 'priority': 1},
            {'name': "Review & Closure", 'description': "Review project outcomes and close.", 'priority': 0}
        ]
        self._templates.append(
            ProjectTemplate(
                name="Simple Generic Project",
                description="A basic template for simple projects.",
                tasks=simple_tasks
            )
        )

    def get_templates(self):
        return self._templates

    def get_template_by_name(self, name):
        for tpl in self._templates:
            if tpl.name == name:
                return tpl
        return None
