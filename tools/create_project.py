#!/usr/bin/env python3
# tools/create_project.py

import sys
import json
import os
from pathlib import Path
from typing import Dict, Any


def main():
    if len(sys.argv) != 2:
        err = {"exit_code": 1, "stdout": "", "stderr": "Expected exactly one JSON arg"}
        print(json.dumps(err))
        sys.exit(1)

    try:
        args = json.loads(sys.argv[1])
        project_type = args.get("project_type", "")
        project_name = args.get("project_name", "")
        project_path = args.get("project_path", ".")
        
        if not project_name:
            raise ValueError("Missing 'project_name'")
        
        result = create_project_structure(project_type, project_name, project_path)
        resp = {"exit_code": 0, "stdout": json.dumps(result), "stderr": ""}
        
    except Exception as e:
        resp = {"exit_code": 1, "stdout": "", "stderr": str(e)}

    print(json.dumps(resp))
    sys.exit(resp["exit_code"])


def create_project_structure(project_type: str, project_name: str, project_path: str) -> Dict[str, Any]:
    """
    Create basic project structure based on project type.
    
    Returns information about what was created.
    """
    base_path = Path(project_path) / project_name
    base_path.mkdir(parents=True, exist_ok=True)
    
    created_files = []
    created_dirs = []
    
    if project_type.lower() in ["python", "py"]:
        # Python project structure
        dirs_to_create = [
            "src",
            "tests", 
            "docs",
            ".github/workflows"
        ]
        
        files_to_create = {
            "README.md": f"# {project_name}\n\nA Python project.\n",
            "requirements.txt": "# Add your dependencies here\n",
            "pyproject.toml": generate_pyproject_toml(project_name),
            ".gitignore": generate_python_gitignore(),
            "src/__init__.py": "",
            "tests/__init__.py": "",
            "tests/test_basic.py": generate_basic_test(project_name)
        }
        
    elif project_type.lower() in ["javascript", "js", "node"]:
        # JavaScript/Node project structure
        dirs_to_create = [
            "src",
            "tests",
            "docs"
        ]
        
        files_to_create = {
            "README.md": f"# {project_name}\n\nA JavaScript project.\n",
            "package.json": generate_package_json(project_name),
            ".gitignore": generate_js_gitignore(),
            "src/index.js": f"// {project_name} main entry point\nconsole.log('Hello from {project_name}!');\n",
            "tests/basic.test.js": generate_basic_js_test(project_name)
        }
        
    else:
        # Generic project structure
        dirs_to_create = [
            "src",
            "docs"
        ]
        
        files_to_create = {
            "README.md": f"# {project_name}\n\nProject description goes here.\n",
            ".gitignore": "# Add files to ignore here\n"
        }
    
    # Create directories
    for dir_name in dirs_to_create:
        dir_path = base_path / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)
        created_dirs.append(str(dir_path))
    
    # Create files
    for file_name, content in files_to_create.items():
        file_path = base_path / file_name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        created_files.append(str(file_path))
    
    return {
        "project_name": project_name,
        "project_type": project_type,
        "project_path": str(base_path),
        "created_files": created_files,
        "created_dirs": created_dirs,
        "status": "success"
    }


def generate_pyproject_toml(project_name: str) -> str:
    return f'''[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{project_name}"
version = "0.1.0"
description = "A Python project"
authors = [
    {{name = "Your Name", email = "your.email@example.com"}},
]
dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=6.0",
    "black",
    "isort",
    "flake8"
]

[tool.black]
line-length = 88
target-version = ['py38']

[tool.isort]
profile = "black"
'''


def generate_python_gitignore() -> str:
    return '''# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# PyInstaller
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
.hypothesis/
.pytest_cache/

# Virtual environments
venv/
env/
ENV/

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
'''


def generate_basic_test(project_name: str) -> str:
    return f'''import pytest


def test_basic():
    """Basic test to ensure testing framework works."""
    assert True


def test_{project_name.lower().replace('-', '_')}_exists():
    """Test that the project module can be imported."""
    # This will fail until you create actual source files
    # import {project_name.lower().replace('-', '_')}
    pass
'''


def generate_package_json(project_name: str) -> str:
    return f'''{{
  "name": "{project_name}",
  "version": "0.1.0",
  "description": "A JavaScript project",
  "main": "src/index.js",
  "scripts": {{
    "start": "node src/index.js",
    "test": "jest",
    "lint": "eslint src/"
  }},
  "keywords": [],
  "author": "Your Name",
  "license": "MIT",
  "devDependencies": {{
    "jest": "^29.0.0",
    "eslint": "^8.0.0"
  }}
}}
'''


def generate_js_gitignore() -> str:
    return '''# Dependencies
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Runtime data
pids
*.pid
*.seed
*.pid.lock

# Coverage directory used by tools like istanbul
coverage/

# Logs
logs
*.log

# Runtime data
pids
*.pid
*.seed

# Directory for instrumented libs generated by jscoverage/JSCover
lib-cov

# Coverage directory used by tools like istanbul
coverage

# Grunt intermediate storage
.grunt

# Dependency directories
node_modules/

# Optional npm cache directory
.npm

# Optional REPL history
.node_repl_history

# Output of 'npm pack'
*.tgz

# Yarn Integrity file
.yarn-integrity

# Environment variables
.env

# IDEs
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
'''


def generate_basic_js_test(project_name: str) -> str:
    return f'''// Basic test for {project_name}

describe('{project_name}', () => {{
  test('should be defined', () => {{
    expect(true).toBe(true);
  }});
  
  test('basic functionality', () => {{
    // Add your tests here
    expect(1 + 1).toBe(2);
  }});
}});
'''


if __name__ == "__main__":
    main()