import sqlite3
from typing import Optional, Dict, List, Tuple, Any
from contextlib import contextmanager
import pandas as pd
from pathlib import Path


class DatabaseManager:
    """Manages SQLite database connections and operations."""
    
    def __init__(self, db_path: str = "data/campaigns.db"):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._verify_database()
    
    def _verify_database(self):
        """Verify that database file exists and is accessible."""
        if not Path(self.db_path).exists():
            raise FileNotFoundError(
                f"Database not found at {self.db_path}. "
                f"Please run 'python setup_db.py' first."
            )
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.
        
        Yields:
            sqlite3.Connection: Database connection object
        """
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()
    
    def execute_query(self, query: str, params: Optional[Tuple] = None) -> Tuple[bool, Any, Optional[str]]:
        """
        Execute SQL query and return results.
        
        Args:
            query: SQL query string
            params: Optional query parameters for parameterized queries
        
        Returns:
            Tuple of (success: bool, result: DataFrame or None, error: str or None)
        """
        try:
            with self.get_connection() as conn:
                # Execute query and return as DataFrame
                df = pd.read_sql_query(query, conn, params=params)
                return True, df, None
                
        except sqlite3.Error as e:
            error_msg = f"SQL Error: {str(e)}"
            return False, None, error_msg
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            return False, None, error_msg
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Retrieve complete database schema information.
        
        Returns:
            Dictionary containing schema details including:
            - table_name
            - columns (with names and types)
            - sample_values
            - row_count
            - column_descriptions
        """
        schema_info = {
            "table_name": "facebook_ads",
            "columns": [],
            "sample_values": {},
            "row_count": 0,
            "column_descriptions": self._get_column_descriptions()
        }
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get column information
            cursor.execute("PRAGMA table_info(facebook_ads)")
            columns = cursor.fetchall()
            
            for col in columns:
                col_name = col[1]
                col_type = col[2]
                schema_info["columns"].append({
                    "name": col_name,
                    "type": col_type
                })
                
                # Get sample values for each column
                cursor.execute(
                    f"SELECT DISTINCT {col_name} FROM facebook_ads "
                    f"WHERE {col_name} IS NOT NULL LIMIT 5"
                )
                samples = [row[0] for row in cursor.fetchall()]
                schema_info["sample_values"][col_name] = samples
            
            # Get row count
            cursor.execute("SELECT COUNT(*) FROM facebook_ads")
            schema_info["row_count"] = cursor.fetchone()[0]
        
        return schema_info
    
    def _get_column_descriptions(self) -> Dict[str, str]:
        """
        Get human-readable descriptions for each column.
        
        Returns:
            Dictionary mapping column names to descriptions
        """
        return {
            "ad_id": "Unique identifier for each ad",
            "reporting_start": "Start date of the reporting period (YYYY-MM-DD)",
            "reporting_end": "End date of the reporting period (YYYY-MM-DD)",
            "campaign_id": "Campaign identifier",
            "fb_campaign_id": "Facebook campaign identifier",
            "age": "Age group of the target audience (e.g., '30-34', '45-49')",
            "gender": "Gender of the target audience ('M' for Male, 'F' for Female)",
            "interest1": "First interest category code",
            "interest2": "Second interest category code",
            "interest3": "Third interest category code",
            "impressions": "Number of times the ad was displayed",
            "clicks": "Number of clicks on the ad",
            "spent": "Amount spent on the ad campaign in currency units",
            "total_conversion": "Total number of conversions (e.g., purchases, signups)",
            "approved_conversion": "Number of approved/verified conversions"
        }
    
    def get_schema_text(self) -> str:
        """
        Get schema as formatted text for LLM prompts.
        
        Returns:
            Formatted string containing schema information
        """
        schema = self.get_schema()
        
        text = f"Table: {schema['table_name']}\n"
        text += f"Total Rows: {schema['row_count']}\n\n"
        text += "Columns:\n"
        
        for col in schema['columns']:
            col_name = col['name']
            col_type = col['type']
            description = schema['column_descriptions'].get(col_name, "")
            samples = schema['sample_values'].get(col_name, [])
            
            text += f"  - {col_name} ({col_type}): {description}\n"
            if samples:
                sample_str = ", ".join(str(s) for s in samples[:3])
                text += f"    Sample values: {sample_str}\n"
        
        return text
    
    def get_table_statistics(self) -> Dict[str, Any]:
        """
        Get useful statistics about the data for context.
        
        Returns:
            Dictionary containing various statistics
        """
        stats = {}
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Date range
            cursor.execute(
                "SELECT MIN(reporting_start), MAX(reporting_end) FROM facebook_ads"
            )
            date_range = cursor.fetchone()
            stats['date_range'] = {
                'start': date_range[0],
                'end': date_range[1]
            }
            
            # Demographics
            cursor.execute("SELECT DISTINCT age FROM facebook_ads ORDER BY age")
            stats['age_groups'] = [row[0] for row in cursor.fetchall()]
            
            cursor.execute("SELECT DISTINCT gender FROM facebook_ads")
            stats['genders'] = [row[0] for row in cursor.fetchall()]
            
            # Campaign counts
            cursor.execute("SELECT COUNT(DISTINCT campaign_id) FROM facebook_ads")
            stats['total_campaigns'] = cursor.fetchone()[0]
            
            # Performance metrics
            cursor.execute("""
                SELECT 
                    SUM(impressions) as total_impressions,
                    SUM(clicks) as total_clicks,
                    SUM(spent) as total_spent,
                    SUM(total_conversion) as total_conversions,
                    ROUND(SUM(clicks) * 100.0 / NULLIF(SUM(impressions), 0), 2) as ctr,
                    ROUND(SUM(spent) / NULLIF(SUM(total_conversion), 0), 2) as cost_per_conversion
                FROM facebook_ads
            """)
            metrics = cursor.fetchone()
            stats['metrics'] = {
                'total_impressions': metrics[0],
                'total_clicks': metrics[1],
                'total_spent': metrics[2],
                'total_conversions': metrics[3],
                'overall_ctr': metrics[4],
                'cost_per_conversion': metrics[5]
            }
        
        return stats


# Global instance
db_manager = DatabaseManager()


# Convenience functions
def get_schema() -> Dict[str, Any]:
    """Get database schema."""
    return db_manager.get_schema()


def get_schema_text() -> str:
    """Get schema as formatted text."""
    return db_manager.get_schema_text()


def execute_query(query: str) -> Tuple[bool, Any, Optional[str]]:
    """Execute SQL query."""
    return db_manager.execute_query(query)


def get_statistics() -> Dict[str, Any]:
    """Get table statistics."""
    return db_manager.get_table_statistics()
