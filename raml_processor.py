import yaml
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import re
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

@dataclass
class ApiExample:
    request: Dict
    response: Dict
    description: str

@dataclass
class ValidationRule:
    type: str
    pattern: str
    description: str
    example: str

class ExampleGenerator:
    """Generates realistic examples for each API endpoint"""
    
    def __init__(self):
        self.example_values = {
            'ip': '192.168.88.1',
            'ipv6': '2001:db8::1',
            'interface': 'ether1',
            'mac': '00:0C:29:45:67:89',
            'string': 'example_value',
            'number': 1,
            'boolean': True,
            'comment': 'Example comment',
            'username': 'admin',
            'password': 'password123',
            'port': 8080,
            'vlan': 100,
        }

    def generate_example_for_endpoint(self, endpoint_path: str, method: str, params: Dict) -> ApiExample:
        """Generate example request/response for an endpoint"""
        
        # Generate request body based on parameters
        request_body = {}
        for param_name, param_info in params.items():
            param_type = param_info.get('type', 'string')
            request_body[param_name] = self.get_example_value(param_type, param_name)

        # Generate appropriate response based on method
        if method.lower() == 'get':
            response_body = {"items": [request_body]}
        elif method.lower() == 'post':
            response_body = {"result": "success", "ret": "done"}
        else:
            response_body = {"status": "success"}

        example = ApiExample(
            request={
                "method": method,
                "path": endpoint_path,
                "body": request_body
            },
            response={
                "status": 200,
                "body": response_body
            },
            description=f"Example {method} request to {endpoint_path}"
        )

        return example

    def get_example_value(self, param_type: str, param_name: str) -> Any:
        """Get example value based on parameter type and name"""
        
        # Check if we have a specific example for this parameter name
        for key in self.example_values:
            if key in param_name.lower():
                return self.example_values[key]

        # Default to type-based examples
        return self.example_values.get(param_type, 'example_value')

class ApiDocGenerator:
    def __init__(self):
        self.validation_rules = {
            "ip": ValidationRule(
                type="ip",
                pattern=r"^(\d{1,3}\.){3}\d{1,3}(/\d{1,2})?$",
                description="IPv4 address with optional CIDR",
                example="192.168.88.1"
            ),
            "mac": ValidationRule(
                type="mac",
                pattern=r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$",
                description="MAC address in XX:XX:XX:XX:XX:XX format",
                example="00:0C:29:45:67:89"
            ),
            "interface": ValidationRule(
                type="interface",
                pattern=r"^[a-zA-Z0-9-_]+$",
                description="Interface name",
                example="ether1"
            )
        }
        self.example_generator = ExampleGenerator()

    def generate_markdown(self, endpoint_data: Dict, path: str) -> str:
        """Generate markdown documentation for endpoint"""
        md = [
            f"# {path} API Documentation\n",
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        ]

        if 'description' in endpoint_data:
            md.extend([
                "## Description\n",
                f"{endpoint_data['description']}\n"
            ])

        md.append("## Endpoints\n")

        for method, details in endpoint_data.get('endpoints', {}).items():
            md.extend([
                f"### {method.upper()}\n",
                "#### Parameters\n",
                "| Name | Type | Required | Description |\n",
                "|------|------|----------|-------------|\n"
            ])

            # Add parameters
            if 'parameters' in details:
                for param, param_details in details['parameters'].items():
                    required = "Yes" if param_details.get('required', False) else "No"
                    desc = param_details.get('description', '')
                    md.append(f"| {param} | {param_details.get('type', '')} | {required} | {desc} |\n")

            # Add examples
            if 'examples' in details:
                md.extend([
                    "\n#### Examples\n",
                    "```json\n",
                    json.dumps(details['examples'], indent=2),
                    "\n```\n"
                ])

            # Add validation rules if any
            if 'validation' in details:
                md.extend([
                    "\n#### Validation Rules\n",
                    "```json\n",
                    json.dumps(details['validation'], indent=2),
                    "\n```\n"
                ])

        return ''.join(md)

