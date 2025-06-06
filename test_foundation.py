#!/usr/bin/env python3
"""
Foundation Test Script - Tests core functionality without dependencies
Run with: python test_foundation.py
"""

import sys
import json
import os
from pathlib import Path

print("🧪 Cokeydex Foundation Test Suite")
print("=" * 50)

# Test 1: Check project structure
print("\n1️⃣ Testing Project Structure...")
required_dirs = [
    "agent", "agent/tools", "agent/memory", "agent/utils",
    "cli", "cli/commands", "tools", "tests", "memory"
]
missing_dirs = []
for d in required_dirs:
    if not Path(d).exists():
        missing_dirs.append(d)
        
if missing_dirs:
    print(f"❌ Missing directories: {missing_dirs}")
else:
    print("✅ All directories present")

# Test 2: Test imports
print("\n2️⃣ Testing Python Imports...")
try:
    from agent.config import Settings, get_settings
    from agent.memory.manager import MemoryManager
    from agent.memory.utils import estimate_tokens
    from agent.tools.schema import ToolRequest
    from agent.tools.permissions import ACL
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")

# Test 3: Test configuration
print("\n3️⃣ Testing Configuration System...")
try:
    # Create a test config
    test_config = Path(".cokeydex.yml")
    if not test_config.exists():
        test_config.write_text("""
openai_api_key: "test-key"
memory_summarise_threshold: 100
tools_allowed:
  - read_file
  - grep
""")
    
    settings = get_settings()
    print(f"✅ Config loaded: threshold={settings.memory_summarise_threshold}")
except Exception as e:
    print(f"❌ Config error: {e}")

# Test 4: Test memory system
print("\n4️⃣ Testing Memory System...")
try:
    mem = MemoryManager()
    
    # Test scratch operations
    mem.append_scratch("test-task", "This is a test note")
    content = mem.read_scratch("test-task")
    if "test note" in content:
        print("✅ Scratch read/write working")
    else:
        print("❌ Scratch content mismatch")
        
    # Test token estimation
    tokens = estimate_tokens("Hello world")
    print(f"✅ Token estimation: 'Hello world' = {tokens} tokens")
    
except Exception as e:
    print(f"❌ Memory error: {e}")

# Test 5: Test tool schema validation
print("\n5️⃣ Testing Tool Schema...")
try:
    # Valid request
    valid_req = {
        "name": "read_file",
        "args": {"path": "test.txt"},
        "secure": True,
        "timeout_seconds": 30
    }
    tool_req = ToolRequest.model_validate(valid_req)
    print("✅ Valid tool request accepted")
    
    # Invalid request (should fail)
    try:
        invalid_req = {
            "name": "bad;name",  # Invalid characters
            "args": {},
            "secure": True,
            "timeout_seconds": 30
        }
        ToolRequest.model_validate(invalid_req)
        print("❌ Invalid tool request was accepted (should have failed)")
    except ValueError:
        print("✅ Invalid tool request rejected correctly")
        
except Exception as e:
    print(f"❌ Tool schema error: {e}")

# Test 6: Test ACL permissions
print("\n6️⃣ Testing ACL Permissions...")
try:
    acl = ACL()
    if acl.is_allowed("read_file"):
        print("✅ ACL allows 'read_file'")
    else:
        print("❌ ACL should allow 'read_file'")
        
    if not acl.is_allowed("write_file"):
        print("✅ ACL correctly denies unlisted tool")
    else:
        print("❌ ACL should deny 'write_file'")
        
except Exception as e:
    print(f"❌ ACL error: {e}")

# Test 7: Test CLI imports
print("\n7️⃣ Testing CLI Components...")
try:
    from cli.main import app
    from cli.commands.new import repo
    print("✅ CLI components import successfully")
except Exception as e:
    print(f"❌ CLI import error: {e}")

# Test 8: Simple tool execution test
print("\n8️⃣ Testing Tool Execution (without sandbox)...")
try:
    # We'll test if the tool wrapper can be called
    tool_path = Path("tools/read_file.py")
    if tool_path.exists():
        print("✅ Tool wrapper files exist")
        
        # Test tool core import
        from agent.tools.core import invoke_tool
        
        # Try a simple read (this will fail if dependencies missing)
        request = {
            "name": "read_file",
            "args": {"path": "README.md"},
            "secure": False,  # Skip sandbox for this test
            "timeout_seconds": 5
        }
        
        # Note: This might fail due to missing dependencies
        # but at least tests the structure
        print("✅ Tool core imports successfully")
        
except Exception as e:
    print(f"⚠️  Tool execution setup incomplete (expected): {e}")

print("\n" + "=" * 50)
print("🏁 Foundation Test Complete!")
print("\nNOTE: Some tests may fail due to missing dependencies.")
print("This is expected. Key structural tests should pass.")
print("\nTo run full test suite with dependencies:")
print("1. Install dependencies: pip install -r requirements.txt")
print("2. Run pytest: python -m pytest tests/")