#!/bin/bash
exec npx mcp-remote http://modernengg-dev-4c1347b0bd2e4e80.elb.us-west-2.amazonaws.com/bedrock-kb-retrieval/sse --allow-http --transport sse-only --debug
