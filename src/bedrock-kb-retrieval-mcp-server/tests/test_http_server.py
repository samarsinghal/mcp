# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""Tests for the HTTP server implementation of the bedrock-kb-retrieval-mcp-server."""

import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from awslabs.bedrock_kb_retrieval_mcp_server.server import app, handle_message


class TestHTTPServer:
    """Tests for the HTTP server implementation."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        return TestClient(app)

    def test_root_endpoint(self, client):
        """Test the root endpoint."""
        response = client.get("/")
        assert response.status_code == 200

        response = client.post("/")
        assert response.status_code == 200

    def test_sse_endpoint_get(self, client):
        """Test the SSE endpoint with GET."""
        response = client.get("/sse")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream"
        
        # The first message should be an "endpoint" event with a session ID
        content = response.content.decode("utf-8")
        assert "event: endpoint" in content
        assert "data: /messages/?session_id=" in content

    def test_sse_endpoint_post(self, client):
        """Test the SSE endpoint with POST."""
        response = client.post("/sse")
        assert response.status_code == 200

    @patch("awslabs.bedrock_kb_retrieval_mcp_server.server.handle_message")
    def test_messages_endpoint_invalid_session(self, mock_handle_message, client):
        """Test the messages endpoint with an invalid session ID."""
        response = client.post("/messages/", params={"session_id": "invalid-session"})
        assert response.status_code == 404
        mock_handle_message.assert_not_called()

    @patch("awslabs.bedrock_kb_retrieval_mcp_server.server.handle_message")
    async def test_handle_message_initialize(self, mock_handle_message):
        """Test the handle_message function with initialize method."""
        mock_handle_message.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "name": "awslabs.bedrock-kb-retrieval-mcp-server",
                "version": "1.0.0",
                "capabilities": {}
            }
        }
        
        result = await handle_message({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        })
        
        assert result["jsonrpc"] == "2.0"
        assert result["id"] == 1
        assert result["result"]["name"] == "awslabs.bedrock-kb-retrieval-mcp-server"
        assert result["result"]["version"] == "1.0.0"
        assert result["result"]["capabilities"] == {}

    @patch("awslabs.bedrock_kb_retrieval_mcp_server.server.discover_knowledge_bases")
    async def test_handle_message_knowledgebases(self, mock_discover_knowledge_bases):
        """Test the handle_message function with resource://knowledgebases method."""
        mock_discover_knowledge_bases.return_value = {
            "kb-12345": {
                "name": "Test Knowledge Base",
                "data_sources": [
                    {"id": "ds-12345", "name": "Test Data Source"},
                ]
            }
        }
        
        result = await handle_message({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "resource://knowledgebases",
            "params": {}
        })
        
        assert result["jsonrpc"] == "2.0"
        assert result["id"] == 1
        assert "kb-12345" in result["result"]
        assert result["result"]["kb-12345"]["name"] == "Test Knowledge Base"
        assert len(result["result"]["kb-12345"]["data_sources"]) == 1
        assert result["result"]["kb-12345"]["data_sources"][0]["id"] == "ds-12345"
        assert result["result"]["kb-12345"]["data_sources"][0]["name"] == "Test Data Source"

    @patch("awslabs.bedrock_kb_retrieval_mcp_server.server.query_knowledge_base")
    async def test_handle_message_query_knowledge_bases(self, mock_query_knowledge_base):
        """Test the handle_message function with QueryKnowledgeBases method."""
        mock_query_knowledge_base.return_value = json.dumps({
            "content": {"text": "This is a test document content.", "type": "TEXT"},
            "location": {"s3Location": {"uri": "s3://test-bucket/test-document.txt"}},
            "score": 0.95,
        })
        
        result = await handle_message({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "QueryKnowledgeBases",
            "params": {
                "query": "test query",
                "knowledge_base_id": "kb-12345",
                "number_of_results": 10,
                "reranking": True,
                "reranking_model_name": "AMAZON",
                "data_source_ids": ["ds-12345", "ds-67890"]
            }
        })
        
        assert result["jsonrpc"] == "2.0"
        assert result["id"] == 1
        assert isinstance(result["result"], str)
        assert "This is a test document content." in result["result"]
        assert "s3://test-bucket/test-document.txt" in result["result"]
        assert "0.95" in result["result"]
        
        mock_query_knowledge_base.assert_called_once_with(
            query="test query",
            knowledge_base_id="kb-12345",
            kb_agent_client=MagicMock(),  # We can't directly access the global variable in tests
            number_of_results=10,
            reranking=True,
            reranking_model_name="AMAZON",
            data_source_ids=["ds-12345", "ds-67890"],
        )

    async def test_handle_message_unknown_method(self):
        """Test the handle_message function with an unknown method."""
        result = await handle_message({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "unknown_method",
            "params": {}
        })
        
        assert result["jsonrpc"] == "2.0"
        assert result["id"] == 1
        assert "error" in result
        assert result["error"]["code"] == -32601
        assert "Method not found: unknown_method" in result["error"]["message"]