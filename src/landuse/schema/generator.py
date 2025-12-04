"""Code and documentation generators for schema management."""

import re
from datetime import datetime
from typing import Dict, List, Optional, Set

from .models import SchemaDefinition, TableDefinition, ViewDefinition


class SchemaDocGenerator:
    """Generate documentation from schema definitions."""

    def generate_markdown(self, schema: SchemaDefinition) -> str:
        """Generate Markdown documentation.

        Args:
            schema: Schema definition

        Returns:
            Markdown formatted documentation
        """
        lines = [
            f"# Schema Documentation v{schema.version}",
            "",
            f"**Generated:** {datetime.utcnow().isoformat()}",
            f"**Description:** {schema.description}",
            f"**Author:** {schema.author}",
            f"**Backward Compatible:** {'Yes' if schema.backward_compatible else 'No'}",
            "",
            "## Tables",
            ""
        ]

        # Document tables
        for table_name, table_def in sorted(schema.tables.items()):
            lines.extend(self._document_table_markdown(table_name, table_def))
            lines.append("")

        # Document views
        if schema.views:
            lines.extend([
                "## Views",
                ""
            ])
            for view_name, view_def in sorted(schema.views.items()):
                lines.extend(self._document_view_markdown(view_name, view_def))
                lines.append("")

        return "\n".join(lines)

    def _document_table_markdown(
        self,
        table_name: str,
        table_def: TableDefinition
    ) -> List[str]:
        """Generate Markdown documentation for a table.

        Args:
            table_name: Table name
            table_def: Table definition

        Returns:
            List of documentation lines
        """
        lines = [
            f"### {table_name}",
            ""
        ]

        if table_def.description:
            lines.extend([
                table_def.description,
                ""
            ])

        # Extract columns from DDL
        columns = self._extract_columns_from_ddl(table_def.ddl)
        if columns:
            lines.extend([
                "| Column | Type | Constraints | Description |",
                "|--------|------|------------|-------------|"
            ])
            for col in columns:
                lines.append(
                    f"| {col['name']} | {col['type']} | "
                    f"{col['constraints']} | {col.get('description', '')} |"
                )
            lines.append("")

        # Document indexes
        if table_def.indexes:
            lines.extend([
                "**Indexes:**",
                ""
            ])
            for index in table_def.indexes:
                if isinstance(index, dict) and 'ddl' in index:
                    lines.append(f"- {index['ddl']}")
                else:
                    lines.append(f"- {index}")
            lines.append("")

        return lines

    def _document_view_markdown(
        self,
        view_name: str,
        view_def: ViewDefinition
    ) -> List[str]:
        """Generate Markdown documentation for a view.

        Args:
            view_name: View name
            view_def: View definition

        Returns:
            List of documentation lines
        """
        lines = [
            f"### {view_name}",
            ""
        ]

        if view_def.description:
            lines.extend([
                view_def.description,
                ""
            ])

        if view_def.materialized:
            lines.append("**Type:** Materialized View")
            lines.append("")

        # Show simplified DDL
        simplified_ddl = self._simplify_view_ddl(view_def.ddl)
        lines.extend([
            "**Definition:**",
            "```sql",
            simplified_ddl,
            "```"
        ])

        return lines

    def generate_er_diagram(self, schema: SchemaDefinition) -> str:
        """Generate ER diagram in Mermaid format.

        Args:
            schema: Schema definition

        Returns:
            Mermaid ER diagram
        """
        lines = [
            "```mermaid",
            "erDiagram"
        ]

        # Extract relationships from foreign keys
        relationships = self._extract_relationships(schema)

        # Add entities (tables)
        for table_name in sorted(schema.tables.keys()):
            # Extract primary key
            pk = self._extract_primary_key(schema.tables[table_name].ddl)
            if pk:
                lines.append(f"    {table_name} {{")
                lines.append(f"        {pk} PK")
                lines.append("    }")

        # Add relationships
        for rel in relationships:
            lines.append(f"    {rel['from']} ||--o{{ {rel['to']} : \"{rel['label']}\"")

        lines.append("```")
        return "\n".join(lines)

    def generate_sql_ddl(self, schema: SchemaDefinition) -> str:
        """Generate complete SQL DDL script.

        Args:
            schema: Schema definition

        Returns:
            Complete SQL DDL
        """
        lines = [
            f"-- Schema DDL v{schema.version}",
            f"-- Generated: {datetime.utcnow().isoformat()}",
            f"-- Description: {schema.description}",
            "",
            "-- Drop existing objects (careful!)",
            "-- Uncomment to use:",
            ""
        ]

        # Generate DROP statements (commented out for safety)
        for view_name in reversed(list(schema.views.keys())):
            lines.append(f"-- DROP VIEW IF EXISTS {view_name};")

        for table_name in reversed(list(schema.tables.keys())):
            lines.append(f"-- DROP TABLE IF EXISTS {table_name};")

        lines.extend([
            "",
            "-- Create tables",
            ""
        ])

        # Create tables in dependency order
        ordered_tables = self._order_tables_by_dependencies(schema)
        for table_name in ordered_tables:
            table_def = schema.tables[table_name]
            lines.extend([
                f"-- Table: {table_name}",
                table_def.ddl.strip(),
                ""
            ])

            # Add indexes
            for index in table_def.indexes:
                if isinstance(index, dict) and 'ddl' in index:
                    lines.append(index['ddl'])
                else:
                    lines.append(str(index))
            lines.append("")

        # Create views
        if schema.views:
            lines.extend([
                "-- Create views",
                ""
            ])
            for view_name, view_def in schema.views.items():
                lines.extend([
                    f"-- View: {view_name}",
                    view_def.ddl.strip(),
                    ""
                ])

        return "\n".join(lines)

    def generate_prompt_format(self, schema: SchemaDefinition) -> str:
        """Generate schema documentation for LLM prompts.

        Args:
            schema: Schema definition

        Returns:
            Formatted schema for prompts
        """
        lines = [
            "DATABASE SCHEMA:",
            ""
        ]

        # Add tables with simplified structure
        for table_name, table_def in sorted(schema.tables.items()):
            columns = self._extract_columns_from_ddl(table_def.ddl)
            column_list = ", ".join([
                f"{col['name']} {col['type']}" for col in columns
            ])
            lines.append(f"Table: {table_name} ({column_list})")

        lines.append("")

        # Add views
        if schema.views:
            lines.append("VIEWS:")
            for view_name, view_def in sorted(schema.views.items()):
                desc = view_def.description or "View"
                lines.append(f"- {view_name}: {desc}")

        return "\n".join(lines)

    def _extract_columns_from_ddl(self, ddl: str) -> List[Dict]:
        """Extract column information from DDL.

        Args:
            ddl: CREATE TABLE DDL

        Returns:
            List of column dictionaries
        """
        columns = []

        # Remove CREATE TABLE and parentheses
        table_body = re.search(r'CREATE TABLE.*?\((.*)\)', ddl, re.DOTALL | re.IGNORECASE)
        if not table_body:
            return columns

        content = table_body.group(1)

        # Split by commas (but not within parentheses)
        lines = self._split_sql_lines(content)

        for line in lines:
            line = line.strip()

            # Skip constraints and keys
            if any(keyword in line.upper() for keyword in [
                'PRIMARY KEY', 'FOREIGN KEY', 'UNIQUE', 'CHECK', 'INDEX'
            ]):
                continue

            # Parse column definition
            match = re.match(r'(\w+)\s+([^\s,]+)(.*)$', line)
            if match:
                col_name = match.group(1)
                col_type = match.group(2)
                col_rest = match.group(3) or ''

                constraints = []
                if 'PRIMARY KEY' in col_rest.upper():
                    constraints.append('PK')
                if 'NOT NULL' in col_rest.upper():
                    constraints.append('NOT NULL')
                if 'UNIQUE' in col_rest.upper():
                    constraints.append('UNIQUE')
                if 'DEFAULT' in col_rest.upper():
                    constraints.append('DEFAULT')

                columns.append({
                    'name': col_name,
                    'type': col_type,
                    'constraints': ' '.join(constraints)
                })

        return columns

    def _split_sql_lines(self, sql: str) -> List[str]:
        """Split SQL by commas, respecting parentheses.

        Args:
            sql: SQL string

        Returns:
            List of SQL lines
        """
        lines = []
        current = []
        paren_depth = 0

        for char in sql:
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
            elif char == ',' and paren_depth == 0:
                lines.append(''.join(current))
                current = []
                continue

            current.append(char)

        if current:
            lines.append(''.join(current))

        return lines

    def _extract_relationships(self, schema: SchemaDefinition) -> List[Dict]:
        """Extract foreign key relationships.

        Args:
            schema: Schema definition

        Returns:
            List of relationship dictionaries
        """
        relationships = []

        for table_name, table_def in schema.tables.items():
            # Find foreign key references
            fk_pattern = r'FOREIGN\s+KEY\s*\((\w+)\)\s*REFERENCES\s+(\w+)'
            matches = re.finditer(fk_pattern, table_def.ddl, re.IGNORECASE)

            for match in matches:
                fk_column = match.group(1)
                ref_table = match.group(2)
                relationships.append({
                    'from': ref_table,
                    'to': table_name,
                    'label': fk_column
                })

        return relationships

    def _extract_primary_key(self, ddl: str) -> Optional[str]:
        """Extract primary key column from DDL.

        Args:
            ddl: Table DDL

        Returns:
            Primary key column name
        """
        # Try column-level PK
        match = re.search(r'(\w+)\s+.*PRIMARY\s+KEY', ddl, re.IGNORECASE)
        if match:
            return match.group(1)

        # Try table-level PK
        match = re.search(r'PRIMARY\s+KEY\s*\((\w+)\)', ddl, re.IGNORECASE)
        if match:
            return match.group(1)

        return None

    def _simplify_view_ddl(self, ddl: str) -> str:
        """Simplify view DDL for documentation.

        Args:
            ddl: View DDL

        Returns:
            Simplified DDL
        """
        # Remove excessive whitespace
        ddl = re.sub(r'\s+', ' ', ddl)

        # Format for readability
        ddl = ddl.replace(' SELECT ', '\nSELECT ')
        ddl = ddl.replace(' FROM ', '\nFROM ')
        ddl = ddl.replace(' WHERE ', '\nWHERE ')
        ddl = ddl.replace(' GROUP BY ', '\nGROUP BY ')
        ddl = ddl.replace(' ORDER BY ', '\nORDER BY ')

        return ddl

    def _order_tables_by_dependencies(self, schema: SchemaDefinition) -> List[str]:
        """Order tables by foreign key dependencies.

        Args:
            schema: Schema definition

        Returns:
            List of table names in dependency order
        """
        # Build dependency graph
        dependencies: Dict[str, Set[str]] = {
            table: set() for table in schema.tables
        }

        for table_name, table_def in schema.tables.items():
            # Find tables this table depends on
            fk_pattern = r'REFERENCES\s+(\w+)'
            matches = re.finditer(fk_pattern, table_def.ddl, re.IGNORECASE)
            for match in matches:
                ref_table = match.group(1).lower()
                if ref_table in schema.tables:
                    dependencies[table_name].add(ref_table)

        # Topological sort
        ordered = []
        visited = set()

        def visit(table):
            if table in visited:
                return
            visited.add(table)

            # Visit dependencies first
            for dep in dependencies.get(table, []):
                visit(dep)

            ordered.append(table)

        for table in schema.tables:
            visit(table)

        return ordered


