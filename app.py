"""
app.py
------
Main Chainlit application for Facebook Ad Analytics Agent.

Run with: chainlit run app.py
"""

import chainlit as cl
from src.agents import coordinator
from src.renderers import renderer
from src.database import get_statistics
import traceback


# Welcome message and app configuration
WELCOME_MESSAGE = """
# 🎯 Facebook Ad Analytics Agent

Welcome! I'm your AI-powered data analyst for Facebook ad campaign performance.

I can help you:
- 📊 **Query data**: "Show me top 10 campaigns by conversion rate"
- 📈 **Visualize trends**: "Plot daily spending trends for male users"
- 🔍 **Analyze performance**: "What's the average CTR by age group?"
- 💰 **Cost analysis**: "Which campaigns have the lowest cost per conversion?"

**Quick Stats:**
{stats}

Just ask me anything about your Facebook ad campaigns! 🚀
"""


def format_stats(stats: dict) -> str:
    """Format database statistics for welcome message."""
    metrics = stats.get('metrics', {})
    date_range = stats.get('date_range', {})
    
    return f"""
- **Date Range**: {date_range.get('start', 'N/A')} to {date_range.get('end', 'N/A')}
- **Total Campaigns**: {stats.get('total_campaigns', 0):,}
- **Total Impressions**: {metrics.get('total_impressions', 0):,}
- **Total Clicks**: {metrics.get('total_clicks', 0):,}
- **Total Spent**: ${metrics.get('total_spent', 0):,.2f}
- **Overall CTR**: {metrics.get('overall_ctr', 0)}%
"""


@cl.on_chat_start
async def start():
    """
    Initialize chat session when user connects.
    """
    try:
        # Get database statistics
        stats = get_statistics()
        
        # Format and send welcome message
        welcome_text = WELCOME_MESSAGE.format(stats=format_stats(stats))
        
        await cl.Message(
            content=welcome_text,
            author="Assistant"
        ).send()
        
        # Store coordinator in user session
        cl.user_session.set("coordinator", coordinator)
        
    except Exception as e:
        error_msg = f"Failed to initialize application: {str(e)}"
        await cl.Message(
            content=f"❌ **Error**: {error_msg}",
            author="Assistant"
        ).send()


@cl.on_message
async def main(message: cl.Message):
    """
    Handle incoming user messages.
    
    Args:
        message: User's message object
    """
    user_query = message.content.strip()
    
    if not user_query:
        await cl.Message(
            content="Please ask a question about the Facebook ad campaign data.",
            author="Assistant"
        ).send()
        return
    
    # Show processing indicator
    processing_msg = cl.Message(
        content="🔍 Analyzing your query and generating insights...",
        author="Assistant"
    )
    await processing_msg.send()
    
    try:
        # Get coordinator from session
        coord = cl.user_session.get("coordinator")
        
        # Process query
        success, result = coord.process_query(user_query)
        
        # Remove processing message
        await processing_msg.remove()
        
        if not success:
            # Handle error
            error_text = f"❌ **Error**: {result.get('error', 'Unknown error')}"
            
            # Show SQL if available
            if result.get('sql'):
                error_text += f"\n\n**Generated SQL:**\n``````"
            
            await cl.Message(
                content=error_text,
                author="Assistant"
            ).send()
            return
        
        # Build complete response
        response_parts = []
        
        # 1. Natural language insights
        if result.get('insights'):
            response_parts.append(result['insights'])
        
        # 2. Show SQL query
        if result.get('sql'):
            response_parts.append(f"\n**Generated SQL:**\n``````")
        
        # 3. Data table as markdown
        intent = result.get('intent', 'DATA_QUERY')
        df = result.get('data')
        
        if df is not None and len(df) > 0:
            if intent in ['DATA_QUERY', 'BOTH']:
                # Convert DataFrame to markdown table
                markdown_table = df.to_markdown(index=False, tablefmt='github')
                
                # Add table header
                response_parts.append(f"\n**Query Results** ({len(df)} rows):\n")
                response_parts.append(markdown_table)
                
                # Add note if truncated
                if len(df) > 50:
                    response_parts.append(f"\n*Showing all {len(df)} rows*")
        else:
            response_parts.append("\n⚠️ No data found for your query.")
        
        # Send the complete text response
        full_response = "\n".join(response_parts)
        await cl.Message(
            content=full_response,
            author="Assistant"
        ).send()
        
        # 4. Visualization (as separate HTML file)
        if intent in ['VISUALIZATION', 'BOTH']:
            fig = result.get('figure')
            
            if fig is not None:
                # Save chart as HTML file
                import tempfile
                import os
                
                # Create a temporary HTML file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                    chart_html = renderer.render_chart(fig, include_plotlyjs='cdn')
                    f.write(chart_html)
                    temp_path = f.name
                
                # Send as file element
                chart_file = cl.File(
                    name="visualization.html",
                    path=temp_path,
                    display="inline"
                )
                
                await cl.Message(
                    content="📊 **Interactive Visualization:**",
                    elements=[chart_file]
                ).send()
                
                # Clean up temp file after a delay
                # (Chainlit will copy it, so we can delete the original)
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
            elif df is not None and len(df) > 0:
                await cl.Message(
                    content="⚠️ Could not generate visualization, but the data is shown above.",
                    author="Assistant"
                ).send()
        
    except Exception as e:
        # Remove processing message on error
        try:
            await processing_msg.remove()
        except:
            pass
        
        # Log detailed error
        error_trace = traceback.format_exc()
        print(f"Error processing query: {error_trace}")
        
        # Send user-friendly error
        await cl.Message(
            content=f"❌ **An unexpected error occurred:**\n``````",
            author="Assistant"
        ).send()


@cl.on_chat_end
def end():
    """
    Cleanup when chat session ends.
    """
    print("Chat session ended")