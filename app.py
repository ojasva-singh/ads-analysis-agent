import chainlit as cl
from src.agents import coordinator
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
                sql_text = result['sql']
                error_text += f"\n\n**Generated SQL:**\n```sql\n{sql_text}\n```)"
            
            await cl.Message(
                content=error_text,
                author="Assistant"
            ).send()
            return
        
        # Build response parts
        response_parts = []
        
        # 1. Natural language insights
        if result.get('insights'):
            response_parts.append(result['insights'])
        
        # 2. Show SQL query
        if result.get('sql'):
            sql_text = result['sql']
            response_parts.append(f"\n**Generated SQL:**")
            response_parts.append(f"```sql\n{sql_text}\n```")
        
        # Send text response first
        if response_parts:
            full_response = "\n".join(response_parts)
            await cl.Message(
                content=full_response,
                author="Assistant"
            ).send()
        
        # 3. Data table using Custom JSX Element
        intent = result.get('intent', 'DATA_QUERY')
        df = result.get('data')
        
        if df is not None and len(df) > 0:
            if intent in ['DATA_QUERY', 'BOTH']:
                # Convert DataFrame to format for JSX component
                columns = df.columns.tolist()
                rows = df.head(100).values.tolist()
                
                # Format numbers in rows
                formatted_rows = []
                for row in rows:
                    formatted_row = []
                    for val in row:
                        if isinstance(val, (int, float)):
                            formatted_row.append(f"{val:,.2f}" if isinstance(val, float) else f"{val:,}")
                        else:
                            formatted_row.append(str(val))
                    formatted_rows.append(formatted_row)
                
                table_element = cl.CustomElement(
                    name="DataTable",
                    props={
                        "columns": columns,
                        "rows": formatted_rows,
                        "title": f"Query Results ({len(df)} rows)"
                    },
                    display="inline"
                )
                
                await cl.Message(
                    content="📊 **Query Results:**",
                    elements=[table_element]
                ).send()
        else:
            if intent in ['DATA_QUERY', 'BOTH']:
                await cl.Message(
                    content="⚠️ No data found for your query.",
                    author="Assistant"
                ).send()
        
        # 4. Visualization - with extensive logging
        if intent in ['VISUALIZATION', 'BOTH']:
            print("DEBUG: Starting visualization block")
            print(f"DEBUG: Intent is {intent}")
            
            try:
                fig = result.get('figure')
                print(f"DEBUG: Figure retrieved: {fig is not None}")
                print(f"DEBUG: Figure type: {type(fig)}")
                
                if fig is not None:
                    print("DEBUG: About to create Pyplot element")
                    
                    # Use Chainlit's Pyplot element
                    elements = [
                        cl.Pyplot(name="chart", figure=fig, display="inline")
                    ]
                    
                    print("DEBUG: Pyplot element created, sending message")
                    
                    await cl.Message(
                        content="📈 **Interactive Visualization:**",
                        elements=elements
                    ).send()
                    
                    print("DEBUG: Message sent successfully")
                    
                elif df is not None and len(df) > 0:
                    print("DEBUG: No figure but have data")
                    await cl.Message(
                        content="⚠️ Could not generate visualization.",
                        author="Assistant"
                    ).send()
            except Exception as viz_error:
                error_trace = traceback.format_exc()
                print(f"DEBUG: Visualization exception caught!")
                print(f"DEBUG: Error: {str(viz_error)}")
                print(f"DEBUG: Full trace:\n{error_trace}")
                
                await cl.Message(
                    content=f"⚠️ **Visualization Error:**\n``````",
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
        await cl.Message(content=f"(❌ **An unexpected error occurred:**\n```\n{str(e)}\n```)",
            author="Assistant"
        ).send()


@cl.on_chat_end
def end():
    """
    Cleanup when chat session ends.
    """
    print("Chat session ended")