class ModelGenerator:
    """Generate Pydantic models from schema definitions."""

    def generate_from_schema(self, schema: SchemaDefinition) -> str:
        """Generate Pydantic models from schema.

        Args:
            schema: Schema definition

        Returns:
            Python code with Pydantic models
        """
        lines = [
            '"""Auto-generated Pydantic models from schema."""',
            "",
            "from datetime import datetime",
            "from decimal import Decimal",
            "from typing import Optional",
            "",
            "from pydantic import BaseModel, Field",
            "",
            f"# Generated from schema v{schema.version}",
            f"# Generated at: {datetime.utcnow().isoformat()}",
            "",
            ""
        ]

        # Generate model for each table
        for table_name, table_def in sorted(schema.tables.items()):
            model_lines = self._generate_table_model(table_name, table_def)
            lines.extend(model_lines)
            lines.append("")

        return "\n".join(lines)

    def _generate_table_model(
        self,
        table_name: str,
        table_def: TableDefinition
    ) -> List[str]:
        """Generate Pydantic model for a table.

        Args:
            table_name: Table name
            table_def: Table definition

        Returns:
            List of code lines
        """
        # Convert table name to class name
        class_name = ''.join(word.capitalize() for word in table_name.split('_'))

        lines = [
            f"class {class_name}(BaseModel):",
            f'    """Model for {table_name} table."""',
            ""
        ]

        # Extract columns from DDL
        columns = self._extract_columns_for_model(table_def.ddl)

        if not columns:
            lines.append("    pass")
        else:
            for col in columns:
                field_line = self._generate_field_line(col)
                lines.append(field_line)

        lines.extend([
            "",
            "    class Config:",
            '        """Pydantic configuration."""',
            "",
            f'        table_name = "{table_name}"',
            "        validate_assignment = True",
            "        use_enum_values = True"
        ])

        return lines

    def _extract_columns_for_model(self, ddl: str) -> List[Dict]:
        """Extract column information for model generation.

        Args:
            ddl: Table DDL

        Returns:
            List of column information
        """
        columns = []

        # Remove CREATE TABLE and parentheses
        table_body = re.search(r'CREATE TABLE.*?\((.*)\)', ddl, re.DOTALL | re.IGNORECASE)
        if not table_body:
            return columns

        content = table_body.group(1)
        lines = self._split_sql_lines(content)

        for line in lines:
            line = line.strip()

            # Skip constraints
            if any(keyword in line.upper() for keyword in [
                'PRIMARY KEY', 'FOREIGN KEY', 'UNIQUE', 'CHECK', 'INDEX'
            ]):
                continue

            # Parse column
            match = re.match(r'(\w+)\s+([^\s,]+)(.*)$', line)
            if match:
                col_name = match.group(1)
                col_type = match.group(2).upper()
                col_rest = (match.group(3) or '').upper()

                # Determine Python type
                python_type = self._sql_type_to_python(col_type)

                # Check if nullable
                nullable = 'NOT NULL' not in col_rest

                # Check for default
                default = None
                default_match = re.search(r'DEFAULT\s+(\S+)', col_rest)
                if default_match:
                    default = default_match.group(1)

                columns.append({
                    'name': col_name,
                    'type': python_type,
                    'nullable': nullable,
                    'default': default
                })

        return columns

    def _sql_type_to_python(self, sql_type: str) -> str:
        """Convert SQL type to Python type.

        Args:
            sql_type: SQL data type

        Returns:
            Python type string
        """
        type_mapping = {
            'INTEGER': 'int',
            'BIGINT': 'int',
            'SMALLINT': 'int',
            'DECIMAL': 'Decimal',
            'NUMERIC': 'Decimal',
            'FLOAT': 'float',
            'DOUBLE': 'float',
            'VARCHAR': 'str',
            'TEXT': 'str',
            'CHAR': 'str',
            'DATE': 'datetime',
            'TIMESTAMP': 'datetime',
            'BOOLEAN': 'bool',
            'BOOL': 'bool'
        }

        # Remove size specifications
        base_type = re.sub(r'\(.*?\)', '', sql_type).upper()

        return type_mapping.get(base_type, 'str')

    def _generate_field_line(self, col: Dict) -> str:
        """Generate Pydantic field line.

        Args:
            col: Column information

        Returns:
            Field definition line
        """
        field_name = col['name']
        field_type = col['type']

        if col['nullable']:
            field_type = f"Optional[{field_type}]"

        if col['default'] is not None:
            if col['default'] == 'CURRENT_TIMESTAMP':
                field_def = f"Field(default_factory=datetime.utcnow)"
            elif col['default'] in ('NULL', 'null'):
                field_def = "Field(default=None)"
            else:
                field_def = f"Field(default={col['default']})"
        elif col['nullable']:
            field_def = "Field(default=None)"
        else:
            field_def = "Field(...)"

        return f"    {field_name}: {field_type} = {field_def}"

    def _split_sql_lines(self, sql: str) -> List[str]:
        """Split SQL by commas, respecting parentheses.

        Args:
            sql: SQL string

        Returns:
            List of SQL lines
        """
        lines = []
        current = []
        paren_depth = 0

        for char in sql:
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
            elif char == ',' and paren_depth == 0:
                lines.append(''.join(current))
                current = []
                continue

            current.append(char)

        if current:
            lines.append(''.join(current))

        return lines