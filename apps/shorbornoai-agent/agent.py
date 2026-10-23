import os
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

mcp = FastMCP("ShorbornoAI-Cloud-Agent")
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=os.getenv("GEMINI_API_KEY"))
DB_URI = os.getenv("DATABASE_URL")
app = FastAPI(title="ShorbornoAI Cloud Agent Microservice")

pool = None
checkpointer = None

@app.on_event("startup")
async def startup_event():
    global pool, checkpointer
    pool = AsyncConnectionPool(conninfo=DB_URI, max_size=20, kwargs={"autocommit": True})
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()

@app.on_event("shutdown")
async def shutdown_event():
    if pool:
        await pool.close()

@mcp.tool()
async def process_workspace_task(message: str, thread_id: str = "default_session") -> str:
    """Processes pipeline development requests with thread isolation safeguards."""
    if checkpointer is None:
        raise RuntimeError("Database persistence engine checkpoint is still initializing.")
    agent_executor = create_react_agent(llm, tools=[], checkpointer=checkpointer)
    config = {"configurable": {"thread_id": f"acp_{thread_id}"}}
    result = await agent_executor.ainvoke({"messages": [("user", message)]}, config=config)
    return result["messages"][-1].content

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "shorbornoai-agent"}

app.mount("/mcp", mcp.sse_app())
