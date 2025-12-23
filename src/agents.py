import os
from typing import Tuple, Optional, Any
import pandas as pd
import re
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from .database import get_schema_text, execute_query
from .prompts import (get_sql_generation_prompt, get_visualization_prompt, 
                      get_query_intent_prompt, get_insight_generation_prompt)
import traceback
import plotly.graph_objects as go
import plotly.express as px

# Load environment variables
load_dotenv()


class GeminiAgent:
    """Base agent class for Gemini LLM interactions."""
    
    def __init__(self, model_name: str = None, temperature: float = 0.1, max_retries: int = 3):
        """Initialize Gemini agent."""
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
        self.temperature = temperature
        self.max_retries = max_retries
        self.llm = ChatGoogleGenerativeAI(
            model=self.model_name, 
            temperature=self.temperature, 
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
    
    def invoke(self, prompt: str) -> str:
        """Invoke LLM with prompt."""
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
        """Generate SQL query from natural language."""
        prompt = get_sql_generation_prompt(self.schema_text, user_query, error_msg)
        sql = self.invoke(prompt)
        sql = self._clean_sql(sql)
        return sql
    
    def _clean_sql(self, sql: str) -> str:
        """Clean SQL query by removing markdown and extra whitespace."""
        # Remove markdown code blocks
        sql = re.sub(r'```[\w]*\s*', '', sql)
        sql = re.sub(r'```\s*', '', sql)
        sql = sql.strip()
        sql = sql.rstrip(';')
        return sql
    
    def execute_with_retry(self, user_query: str) -> Tuple[bool, Optional[pd.DataFrame], Optional[str], str]:
        """Generate SQL and execute with automatic retry on errors."""
        error_msg = None
        sql = None
        
        for attempt in range(self.max_retries):
            try:
                sql = self.generate_sql(user_query, error_msg)
                success, result, error = execute_query(sql)
                
                if success:
                    return True, result, None, sql
                else:
                    error_msg = error
                    if attempt == self.max_retries - 1:
                        return False, None, error, sql
            except Exception as e:
                error_msg = str(e)
                if attempt == self.max_retries - 1:
                    return False, None, error_msg, sql
        
        return False, None, "Max retries exceeded", sql


class VisualizationAgent(GeminiAgent):
    """Agent for generating visualization code using Plotly."""
    
    def generate_viz_code(self, df: pd.DataFrame, user_query: str) -> str:
        """Generate Plotly visualization code."""
        from .prompts import get_visualization_prompt
        
        df_info = self._get_dataframe_info(df)
        prompt = get_visualization_prompt(df_info, user_query)
        
        print(f"DEBUG: Sending prompt to LLM (length: {len(prompt)})")
        code = self.invoke(prompt)
        print(f"DEBUG: Raw LLM response length: {len(code)}")
        print(f"DEBUG: Raw LLM response: {code[:500]}")  # First 500 chars
        
        code = self._clean_code(code)
        print(f"DEBUG: Cleaned code length: {len(code)}")
        print(f"DEBUG: Cleaned code: {code}")
        
        return code

    def _get_dataframe_info(self, df: pd.DataFrame) -> str:
        """Create summary of DataFrame."""
        info = f"Shape: {df.shape[0]} rows, {df.shape[1]} columns\n\n"
        info += "Columns:\n"
        for col in df.columns:
            dtype = df[col].dtype
            sample_values = df[col].head(3).tolist()
            info += f"  - {col} ({dtype}): {sample_values}\n"
        return info
    
    def _clean_code(self, code: str) -> str:
        """Clean generated Python code."""
        if not code or len(code.strip()) == 0:
            print("DEBUG: Empty code received from LLM!")
            return code
        
        print(f"DEBUG: Code before cleaning (length {len(code)}):\n{code}\n{'='*50}")
        
        # Remove markdown code blocks
        code = re.sub(r'```python\n?', '', code)
        code = re.sub(r'```', '', code)
        
        # Split into lines
        lines = code.split('\n')
        cleaned_lines = []
        skip_empty_start = True
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Skip empty lines only at the very start
            if skip_empty_start and not stripped:
                continue
            else:
                skip_empty_start = False
            
            # Skip language identifier lines
            if stripped.lower() in ['python', 'py', 'python3', 'plotly']:
                print(f"DEBUG: Skipping language tag at line {i}: {stripped}")
                continue
            
            # Skip import statements (we already have them in namespace)
            if stripped.startswith('import ') or stripped.startswith('from '):
                print(f"DEBUG: Skipping import at line {i}: {stripped}")
                continue
            
            # Keep everything else (including empty lines in the middle, comments, actual code)
            cleaned_lines.append(line)
        
        code = '\n'.join(cleaned_lines).strip()
        
        print(f"DEBUG: Code after cleaning (length {len(code)}):\n{code}\n{'='*50}")
        
        # Ensure code ends with 'fig' if not already there
        if code and not code.strip().endswith('fig'):
            print("DEBUG: Adding 'fig' at the end")
            code += '\nfig'
        
        return code


    
    def execute_viz_code(self, df: pd.DataFrame, code: str) -> Tuple[bool, Any, Optional[str]]:
        """Execute visualization code safely with Plotly."""
        if not code or len(code.strip()) == 0:
            return False, None, "No visualization code was generated"
        
        try:
            import plotly.graph_objects as go
            import plotly.express as px
            import numpy as np
            
            print(f"DEBUG: Executing code:\n{code}")
            
            # Create execution namespace
            namespace = {
                'df': df,
                'pd': pd,
                'go': go,
                'px': px,
                'np': np
            }
            
            # Execute code
            exec(code, namespace)
            
            # Get figure - try multiple ways
            fig = namespace.get('fig')
            if fig is None:
                print("DEBUG: 'fig' variable not found in namespace")
                print(f"DEBUG: Available variables: {list(namespace.keys())}")
                return False, None, "Code did not create a 'fig' variable"
            
            print(f"DEBUG: Figure type: {type(fig)}")
            return True, fig, None
            
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"DEBUG: Execution error:\n{error_trace}")
            return False, None, f"Visualization error: {str(e)}"