class EnhancedRamlSplitter:
    def __init__(self, output_dir: str = "api"):
        self.output_dir = output_dir
        self.base_path = Path(output_dir)
        self.doc_generator = ApiDocGenerator()
        
    def process_raml(self, input_file: str):
        """Main method to process RAML file"""
        try:
            logging.info(f"Processing RAML file: {input_file}")
            
            # Create directory structure
            self.create_directory_structure()
            
            # Load and split RAML
            raml_content = self.load_raml(input_file)
            self.split_raml(raml_content)
            
            # Generate index and relationships
            self.generate_index()
            
            logging.info(f"Processing complete! Documentation available at {self.base_path}/README.md")
            
        except Exception as e:
            logging.error(f"Error processing RAML: {str(e)}")
            raise

    def create_directory_structure(self):
        """Create necessary directories"""
        dirs = [
            self.base_path,
            self.base_path / 'docs',
            self.base_path / 'examples'
        ]
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
            logging.info(f"Created directory: {dir_path}")

    def load_raml(self, file_path: str) -> Dict:
        """Load RAML file"""
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)

    def split_raml(self, raml_content: Dict):
        """Split RAML into separate files"""
        for family, endpoints in raml_content.items():
            if family.startswith('/'):
                family_dir = self.create_family_directory(family.strip('/'))
                self.process_family(family, endpoints, family_dir)

    def process_family(self, family: str, endpoints: Dict, family_dir: Path):
        """Process a family of endpoints"""
        logging.info(f"Processing family: {family}")
        
        # Create family index
        family_index = {
            "family": family,
            "endpoints": [],
            "examples": []
        }

        # Process each endpoint
        for endpoint, data in endpoints.items():
            if isinstance(data, dict):
                processed_endpoint = self.process_endpoint(endpoint, data, family_dir)
                family_index["endpoints"].append(processed_endpoint)

        # Write family index
        with open(family_dir / '_index.json', 'w') as f:
            json.dump(family_index, f, indent=2)

    def process_endpoint(self, endpoint: str, data: Dict, family_dir: Path) -> Dict:
        """Process single endpoint"""
        logging.info(f"Processing endpoint: {endpoint}")
        
        # Generate examples
        examples = self.doc_generator.example_generator.generate_example_for_endpoint(
            endpoint, 
            data.get('method', 'GET'),
            data.get('parameters', {})
        )

        # Enhance endpoint data
        enhanced_data = {
            "endpoint": endpoint,
            "data": data,
            "examples": examples.__dict__,
            "validation": self.get_validation_rules(data)
        }

        # Write endpoint file
        endpoint_file = family_dir / f"{endpoint.strip('/')}.json"
        with open(endpoint_file, 'w') as f:
            json.dump(enhanced_data, f, indent=2)

        # Generate documentation
        doc_file = family_dir / 'docs' / f"{endpoint.strip('/')}.md"
        doc_content = self.doc_generator.generate_markdown(enhanced_data, endpoint)
        with open(doc_file, 'w') as f:
            f.write(doc_content)

        return enhanced_data

    def get_validation_rules(self, data: Dict) -> Dict:
        """Get validation rules for endpoint parameters"""
        rules = {}
        for param, details in data.get('parameters', {}).items():
            param_type = details.get('type', 'string')
            if param_type in self.doc_generator.validation_rules:
                rules[param] = self.doc_generator.validation_rules[param_type].__dict__
        return rules

    def create_family_directory(self, family: str) -> Path:
        """Create and return family directory"""
        family_dir = self.base_path / family
        family_dir.mkdir(parents=True, exist_ok=True)
        (family_dir / 'docs').mkdir(exist_ok=True)
        return family_dir

    def generate_index(self):
        """Generate main index file"""
        index = {
            "generated_at": datetime.now().isoformat(),
            "families": []
        }

        # Collect all families
        for family_dir in self.base_path.glob('*/'):
            if family_dir.is_dir() and not family_dir.name.startswith('.'):
                index_file = family_dir / '_index.json'
                if index_file.exists():
                    with open(index_file) as f:
                        family_data = json.load(f)
                        index["families"].append(family_data)

        # Write main index
        with open(self.base_path / 'index.json', 'w') as f:
            json.dump(index, f, indent=2)

def main():
    # Define paths
    raml_path = Path("/Users/vivek/Documents/mkdocs/schema.raml")
    output_dir = Path("api")

    if not raml_path.exists():
        logging.error(f"RAML file not found: {raml_path}")
        return

    try:
        processor = EnhancedRamlSplitter(output_dir=str(output_dir))
        processor.process_raml(str(raml_path))
        
    except Exception as e:
        logging.error(f"Failed to process RAML: {e}")
        raise

if __name__ == "__main__":
    main()