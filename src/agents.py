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
    """Agent for generating visualization code using Matplotlib."""
    
    def generate_viz_code(self, df: pd.DataFrame, user_query: str) -> str:
        """Generate Matplotlib visualization code."""
        df_info = self._get_dataframe_info(df)
        
        prompt = f"""You are a data visualization expert. Generate Python code using Matplotlib to create a chart.

DATAFRAME INFORMATION:
{df_info}

The DataFrame variable is named 'df' and is already loaded.

USER REQUEST: {user_query}

REQUIREMENTS:
1. Use matplotlib.pyplot (already imported as plt)
2. Create appropriate chart type (line, bar, scatter, pie, etc.)
3. Add proper titles, axis labels
4. Use figure size (10, 6)
5. No plt.show() - just create the figure

IMPORTANT:
- Return ONLY executable Python code
- Do NOT include import statements
- Do NOT include markdown code fences or language tags
- Create a variable named 'fig' containing the figure

Example:
fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(df['date'], df['value'])
ax.set_title('Chart Title')
ax.set_xlabel('X Axis')
ax.set_ylabel('Y Axis')
plt.tight_layout()
"""
        
        code = self.invoke(prompt)
        code = self._clean_code(code)
        return code
    
    def _get_dataframe_info(self, df: pd.DataFrame) -> str:
        """Create summary of DataFrame."""
        info = f"Shape: {df.shape[0]} rows, {df.shape[1]} columns\n\n"
        info += "Columns:\n"
        for col in df.columns:
            dtype = df[col].dtype
            sample_values = df[col].head(3).tolist()
            info += f" - {col} ({dtype}): {sample_values}\n"
        return info
    
    def _clean_code(self, code: str) -> str:
        """Clean generated Python code aggressively."""
        # Remove markdown code blocks with or without language specifier
        code = re.sub(r'```[\w]*', '', code)  # Remove opening fence with language
        code = re.sub(r'```', '', code)       # Remove closing fence
        
        # Remove any standalone language tags at the start
        lines = code.split('\n')
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            # Skip lines that are just language names
            if stripped.lower() in ['python', 'py', 'python3']:
                continue
            cleaned_lines.append(line)
        
        code = '\n'.join(cleaned_lines)
        
        # Remove import statements (we handle them)
        code = re.sub(r'^import.*\n', '', code, flags=re.MULTILINE)
        code = re.sub(r'^from.*import.*\n', '', code, flags=re.MULTILINE)
        
        return code.strip()
    
    def execute_viz_code(self, df: pd.DataFrame, code: str) -> Tuple[bool, Any, Optional[str]]:
        """Execute visualization code safely with Matplotlib."""
        try:
            import matplotlib.pyplot as plt
            import matplotlib
            matplotlib.use('Agg')  # Use non-interactive backend
            
            # Create execution namespace
            namespace = {
                'df': df,
                'pd': pd,
                'plt': plt,
                'np': __import__('numpy')
            }
            
            # Execute code
            exec(code, namespace)
            
            # Get figure
            fig = namespace.get('fig')
            if fig is None:
                # Try to get current figure if 'fig' wasn't created
                fig = plt.gcf()
            
            if fig is None:
                return False, None, "Code did not create a figure"
            
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
                
                try:
                    viz_code = self.viz_agent.generate_viz_code(df, user_query)
                    print(f"DEBUG: Generated viz code length: {len(viz_code)}")
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
