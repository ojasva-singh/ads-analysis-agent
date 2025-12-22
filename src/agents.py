import os
from typing import Tuple, Optional, Any
import pandas as pd
import re
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

from .database import get_schema_text, execute_query
from .prompts import (get_sql_generation_prompt, get_visualization_prompt, get_query_intent_prompt, get_insight_generation_prompt)

# Load environment variables
load_dotenv()

class GeminiAgent:
    """Base agent class for Gemini LLM interactions."""
    
    def __init__(self, model_name: str = None, temperature: float = 0.1, max_retries: int = 3):
        """
        Initialize Gemini agent.
        
        Args:
            model_name: Gemini model name
            temperature: LLM temperature (0-1)
            max_retries: Maximum retry attempts for failed queries
        """
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-3-pro")
        self.temperature = temperature
        self.max_retries = max_retries
        
        # Initialize Gemini LLM
        self.llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            temperature=self.temperature,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
    
    def invoke(self, prompt: str) -> str:
        """
        Invoke LLM with prompt.
        
        Args:
            prompt: Input prompt
            
        Returns:
            LLM response text
        """
        try:
            response = self.llm.invoke(prompt)
            return response.content.strip()
        except Exception as e:
            raise Exception(f"LLM invocation failed: {str(e)}")


class SQLAgent(GeminiAgent):
    """Agent for generating and executing SQL queries."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.schema_text = get_schema_text()
    
    def generate_sql(self, user_query: str, error_msg: str = None) -> str:
        """
        Generate SQL query from natural language.
        
        Args:
            user_query: User's natural language question
            error_msg: Optional error message for correction
            
        Returns:
            Generated SQL query string
        """
        prompt = get_sql_generation_prompt(self.schema_text, user_query, error_msg)
        sql = self.invoke(prompt)
        
        # Clean SQL (remove markdown code blocks if present)
        sql = self._clean_sql(sql)
        
        return sql
    
    def _clean_sql(self, sql: str) -> str:
        """
        Clean SQL query by removing markdown and extra whitespace.
        
        Args:
            sql: Raw SQL string
            
        Returns:
            Cleaned SQL string
        """
        # Remove markdown code blocks
        sql = re.sub(r'```[\w]*\s*', '', sql)
        sql = re.sub(r'```\s*', '', sql)
        
        # Remove extra whitespace
        sql = sql.strip()
        
        # Remove trailing semicolons
        sql = sql.rstrip(';')
        
        return sql
    
    def execute_with_retry(self, user_query: str) -> Tuple[bool, Optional[pd.DataFrame], Optional[str], str]:
        """
        Generate SQL and execute with automatic retry on errors.
        
        Args:
            user_query: User's natural language question
            
        Returns:
            Tuple of (success, dataframe, error_message, sql_query)
        """
        error_msg = None
        sql = None
        
        for attempt in range(self.max_retries):
            try:
                # Generate SQL
                sql = self.generate_sql(user_query, error_msg)
                
                # Execute query
                success, result, error = execute_query(sql)
                
                if success:
                    return True, result, None, sql
                else:
                    # Store error for next iteration
                    error_msg = error
                    
                    # If last attempt, return error
                    if attempt == self.max_retries - 1:
                        return False, None, error, sql
                        
            except Exception as e:
                error_msg = str(e)
                if attempt == self.max_retries - 1:
                    return False, None, error_msg, sql
        
        return False, None, "Max retries exceeded", sql


class VisualizationAgent(GeminiAgent):
    """Agent for generating visualization code."""
    
    def generate_viz_code(self, df: pd.DataFrame, user_query: str) -> str:
        """
        Generate Plotly visualization code.
        
        Args:
            df: DataFrame to visualize
            user_query: User's visualization request
            
        Returns:
            Python code string for creating Plotly figure
        """
        # Create dataframe info summary
        df_info = self._get_dataframe_info(df)
        
        # Generate prompt
        prompt = get_visualization_prompt(df_info, user_query)
        
        # Get code from LLM
        code = self.invoke(prompt)
        
        # Clean code
        code = self._clean_code(code)
        
        return code
    
    def _get_dataframe_info(self, df: pd.DataFrame) -> str:
        """
        Create summary of DataFrame for prompt.
        
        Args:
            df: DataFrame to summarize
            
        Returns:
            Formatted string with DataFrame info
        """
        info = f"Shape: {df.shape[0]} rows, {df.shape[1]} columns\n\n"
        info += "Columns:\n"
        
        for col in df.columns:
            dtype = df[col].dtype
            sample_values = df[col].head(3).tolist()
            info += f"  - {col} ({dtype}): {sample_values}\n"
        
        return info
    
    def _clean_code(self, code: str) -> str:
        """
        Clean generated Python code.
        
        Args:
            code: Raw code string
            
        Returns:
            Cleaned code string
        """
        # Remove markdown code blocks
        code = re.sub(r'```[\w]*\s*', '', code)
        code = re.sub(r'```\s*', '', code)
        
        # Remove import statements (we'll handle them separately)
        code = re.sub(r'import.*\n', '', code)
        code = re.sub(r'from.*import.*\n', '', code)
        
        return code.strip()
    
    def execute_viz_code(self, df: pd.DataFrame, code: str) -> Tuple[bool, Any, Optional[str]]:
        """
        Execute visualization code safely.
        
        Args:
            df: DataFrame to visualize
            code: Python code to execute
            
        Returns:
            Tuple of (success, figure, error_message)
        """
        try:
            import plotly.graph_objects as go
            import plotly.express as px
            
            # Create execution namespace
            namespace = {
                'df': df,
                'pd': pd,
                'go': go,
                'px': px
            }
            
            # Execute code
            exec(code, namespace)
            
            # Get figure from namespace
            fig = namespace.get('fig')
            
            if fig is None:
                return False, None, "Code did not create 'fig' variable"
            
            return True, fig, None
            
        except Exception as e:
            return False, None, f"Visualization error: {str(e)}"


class CoordinatorAgent(GeminiAgent):
    """Agent for coordinating query routing and response generation."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sql_agent = SQLAgent(**kwargs)
        self.viz_agent = VisualizationAgent(**kwargs)
    
    def determine_intent(self, user_query: str) -> str:
        """
        Determine user's intent (DATA_QUERY, VISUALIZATION, or BOTH).
        
        Args:
            user_query: User's question
            
        Returns:
            Intent classification string
        """
        prompt = get_query_intent_prompt(user_query)
        intent = self.invoke(prompt).upper()
        
        # Validate intent
        valid_intents = ["DATA_QUERY", "VISUALIZATION", "BOTH"]
        if intent not in valid_intents:
            # Default to DATA_QUERY if unclear
            intent = "DATA_QUERY"
        
        return intent
    
    def generate_insights(self, user_query: str, df: pd.DataFrame) -> str:
        """
        Generate natural language insights from query results.
        
        Args:
            user_query: Original user query
            df: Results dataframe
            
        Returns:
            Natural language summary
        """
        # Create result summary
        summary = f"Returned {len(df)} rows\n"
        summary += f"Columns: {', '.join(df.columns.tolist())}\n\n"
        
        # Add sample data
        if len(df) > 0:
            summary += "Sample results:\n"
            summary += df.head(3).to_string()
        
        # Generate insights
        prompt = get_insight_generation_prompt(user_query, summary)
        insights = self.invoke(prompt)
        
        return insights
    
    def process_query(self, user_query: str) -> Tuple[bool, dict]:
        """
        Process user query end-to-end.
        
        Args:
            user_query: User's natural language question
    
        Returns:
            Tuple of (success, result_dict)
            result_dict contains: intent, data, sql, figure, insights, error
        """
        result = {
            'intent': None,
            'data': None,
            'sql': None,
            'figure': None,
            'insights': None,
            'error': None
        }
        
        try:
            # Determine intent
            intent = self.determine_intent(user_query)
            result['intent'] = intent
            
            # Execute SQL query (needed for both data and visualization)
            success, df, error, sql = self.sql_agent.execute_with_retry(user_query)
            result['sql'] = sql
            
            if not success:
                result['error'] = error
                return False, result
            
            result['data'] = df
            
            # Generate insights
            if len(df) > 0:
                result['insights'] = self.generate_insights(user_query, df)
            
            # Generate visualization if requested
            if intent in ["VISUALIZATION", "BOTH"] and len(df) > 0:
                viz_code = self.viz_agent.generate_viz_code(df, user_query)
                viz_success, fig, viz_error = self.viz_agent.execute_viz_code(df, viz_code)
                
                if viz_success:
                    result['figure'] = fig
                else:
                    result['error'] = viz_error
            
            return True, result
            
        except Exception as e:
            result['error'] = str(e)
            return False, result


# Global coordinator instance
coordinator = CoordinatorAgent()