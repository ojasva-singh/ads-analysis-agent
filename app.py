import chainlit as cl
from src.agents import coordinator
from src.database import get_statistics
from src.renderers import HTMLRenderer
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


# @cl.on_message
# async def main(message: cl.Message):
#     """
#     Handle incoming user messages.
    
#     Args:
#         message: User's message object
#     """
#     user_query = message.content.strip()
    
#     if not user_query:
#         await cl.Message(
#             content="Please ask a question about the Facebook ad campaign data.",
#             author="Assistant"
#         ).send()
#         return
    
#     # Show processing indicator
#     processing_msg = cl.Message(
#         content="🔍 Analyzing your query and generating insights...",
#         author="Assistant"
#     )
#     await processing_msg.send()
    
#     try:
#         # Get coordinator from session
#         coord = cl.user_session.get("coordinator")
        
#         # Process query
#         success, result = coord.process_query(user_query)
        
#         # Remove processing message
#         await processing_msg.remove()
        
#         if not success:
#             # Handle error
#             error_text = f"❌ **Error**: {result.get('error', 'Unknown error')}"
            
#             # Show SQL if available
#             if result.get('sql'):
#                 sql_text = result['sql']
#                 error_text += f"\n\n**Generated SQL:**\n```sql\n{sql_text}\n```)"
            
#             await cl.Message(
#                 content=error_text,
#                 author="Assistant"
#             ).send()
#             return
        
#         # Build response parts
#         response_parts = []
        
#         # 1. Natural language insights
#         if result.get('insights'):
#             response_parts.append(result['insights'])
        
#         # 2. Show SQL query
#         if result.get('sql'):
#             sql_text = result['sql']
#             response_parts.append(f"\n**Generated SQL:**")
#             response_parts.append(f"```sql\n{sql_text}\n```")
        
#         # Send text response first
#         if response_parts:
#             full_response = "\n".join(response_parts)
#             await cl.Message(
#                 content=full_response,
#                 author="Assistant"
#             ).send()
        
#         # 3. Data table using Custom JSX Element
#         intent = result.get('intent', 'DATA_QUERY')
#         df = result.get('data')
        
#         if df is not None and len(df) > 0:
#             if intent in ['DATA_QUERY', 'BOTH']:
#                 # Convert DataFrame to format for JSX component
#                 columns = df.columns.tolist()
#                 rows = df.head(100).values.tolist()
                
#                 # Format numbers in rows
#                 formatted_rows = []
#                 for row in rows:
#                     formatted_row = []
#                     for val in row:
#                         if isinstance(val, (int, float)):
#                             formatted_row.append(f"{val:,.2f}" if isinstance(val, float) else f"{val:,}")
#                         else:
#                             formatted_row.append(str(val))
#                     formatted_rows.append(formatted_row)
                
#                 table_element = cl.CustomElement(
#                     name="DataTable",
#                     props={
#                         "columns": columns,
#                         "rows": formatted_rows,
#                         "title": f"Query Results ({len(df)} rows)"
#                     },
#                     display="inline"
#                 )
                
#                 await cl.Message(
#                     content="📊 **Query Results:**",
#                     elements=[table_element]
#                 ).send()
#         else:
#             if intent in ['DATA_QUERY', 'BOTH']:
#                 await cl.Message(
#                     content="⚠️ No data found for your query.",
#                     author="Assistant"
#                 ).send()
        
#         # 4. Visualization - using Custom Chart Element
#         if intent in ['VISUALIZATION', 'BOTH']:
#             print("DEBUG: Starting visualization block")
#             print(f"DEBUG: Intent is {intent}")
            
#             try:
#                 fig = result.get('figure')
#                 print(f"DEBUG: Figure retrieved: {fig is not None}")
                
#                 if fig is not None:
#                     print("DEBUG: About to create Chart element")
                    
#                     try:
#                         # Import the renderer
#                         from src.renderers import HTMLRenderer
                        
#                         # Convert Plotly figure to HTML
#                         chart_html = HTMLRenderer.render_chart(fig, include_plotlyjs='cdn')
#                         print(f"DEBUG: Chart HTML generated, length: {len(chart_html)}")
                        
