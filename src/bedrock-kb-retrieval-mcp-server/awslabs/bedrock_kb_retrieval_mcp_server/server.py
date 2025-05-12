# server.py
import argparse
import json
import os
import sys
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
from sse_starlette.sse import EventSourceResponse
from typing import Dict, List, Optional, Any
import uuid

# Import your existing code
from awslabs.bedrock_kb_retrieval_mcp_server.knowledgebases.clients import (
    get_bedrock_agent_client,
    get_bedrock_agent_runtime_client,
)
from awslabs.bedrock_kb_retrieval_mcp_server.knowledgebases.discovery import (
    DEFAULT_KNOWLEDGE_BASE_TAG_INCLUSION_KEY,
    discover_knowledge_bases,
)
from awslabs.bedrock_kb_retrieval_mcp_server.knowledgebases.retrieval import (
    query_knowledge_base,
)
from loguru import logger

# Remove all default handlers then add our own
logger.remove()
logger.add(sys.stderr, level='INFO')

# Initialize clients
try:
    kb_runtime_client = get_bedrock_agent_runtime_client(
        region_name=os.getenv('AWS_REGION'),
        profile_name=os.getenv('AWS_PROFILE'),
    )
    kb_agent_mgmt_client = get_bedrock_agent_client(
        region_name=os.getenv('AWS_REGION'),
        profile_name=os.getenv('AWS_PROFILE'),
    )
except Exception as e:
    logger.error(f'Error getting bedrock agent client: {e}')
    raise e

kb_inclusion_tag_key = os.getenv('KB_INCLUSION_TAG_KEY', DEFAULT_KNOWLEDGE_BASE_TAG_INCLUSION_KEY)

# Parse reranking enabled environment variable
kb_reranking_enabled_raw = os.getenv('BEDROCK_KB_RERANKING_ENABLED')
kb_reranking_enabled = False  # Default value is now False (off)
if kb_reranking_enabled_raw is not None:
    kb_reranking_enabled_raw = kb_reranking_enabled_raw.strip().lower()
    if kb_reranking_enabled_raw in ('true', '1', 'yes', 'on'):
        kb_reranking_enabled = True
logger.info(
    f'Default reranking enabled: {kb_reranking_enabled} (from BEDROCK_KB_RERANKING_ENABLED)'
)

# Create FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active connections
connections: Dict[str, asyncio.Queue] = {}

# Handle SSE connections
@app.get("/sse")
async def sse(request: Request):
    session_id = str(uuid.uuid4())
    queue = asyncio.Queue()
    connections[session_id] = queue
    
    async def event_generator():
        yield {"event": "endpoint", "data": f"/messages/?session_id={session_id}"}
        try:
            while True:
                message = await queue.get()
                if message is None:
                    break
                yield {"data": message}
        except asyncio.CancelledError:
            pass
        finally:
            connections.pop(session_id, None)
    
    return EventSourceResponse(event_generator())

# Handle POST requests to /sse
@app.post("/sse")
async def post_sse():
    return Response(status_code=200)

# Handle JSON-RPC messages
@app.post("/messages/")
async def messages(request: Request):
    session_id = request.query_params.get("session_id")
    if not session_id or session_id not in connections:
        return Response(status_code=404)
    
    data = await request.json()
    response = await handle_message(data)
    
    return response

# Handle root path
@app.get("/")
@app.post("/")
async def root():
    return Response(status_code=200)

# Handle messages
async def handle_message(data: Dict[str, Any]):
    method = data.get("method")
    params = data.get("params", {})
    id = data.get("id", 0)
    
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": id,
            "result": {
                "name": "awslabs.bedrock-kb-retrieval-mcp-server",
                "version": "1.0.0",
                "capabilities": {}
            }
        }
    elif method == "shutdown":
        return {
            "jsonrpc": "2.0",
            "id": id,
            "result": None
        }
    elif method == "resource://knowledgebases":
        result = await discover_knowledge_bases(kb_agent_mgmt_client, kb_inclusion_tag_key)
        return {
            "jsonrpc": "2.0",
            "id": id,
            "result": result
        }
    elif method == "QueryKnowledgeBases":
        result = await query_knowledge_base(
            query=params.get("query", ""),
            knowledge_base_id=params.get("knowledge_base_id", ""),
            kb_agent_client=kb_runtime_client,
            number_of_results=params.get("number_of_results", 10),
            reranking=params.get("reranking", kb_reranking_enabled),
            reranking_model_name=params.get("reranking_model_name", "AMAZON"),
            data_source_ids=params.get("data_source_ids", None),
        )
        return {
            "jsonrpc": "2.0",
            "id": id,
            "result": result
        }
    else:
        return {
            "jsonrpc": "2.0",
            "id": id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }

def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(description='A Model Context Protocol (MCP) server')
    parser.add_argument('--port', type=int, default=8080, help='Port to run the server on')
    
    args = parser.parse_args()
    
    uvicorn.run(app, host="0.0.0.0", port=args.port)

if __name__ == '__main__':
    main()
