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

"""Tests for IAM permissions in the application.yaml file."""

import json
import os
import pytest
import yaml


class TestIAMPermissions:
    """Tests for IAM permissions in the application.yaml file."""

    def test_application_yaml_has_required_permissions(self):
        """Test that the application.yaml file has the required IAM permissions."""
        # Get the path to the application.yaml file
        app_yaml_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'deployment',
            'dev',
            'application.yaml'
        )

        # Check that the file exists
        assert os.path.exists(app_yaml_path), f"application.yaml file not found at {app_yaml_path}"

        # Load the YAML file
        with open(app_yaml_path, 'r') as f:
            app_yaml = yaml.safe_load(f)

        # Check that the file has the expected structure
        assert 'spec' in app_yaml, "application.yaml is missing 'spec' section"
        assert 'components' in app_yaml['spec'], "application.yaml is missing 'components' section"
        assert len(app_yaml['spec']['components']) > 0, "application.yaml has no components"

        # Get the component for the bedrock-kb-retrieval-mcp-server
        component = None
        for comp in app_yaml['spec']['components']:
            if comp.get('name') == 'bedrock-kb-retrieval-mcp-server':
                component = comp
                break

        assert component is not None, "bedrock-kb-retrieval-mcp-server component not found"
        assert 'properties' in component, "Component is missing 'properties' section"
        
        # Check for serviceAccountName
        assert 'serviceAccountName' in component['properties'], "Component is missing 'serviceAccountName'"
        assert component['properties']['serviceAccountName'] == 'bedrock-kb-retrieval-sa', \
            "serviceAccountName should be 'bedrock-kb-retrieval-sa'"
        
        # Check for iamPolicyDocument
        assert 'iamPolicyDocument' in component['properties'], "Component is missing 'iamPolicyDocument'"
        
        # Parse the IAM policy document
        policy_doc = json.loads(component['properties']['iamPolicyDocument'])
        
        # Check that the policy document has the expected structure
        assert 'Version' in policy_doc, "Policy document is missing 'Version'"
        assert 'Statement' in policy_doc, "Policy document is missing 'Statement'"
        assert len(policy_doc['Statement']) > 0, "Policy document has no statements"
        
        # Check for required permissions
        required_permissions = {
            'bedrock': ['ListFoundationModels', 'GetFoundationModel', 'InvokeModel', 'InvokeModelWithResponseStream'],
            'bedrock-agent': ['ListKnowledgeBases', 'GetKnowledgeBase', 'ListDataSources', 'ListTagsForResource', 'RetrieveAndGenerate'],
            'bedrock-agent-runtime': ['Retrieve', 'RetrieveAndGenerate']
        }
        
        # Check each service's permissions
        for service, actions in required_permissions.items():
            # Find the statement for this service
            service_statement = None
            for statement in policy_doc['Statement']:
                if any(action.startswith(f"{service}:") for action in statement.get('Action', [])):
                    service_statement = statement
                    break
            
            assert service_statement is not None, f"No statement found for {service} permissions"
            assert service_statement['Effect'] == 'Allow', f"Statement for {service} should have Effect: Allow"
            
            # Check that all required actions are present
            for action in actions:
                action_name = f"{service}:{action}"
                assert action_name in service_statement['Action'], f"Missing required action: {action_name}"

    def test_application_yaml_has_config_map_trait(self):
        """Test that the application.yaml file has the config-map trait."""
        # Get the path to the application.yaml file
        app_yaml_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'deployment',
            'dev',
            'application.yaml'
        )

        # Load the YAML file
        with open(app_yaml_path, 'r') as f:
            app_yaml = yaml.safe_load(f)

        # Get the component for the bedrock-kb-retrieval-mcp-server
        component = None
        for comp in app_yaml['spec']['components']:
            if comp.get('name') == 'bedrock-kb-retrieval-mcp-server':
                component = comp
                break

        assert component is not None, "bedrock-kb-retrieval-mcp-server component not found"
        assert 'traits' in component, "Component is missing 'traits' section"
        
        # Check for config-map trait
        config_map_trait = None
        for trait in component['traits']:
            if trait.get('type') == 'config-map':
                config_map_trait = trait
                break
        
        assert config_map_trait is not None, "config-map trait not found"
        assert 'properties' in config_map_trait, "config-map trait is missing 'properties' section"
        assert 'name' in config_map_trait['properties'], "config-map trait is missing 'name' property"
        assert config_map_trait['properties']['name'] == 'bedrock-kb-config', "config-map name should be 'bedrock-kb-config'"
        
        # Check for required config data
        assert 'data' in config_map_trait['properties'], "config-map trait is missing 'data' section"
        required_configs = ['aws-region', 'bedrock-kb-reranking-enabled', 'kb-inclusion-tag-key']
        for config in required_configs:
            assert config in config_map_trait['properties']['data'], f"config-map is missing '{config}' data"

    def test_application_yaml_has_env_trait(self):
        """Test that the application.yaml file has the env trait with proper configuration."""
        # Get the path to the application.yaml file
        app_yaml_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'deployment',
            'dev',
            'application.yaml'
        )

        # Load the YAML file
        with open(app_yaml_path, 'r') as f:
            app_yaml = yaml.safe_load(f)

        # Get the component for the bedrock-kb-retrieval-mcp-server
        component = None
        for comp in app_yaml['spec']['components']:
            if comp.get('name') == 'bedrock-kb-retrieval-mcp-server':
                component = comp
                break

        assert component is not None, "bedrock-kb-retrieval-mcp-server component not found"
        assert 'traits' in component, "Component is missing 'traits' section"
        
        # Check for env trait
        env_trait = None
        for trait in component['traits']:
            if trait.get('type') == 'env':
                env_trait = trait
                break
        
        assert env_trait is not None, "env trait not found"
        assert 'properties' in env_trait, "env trait is missing 'properties' section"
        
        # Check for envFrom section
        assert 'envFrom' in env_trait['properties'], "env trait is missing 'envFrom' section"
        assert len(env_trait['properties']['envFrom']) > 0, "env trait has no envFrom items"
        assert 'configMapRef' in env_trait['properties']['envFrom'][0], "envFrom is missing 'configMapRef'"
        assert 'name' in env_trait['properties']['envFrom'][0]['configMapRef'], "configMapRef is missing 'name'"
        assert env_trait['properties']['envFrom'][0]['configMapRef']['name'] == 'bedrock-kb-config', \
            "configMapRef name should be 'bedrock-kb-config'"
        
        # Check for env section
        assert 'env' in env_trait['properties'], "env trait is missing 'env' section"
        required_env_vars = ['AWS_REGION', 'BEDROCK_KB_RERANKING_ENABLED', 'KB_INCLUSION_TAG_KEY']
        for env_var in required_env_vars:
            env_var_found = False
            for env_item in env_trait['properties']['env']:
                if env_item.get('name') == env_var:
                    env_var_found = True
                    assert 'valueFrom' in env_item, f"env var '{env_var}' is missing 'valueFrom'"
                    assert 'configMapKeyRef' in env_item['valueFrom'], f"env var '{env_var}' is missing 'configMapKeyRef'"
                    assert 'name' in env_item['valueFrom']['configMapKeyRef'], f"configMapKeyRef for '{env_var}' is missing 'name'"
                    assert env_item['valueFrom']['configMapKeyRef']['name'] == 'bedrock-kb-config', \
                        f"configMapKeyRef name for '{env_var}' should be 'bedrock-kb-config'"
                    break
            assert env_var_found, f"Required environment variable '{env_var}' not found"