#                         # Use Custom Chart Element
#                         chart_element = cl.CustomElement(
#                             name="Chart",
#                             props={
#                                 "html": chart_html
#                             },
#                             display="inline"
#                         )
                        
#                         print("DEBUG: Chart element created successfully")
                        
#                         await cl.Message(
#                             content="📈 **Interactive Visualization:**",
#                             elements=[chart_element]
#                         ).send()
#                         print("DEBUG: Chart message sent successfully")
                        
#                     except Exception as chart_error:
#                         print(f"DEBUG: Chart creation error: {str(chart_error)}")
#                         print(f"DEBUG: Chart error trace:\n{traceback.format_exc()}")
#                         await cl.Message(
#                             content=f"⚠️ **Chart rendering error:** {str(chart_error)}",
#                             author="Assistant"
#                         ).send()
                        
#                 elif df is not None and len(df) > 0:
#                     print("DEBUG: No figure but have data")
#                     await cl.Message(
#                         content="⚠️ Could not generate visualization.",
#                         author="Assistant"
#                     ).send()
                    
#             except Exception as viz_error:
#                 error_trace = traceback.format_exc()
#                 print(f"DEBUG: Visualization exception caught!")
#                 print(f"DEBUG: Error: {str(viz_error)}")
#                 print(f"DEBUG: Full trace:\n{error_trace}")
                
#                 await cl.Message(
#                     content=f"⚠️ **Visualization Error:**\n``````",
#                     author="Assistant"
#                 ).send()


#     except Exception as e:
#         # Remove processing message on error
#         try:
#             await processing_msg.remove()
#         except:
#             pass
        
#         # Log detailed error
#         error_trace = traceback.format_exc()
#         print(f"Error processing query: {error_trace}")
        
#         # Send user-friendly error
#         await cl.Message(content=f"(❌ **An unexpected error occurred:**\n```\n{str(e)}\n```)",
#             author="Assistant"
#         ).send()

