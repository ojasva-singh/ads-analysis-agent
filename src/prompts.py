def get_sql_generation_prompt(schema_text: str, user_query: str, error_msg: str = None) -> str:
    """
    Generate prompt for SQL query generation.
    
    Args:
        schema_text: Database schema information
        user_query: User's natural language query
        error_msg: Optional SQL error message for correction
    
    Returns:
        Formatted prompt string
    """
    
    if error_msg:
        # Error correction prompt
        return f"""You are a SQL expert. The previous SQL query generated an error.

DATABASE SCHEMA:
{schema_text}

USER QUERY: {user_query}

PREVIOUS ERROR:
{error_msg}

Please generate a CORRECTED SQL query that fixes this error.

IMPORTANT RULES:
1. Return ONLY the SQL query, no explanations
2. Use SQLite syntax
3. Table name is 'facebook_ads'
4. For date filtering, use format 'YYYY-MM-DD'
5. Use proper aggregation functions (SUM, AVG, COUNT, etc.)
6. Always include column aliases for calculated fields
7. Use ROUND() for decimal values (2 decimal places)

SQL Query:"""
    
    else:
        # Initial SQL generation prompt
        return f"""You are a SQL expert. Convert the user's question into a valid SQLite query.

DATABASE SCHEMA:
{schema_text}

USER QUERY: {user_query}

IMPORTANT RULES:
1. Return ONLY the SQL query, no explanations or markdown
2. Use SQLite syntax only
3. Table name is 'facebook_ads'
4. For dates, use format 'YYYY-MM-DD' and DATE() function
5. For percentages (like CTR), calculate as: (clicks * 100.0 / NULLIF(impressions, 0))
6. For cost metrics, use ROUND(value, 2)
7. Always use proper GROUP BY when using aggregation
8. Use ORDER BY to sort results meaningfully
9. Add LIMIT clause for top/bottom queries
10. Handle NULL values using NULLIF or COALESCE

Common calculations:
- CTR (Click-Through Rate) = (clicks * 100.0 / NULLIF(impressions, 0))
- Cost per Click (CPC) = spent / NULLIF(clicks, 0)
- Cost per Conversion = spent / NULLIF(total_conversion, 0)
- Conversion Rate = (total_conversion * 100.0 / NULLIF(clicks, 0))

SQL Query:"""


def get_visualization_prompt(dataframe_info: str, user_query: str) -> str:
    """
    Generate prompt for visualization code generation.
    
    Args:
        dataframe_info: Information about the DataFrame (columns, shape, sample data)
        user_query: User's visualization request
    
    Returns:
        Formatted prompt string
    """
    
    return f"""You are a data visualization expert. Generate Python code using Plotly to create an interactive chart.

DATAFRAME INFORMATION:
{dataframe_info}

The DataFrame variable is named 'df' and is already loaded in the environment.

USER REQUEST: {user_query}

REQUIREMENTS:
1. Use plotly.graph_objects or plotly.express
2. The code must be executable Python code
3. Create a variable named 'fig' containing the Plotly figure
4. Use appropriate chart type (line, bar, scatter, pie, etc.)
5. Add proper titles, axis labels, and formatting
6. Use professional color schemes
7. Make the chart interactive (hover tooltips, zoom, etc.)
8. Handle date columns properly if present
9. For time series, use line charts with markers
10. For comparisons, use bar or grouped bar charts

IMPORTANT:
- Return ONLY executable Python code, no explanations
- Do NOT include import statements (already imported)
- Do NOT include df.to_html() or display code
- The last line should be: fig (just the variable name)

Example format:
fig = go.Figure()
fig.add_trace(go.Scatter(x=df['date'], y=df['value']))
fig.update_layout(title='Chart Title', xaxis_title='X Axis', yaxis_title='Y Axis')
fig
"""

def get_query_intent_prompt(user_query: str) -> str:
    """
    Generate prompt to determine user's intent (data query vs visualization).
    
    Args:
        user_query: User's natural language query
    
    Returns:
        Formatted prompt string
    """
    
    return f"""Analyze the user's query and determine their intent.

USER QUERY: {user_query}

Classify the query into ONE of these categories:

1. DATA_QUERY - User wants tabular data/statistics (e.g., "show me", "what is", "how many", "list", "top 10")
2. VISUALIZATION - User wants a chart/graph (e.g., "plot", "chart", "visualize", "graph", "trend", "compare over time")
3. BOTH - User wants both data and visualization (e.g., "show me daily trends and plot them")

Return ONLY one word: DATA_QUERY, VISUALIZATION, or BOTH

Classification:"""


def get_insight_generation_prompt(query: str, result_summary: str) -> str:
    """
    Generate prompt for insights/explanation of results.
    
    Args:
        query: Original user query
        result_summary: Summary of the query results
    
    Returns:
        Formatted prompt string
    """
    
    return f"""You are a data analyst. Provide a brief, insightful explanation of the query results.

USER QUERY: {query}

RESULTS SUMMARY:
{result_summary}

Provide a 2-3 sentence natural language summary that:
1. Directly answers the user's question
2. Highlights key findings or trends
3. Uses specific numbers from the results
4. Is conversational and easy to understand

Do NOT use phrases like "based on the data" or "according to the results".
Just state the findings naturally.

Summary: """ 