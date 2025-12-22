import pandas as pd
import plotly.graph_objects as go

class HTMLRenderer:
    """Renders data and visualizations as styled HTML."""
    
    # CSS styles for tables
    TABLE_STYLES = """
    <style>
        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 14px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }
        .data-table thead tr {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-align: left;
            font-weight: 600;
        }
        .data-table th,
        .data-table td {
            padding: 12px 15px;
            border-bottom: 1px solid #e0e0e0;
        }
        .data-table tbody tr {
            transition: background-color 0.2s ease;
        }
        .data-table tbody tr:hover {
            background-color: #f5f5f5;
        }
        .data-table tbody tr:nth-of-type(even) {
            background-color: #f9f9f9;
        }
        .data-table tbody tr:last-of-type {
            border-bottom: 2px solid #667eea;
        }
        .numeric-col {
            text-align: right;
            font-family: 'Courier New', monospace;
        }
        .table-caption {
            font-size: 12px;
            color: #666;
            margin-top: 8px;
            font-style: italic;
        }
    </style>
    """
    
    @staticmethod
    def render_table(df: pd.DataFrame, max_rows: int = 100, show_index: bool = False) -> str:
        """
        Render DataFrame as styled HTML table.
        
        Args:
            df: DataFrame to render
            max_rows: Maximum rows to display
            show_index: Whether to show DataFrame index
            
        Returns:
            HTML string
        """
        if df is None or len(df) == 0:
            return "<p>No data found.</p>"
        
        # Limit rows if needed
        display_df = df.head(max_rows) if len(df) > max_rows else df
        
        # Format numeric columns
        display_df = display_df.copy()
        for col in display_df.columns:
            if display_df[col].dtype in ['float64', 'float32']:
                display_df[col] = display_df[col].apply(lambda x: f"{x:,.2f}" if pd.notna(x) else "")
            elif display_df[col].dtype in ['int64', 'int32']:
                display_df[col] = display_df[col].apply(lambda x: f"{x:,}" if pd.notna(x) else "")
        
        # Convert to HTML
        html = display_df.to_html(index=show_index, classes='data-table', border=0, escape=False)
        
        # Add caption if truncated
        caption = ""
        if len(df) > max_rows:
            caption = f'<div class="table-caption">Showing {max_rows} of {len(df)} rows</div>'
        
        # Combine styles and table
        return HTMLRenderer.TABLE_STYLES + html + caption
    
    @staticmethod
    def render_chart(fig: go.Figure, include_plotlyjs: str = 'cdn') -> str:
        """
        Render Plotly figure as HTML.
        
        Args:
            fig: Plotly figure object
            include_plotlyjs: How to include Plotly.js ('cdn', True, False)
            
        Returns:
            HTML string
        """
        if fig is None:
            return "<p>No visualization available.</p>"
        
        # Update figure layout for better appearance
        fig.update_layout(
            template='plotly_white',
            hovermode='closest',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Segoe UI, sans-serif', size=12),
            margin=dict(l=40, r=40, t=60, b=40)
        )
        
        # Convert to HTML
        html = fig.to_html(
            include_plotlyjs=include_plotlyjs,
            config={
                'displayModeBar': True,
                'displaylogo': False,
                'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d']
            }
        )
        
        return html
    
    @staticmethod
    def render_error(error_message: str) -> str:
        """
        Render error message as styled HTML.
        
        Args:
            error_message: Error message text
            
        Returns:
            HTML string
        """
        return f"""
        <div style="
            background-color: #fee;
            border-left: 4px solid #f44;
            padding: 15px;
            margin: 10px 0;
            border-radius: 4px;
            font-family: monospace;
        ">
            <strong style="color: #c33;">Error:</strong> {error_message}
        </div>
        """
    
    @staticmethod
    def render_sql(sql: str) -> str:
        """
        Render SQL query as formatted HTML.
        
        Args:
            sql: SQL query string
            
        Returns:
            HTML string
        """
        return f"""
        <div style="
            background-color: #f5f5f5;
            border-left: 4px solid #667eea;
            padding: 15px;
            margin: 10px 0;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            overflow-x: auto;
        ">
            <strong style="color: #667eea;">Generated SQL:</strong><br>
            <pre style="margin: 10px 0 0 0; white-space: pre-wrap;">{sql}</pre>
        </div>
        """


# Global renderer instance
renderer = HTMLRenderer()