@cl.on_message
async def main(message: cl.Message):
    """
    Handle incoming user messages.
    
    Args:
        message: User's message object
    """
    import asyncio  # Add this import at the top
    
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
        print(f"\n{'='*60}")
        print(f"NEW QUERY: {user_query}")
        print(f"{'='*60}")
        
        # Get coordinator from session
        coord = cl.user_session.get("coordinator")
        if not coord:
            raise Exception("Coordinator not found in session")
        
        # Process query
        print("DEBUG: Calling process_query...")
        success, result = coord.process_query(user_query)
        print(f"DEBUG: Query processed - success: {success}")
        
        # Remove processing message
        await processing_msg.remove()
        
        if not success:
            print("DEBUG: Query failed")
            # Handle error
            error_text = f"❌ **Error**: {result.get('error', 'Unknown error')}"
            
            # Show SQL if available - FIXED SYNTAX
            if result.get('sql'):
                sql_text = result['sql']
                error_text += f"\n\n**Generated SQL:**\n``````"  # Removed extra )
            
            await cl.Message(
                content=error_text,
                author="Assistant"
            ).send()
            return
        
        print("DEBUG: Building response...")
        
        # Build response parts
        response_parts = []
        
        # 1. Natural language insights
        if result.get('insights'):
            print("DEBUG: Adding insights")
            response_parts.append(result['insights'])
        
        # 2. Show SQL query - FIXED SYNTAX
        if result.get('sql'):
            print("DEBUG: Adding SQL")
            sql_text = result['sql']
            response_parts.append(f"\n**Generated SQL:**\n``````")
        
        # Send text response first
        if response_parts:
            print("DEBUG: Sending text response")
            full_response = "\n".join(response_parts)
            await cl.Message(
                content=full_response,
                author="Assistant"
            ).send()
            await asyncio.sleep(0.3)  # Small delay after text
        
        # 3. Data table using Custom JSX Element
        intent = result.get('intent', 'DATA_QUERY')
        df = result.get('data')
        
        print(f"DEBUG: Intent: {intent}, DataFrame: {df is not None}, Rows: {len(df) if df is not None else 0}")
        
        if df is not None and len(df) > 0:
            if intent in ['DATA_QUERY', 'BOTH']:
                print("DEBUG: Preparing data table")
                try:
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
                    
                    print("DEBUG: Sending data table")
                    await cl.Message(
                        content="📊 **Query Results:**",
                        elements=[table_element]
                    ).send()
                    print("DEBUG: Data table sent successfully")
                    await asyncio.sleep(0.5)  # CRITICAL: Wait before sending chart
                    
                except Exception as table_error:
                    print(f"DEBUG: Table error: {str(table_error)}")
                    print(f"DEBUG: Table traceback:\n{traceback.format_exc()}")
                    await cl.Message(
                        content=f"⚠️ **Table rendering error:** {str(table_error)}",
                        author="Assistant"
                    ).send()
        else:
            if intent in ['DATA_QUERY', 'BOTH']:
                print("DEBUG: No data found")
                await cl.Message(
                    content="⚠️ No data found for your query.",
                    author="Assistant"
                ).send()
        
        # 4. Visualization - using Custom Chart Element
        if intent in ['VISUALIZATION', 'BOTH']:
            print(f"DEBUG: ===== VISUALIZATION BLOCK =====")
            print(f"DEBUG: Intent is {intent}")
            
            try:
                fig = result.get('figure')
                print(f"DEBUG: Figure retrieved: {fig is not None}")
                
                if fig is not None:
                    print("DEBUG: Processing figure for rendering")
                    
                    try:
                        # Import the renderer
                        from src.renderers import HTMLRenderer
                        
                        # Convert Plotly figure to HTML
                        print("DEBUG: Converting figure to HTML...")
                        chart_html = HTMLRenderer.render_chart(fig, include_plotlyjs='cdn')
                        print(f"DEBUG: Chart HTML generated, length: {len(chart_html)}")
                        
                        # Use Custom Chart Element
                        print("DEBUG: Creating Chart element...")
                        chart_element = cl.CustomElement(
                            name="Chart",
                            props={
                                "html": chart_html
                            },
                            display="inline"
                        )
                        print("DEBUG: Chart element created successfully")
                        
                        print("DEBUG: Sending chart message...")
                        await cl.Message(
                            content="📈 **Interactive Visualization:**",
                            elements=[chart_element]
                        ).send()
                        print("DEBUG: ✅ Chart message sent successfully!")
                        await asyncio.sleep(0.2)  # Small delay after chart
                        
                    except Exception as chart_error:
                        print(f"DEBUG: ❌ Chart creation error: {str(chart_error)}")
                        print(f"DEBUG: Chart error trace:\n{traceback.format_exc()}")
                        await cl.Message(
                            content=f"⚠️ **Chart rendering error:** {str(chart_error)}",
                            author="Assistant"
                        ).send()
                        
                elif df is not None and len(df) > 0:
                    print("DEBUG: No figure but have data")
                    await cl.Message(
                        content="⚠️ Could not generate visualization from the data.",
                        author="Assistant"
                    ).send()
                    
            except Exception as viz_error:
                error_trace = traceback.format_exc()
                print(f"DEBUG: ❌ Visualization block exception!")
                print(f"DEBUG: Error: {str(viz_error)}")
                print(f"DEBUG: Full trace:\n{error_trace}")
                
                await cl.Message(
                    content=f"⚠️ **Visualization Error:**\n``````",
                    author="Assistant"
                ).send()
        
        print(f"DEBUG: ✅ Query handling completed successfully")
        print(f"{'='*60}\n")
        
    except Exception as e:
        # Remove processing message on error
        try:
            await processing_msg.remove()
        except:
            pass
        
        # Log detailed error
        error_trace = traceback.format_exc()
        print(f"\n{'!'*60}")
        print(f"CRITICAL ERROR in main handler!")
        print(f"{'!'*60}")
        print(f"Error: {str(e)}")
        print(f"Full traceback:\n{error_trace}")
        print(f"{'!'*60}\n")
        
        # Send user-friendly error
        await cl.Message(
            content=f"❌ **An unexpected error occurred:**\n``````\n\nPlease try rephrasing your query.",
            author="Assistant"
        ).send()


@cl.on_chat_end
def end():
    """
    Cleanup when chat session ends.
    """
    print("Chat session ended")