class CoordinatorAgent(GeminiAgent):
    """Agent for coordinating query routing and response generation."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sql_agent = SQLAgent(**kwargs)
        self.viz_agent = VisualizationAgent(**kwargs)
    
    def determine_intent(self, user_query: str) -> str:
        """Determine user's intent (DATA_QUERY, VISUALIZATION, or BOTH)."""
        prompt = get_query_intent_prompt(user_query)
        intent = self.invoke(prompt).upper()
        
        valid_intents = ["DATA_QUERY", "VISUALIZATION", "BOTH"]
        if intent not in valid_intents:
            intent = "DATA_QUERY"
        
        return intent
    
    def generate_insights(self, user_query: str, df: pd.DataFrame) -> str:
        """Generate natural language insights from query results."""
        summary = f"Returned {len(df)} rows\n"
        summary += f"Columns: {', '.join(df.columns.tolist())}\n\n"
        
        if len(df) > 0:
            summary += "Sample results:\n"
            summary += df.head(3).to_string()
        
        prompt = get_insight_generation_prompt(user_query, summary)
        insights = self.invoke(prompt)
        return insights
    
    def process_query(self, user_query: str) -> Tuple[bool, dict]:
        """Process user query end-to-end."""
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
                print(f"DEBUG: Attempting to generate visualization for {len(df)} rows")
                print(f"DEBUG: DataFrame columns: {df.columns.tolist()}")
                print(f"DEBUG: DataFrame head:\n{df.head()}")
                
                try:
                    viz_code = self.viz_agent.generate_viz_code(df, user_query)
                    print(f"DEBUG: Generated viz code length: {len(viz_code)}")
                    
                    if not viz_code or len(viz_code.strip()) == 0:
                        print("DEBUG: Empty code returned from generate_viz_code")
                        result['error'] = "LLM returned empty visualization code"
                    else:
                        print(f"DEBUG: Viz code preview: {viz_code[:200]}")
                        viz_success, fig, viz_error = self.viz_agent.execute_viz_code(df, viz_code)
                        print(f"DEBUG: Viz execution - success: {viz_success}, fig: {fig is not None}, error: {viz_error}")
                        
                        if viz_success and fig is not None:
                            result['figure'] = fig
                            print("DEBUG: Figure assigned to result")
                        else:
                            print(f"DEBUG: Viz failed - error: {viz_error}")
                            result['error'] = viz_error
                except Exception as e:
                    print(f"DEBUG: Exception in viz generation: {str(e)}")
                    print(f"DEBUG: Traceback: {traceback.format_exc()}")
                    result['error'] = str(e)

            
            # CRITICAL FIX: Always return the result
            return True, result
            
        except Exception as e:
            result['error'] = str(e)
            return False, result


# Global coordinator instance
coordinator = CoordinatorAgent()
