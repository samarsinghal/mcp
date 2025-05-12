# Amazon Bedrock Knowledge Base Retrieval MCP Server

MCP server for accessing Amazon Bedrock Knowledge Bases

## Features

### Discover knowledge bases and their data sources

- Find and explore all available knowledge bases
- Search for knowledge bases by name or tag
- List data sources associated with each knowledge base

### Query knowledge bases with natural language

- Retrieve information using conversational queries
- Get relevant passages from your knowledge bases
- Access citation information for all results

### Filter results by data source

- Focus your queries on specific data sources
- Include or exclude specific data sources
- Prioritize results from specific data sources

### Rerank results

- Improve relevance of retrieval results
- Use Amazon Bedrock reranking capabilities
- Sort results by relevance to your query

## Prerequisites

### Installation Requirements

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`

### AWS Requirements

1. **AWS CLI Configuration**: You must have the AWS CLI configured with credentials and an AWS_PROFILE that has access to Amazon Bedrock and Knowledge Bases
2. **Amazon Bedrock Knowledge Base**: You must have at least one Amazon Bedrock Knowledge Base with the tag key `mcp-multirag-kb` with a value of `true`
3. **IAM Permissions**: Your IAM role/user must have appropriate permissions to:
   - List and describe knowledge bases
   - Access data sources
   - Query knowledge bases

#### Required IAM Permissions

The following IAM permissions are required for the MCP server to function properly:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:ListFoundationModels",
        "bedrock:GetFoundationModel",
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agent:ListKnowledgeBases",
        "bedrock-agent:GetKnowledgeBase",
        "bedrock-agent:ListDataSources",
        "bedrock-agent:ListTagsForResource",
        "bedrock-agent:RetrieveAndGenerate"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agent-runtime:Retrieve",
        "bedrock-agent-runtime:RetrieveAndGenerate"
      ],
      "Resource": "*"
    }
  ]
}
```

These permissions are automatically configured in the `application.yaml` file when deploying the MCP server.

### Reranking Requirements

If you intend to use reranking functionality, your Bedrock Knowledge Base needs additional permissions:

1. Your IAM role must have permissions for both `bedrock:Rerank` and `bedrock:InvokeModel` actions
2. The Amazon Bedrock Knowledge Bases service role must also have these permissions
3. Reranking is only available in specific regions. Please refer to the official [documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/rerank-supported.html) for an up to date list of supported regions.
4. Enable model access for the available reranking models in the specified region.

### Controlling Reranking

Reranking can be globally enabled or disabled using the `BEDROCK_KB_RERANKING_ENABLED` environment variable:

- Set to `false` (default): Disables reranking for all queries unless explicitly enabled
- Set to `true`: Enables reranking for all queries unless explicitly disabled

The environment variable accepts various formats:

- For enabling: 'true', '1', 'yes', or 'on' (case-insensitive)
- For disabling: any other value or not set (default behavior)

This setting provides a global default, while individual API calls can still override it by explicitly setting the `reranking` parameter.

For detailed instructions on setting up knowledge bases, see:

- [Create a knowledge base](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-create.html)
- [Managing permissions for Amazon Bedrock knowledge bases](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-prereq-permissions-general.html)
- [Permissions for reranking in Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/rerank-prereq.html)

## Installation

### Using with Amazon Q CLI

This MCP server can be used with Amazon Q CLI by configuring it in your `~/.aws/amazonq/mcp.json` file:

```json
{
  "mcpServers": {
    "bedrock-kb-retrieval": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://your-server-endpoint/bedrock-kb-retrieval",
        "--allow-http",
        "--transport",
        "http-only"
      ],
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

Replace `http://your-server-endpoint/bedrock-kb-retrieval` with the actual endpoint of your deployed MCP server.

### Local Installation

Here are some ways you can work with MCP across AWS:

```json
{
  "mcpServers": {
    "awslabs.bedrock-kb-retrieval-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.bedrock-kb-retrieval-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-profile-name",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR",
        "KB_INCLUSION_TAG_KEY": "optional-tag-key-to-filter-kbs",
        "BEDROCK_KB_RERANKING_ENABLED": "false"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

or docker after a succesful `docker build -t awslabs/bedrock-kb-retrieval-mcp-server .`:

```file
# ficticious `.env` file with AWS temporary credentials
AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_SESSION_TOKEN=AQoEXAMPLEH4aoAH0gNCAPy...truncated...zrkuWJOgQs8IZZaIv2BXIa2R4Olgk
```

```json
  {
    "mcpServers": {
      "awslabs.bedrock-kb-retrieval-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "--interactive",
          "--env",
          "FASTMCP_LOG_LEVEL=ERROR",
          "--env",
          "KB_INCLUSION_TAG_KEY=optional-tag-key-to-filter-kbs",
          "--env",
          "BEDROCK_KB_RERANKING_ENABLED=false",
          "--env",
          "AWS_REGION=us-east-1",
          "--env-file",
          "/full/path/to/file/above/.env",
          "awslabs/bedrock-kb-retrieval-mcp-server:latest"
        ],
        "env": {},
        "disabled": false,
        "autoApprove": []
      }
    }
  }
```

NOTE: Your credentials will need to be kept refreshed from your host

## Deployment

When deploying the MCP server using the provided `application.yaml` file, the following configurations are automatically applied:

1. **Service Account**: A dedicated service account named `bedrock-kb-retrieval-sa` is created for the MCP server.
2. **IAM Permissions**: The necessary IAM permissions for accessing Amazon Bedrock Knowledge Base are automatically attached to the service account.
3. **Configuration**: The server uses a ConfigMap named `bedrock-kb-config` for configuration, which includes:
   - `aws-region`: Set to `us-west-2` by default
   - `bedrock-kb-reranking-enabled`: Controls whether reranking is enabled
   - `kb-inclusion-tag-key`: Defines the tag key used to filter knowledge bases

This configuration approach is compatible with OAM and KubeVela, providing a more robust way to manage configuration compared to environment variables.

You can customize these settings by modifying the `application.yaml` file in the `deployment/dev` directory.

## HTTP Server Implementation

This MCP server implements the Model Context Protocol (MCP) over HTTP and Server-Sent Events (SSE) as described in the [AWS Community article](https://community.aws/content/2eeJZdwNQoUbT4ndQqEmdQveIMT/ai-powered-database-intelligence-remote-mcp-server-for-amazon-q-cli). The server provides the following endpoints:

- `GET /`: Health check endpoint
- `POST /`: Health check endpoint
- `GET /sse`: SSE endpoint for establishing a connection
- `POST /sse`: SSE endpoint for establishing a connection
- `POST /messages/`: JSON-RPC endpoint for handling messages

The server supports the following JSON-RPC methods:

- `initialize`: Initialize the MCP server
- `shutdown`: Shutdown the MCP server
- `resource://knowledgebases`: Discover knowledge bases
- `QueryKnowledgeBases`: Query knowledge bases

## Limitations

- Results with `IMAGE` content type are not included in the KB query response.
- The `reranking` parameter requires additional permissions, Amazon Bedrock model access, and is only available in specific regions.