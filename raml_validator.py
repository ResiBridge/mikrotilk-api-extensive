import json
import yaml
import os
from pathlib import Path
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

class RamlValidator:
    def __init__(self, api_dir: str = "api"):
        self.api_dir = Path(api_dir)
        self.errors = []
        self.warnings = []
        
    def validate_all(self) -> bool:
        """Run all validations"""
        logging.info("Starting validation...")
        
        # Structure validations
        self.validate_directory_structure()
        self.validate_index_files()
        
        # Content validations
        self.validate_json_files()
        self.validate_markdown_files()
        self.validate_examples()
        
        # Cross-reference validations
        self.validate_references()
        
        # Report results
        self.report_results()
        
        return len(self.errors) == 0

    def validate_directory_structure(self):
        """Validate basic directory structure"""
        required_dirs = ['docs', 'examples']
        for dir_name in required_dirs:
            if not (self.api_dir / dir_name).exists():
                self.errors.append(f"Missing required directory: {dir_name}")

        # Check each family directory
        for family_dir in self.api_dir.glob('*/'):
            if family_dir.is_dir() and not family_dir.name.startswith('.'):
                if not (family_dir / 'docs').exists():
                    self.errors.append(f"Missing docs directory in {family_dir.name}")
                if not (family_dir / '_index.json').exists():
                    self.errors.append(f"Missing _index.json in {family_dir.name}")

    def validate_json_files(self):
        """Validate all JSON files"""
        for json_file in self.api_dir.rglob('*.json'):
            try:
                with open(json_file) as f:
                    data = json.load(f)
                
                # Validate required fields based on file type
                if json_file.name == '_index.json':
                    self._validate_index_file(data, json_file)
                elif json_file.name.endswith('.json'):
                    self._validate_endpoint_file(data, json_file)
                    
            except json.JSONDecodeError as e:
                self.errors.append(f"Invalid JSON in {json_file}: {str(e)}")
            except Exception as e:
                self.errors.append(f"Error processing {json_file}: {str(e)}")

    def _validate_index_file(self, data: Dict, file_path: Path):
        """Validate index file structure"""
        required_fields = ['family', 'endpoints']
        for field in required_fields:
            if field not in data:
                self.errors.append(f"Missing required field '{field}' in {file_path}")

    def _validate_endpoint_file(self, data: Dict, file_path: Path):
        """Validate endpoint file structure"""
        required_fields = ['endpoint', 'data']
        for field in required_fields:
            if field not in data:
                self.errors.append(f"Missing required field '{field}' in {file_path}")
                
        # Validate examples if present
        if 'examples' in data:
            self._validate_examples(data['examples'], file_path)

    def validate_markdown_files(self):
        """Validate markdown documentation files"""
        for md_file in self.api_dir.rglob('*.md'):
            try:
                content = md_file.read_text()
                
                # Check for required sections
                required_sections = ['# ', '## Description', '## Endpoints']
                for section in required_sections:
                    if section not in content:
                        self.warnings.append(f"Missing section '{section}' in {md_file}")
                        
            except Exception as e:
                self.errors.append(f"Error reading markdown file {md_file}: {str(e)}")

    def validate_examples(self):
        """Validate example files and data"""
        for json_file in (self.api_dir / 'examples').glob('*.json'):
            try:
                with open(json_file) as f:
                    data = json.load(f)
                    
                # Validate example structure
                required_fields = ['request', 'response']
                for field in required_fields:
                    if field not in data:
                        self.errors.append(f"Missing required field '{field}' in example {json_file}")
                        
            except Exception as e:
                self.errors.append(f"Error validating example {json_file}: {str(e)}")

    def validate_references(self):
        """Validate cross-references between files"""
        # Load main index
        try:
            with open(self.api_dir / 'index.json') as f:
                main_index = json.load(f)
                
            # Check each family referenced exists
            for family in main_index.get('families', []):
                family_dir = self.api_dir / family
                if not family_dir.exists():
                    self.errors.append(f"Referenced family directory does not exist: {family}")
                    
        except Exception as e:
            self.errors.append(f"Error validating cross-references: {str(e)}")

    def validate_index_files(self):
        """Validate main index and family indexes"""
        # Validate main index
        main_index_path = self.api_dir / 'index.json'
        if not main_index_path.exists():
            self.errors.append("Missing main index.json")
        else:
            try:
                with open(main_index_path) as f:
                    data = json.load(f)
                    if 'families' not in data:
                        self.errors.append("Missing 'families' in main index.json")
            except Exception as e:
                self.errors.append(f"Error validating main index.json: {str(e)}")

    def report_results(self):
        """Print validation results"""
        print("\n=== Validation Results ===")
        
        if self.errors:
            print("\nErrors:")
            for error in self.errors:
                print(f"❌ {error}")
                
        if self.warnings:
            print("\nWarnings:")
            for warning in self.warnings:
                print(f"⚠️  {warning}")
                
        if not self.errors and not self.warnings:
            print("\n✅ All validations passed successfully!")
        
        print(f"\nTotal: {len(self.errors)} errors, {len(self.warnings)} warnings")

def main():
    validator = RamlValidator()
    validator.validate_all()

if __name__ == "__main__":
    main()