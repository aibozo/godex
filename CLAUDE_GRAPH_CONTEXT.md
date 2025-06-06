# Codebase Graph Intelligence

This codebase has been analyzed with claude-code-graph for intelligent navigation.

**Compression**: 49 files → 5 clusters (10:1)

## Cluster Overview

The codebase is organized into these semantic clusters:

### c0: ., cli modules (py) - cli, main, agent
- **Files**: 35 | **Languages**: py
- **Key Files**: cli/main.py, agent/retrieval/bm25_index.py, cli/__main__.py
- **Importance**: 13

### misc: Miscellaneous files (py)
- **Files**: 10 | **Languages**: py
- **Key Files**: setup.py, tools/read_file.py, tools/grep.py
- **Importance**: 3

### c1: ., agent modules (py) - agent, utils, cli
- **Files**: 2 | **Languages**: py
- **Key Files**: agent/utils/fs.py, cli/commands/new.py
- **Importance**: 3

### c2: ., agent modules (py) - agent, models, registry
- **Files**: 1 | **Languages**: py
- **Key Files**: agent/models/registry.py
- **Importance**: 0

### c3: ., tests modules (py) - tests, cli
- **Files**: 1 | **Languages**: py
- **Key Files**: tests/test_cli.py
- **Importance**: 0

## Navigation Commands

Use these commands to navigate efficiently:

- `/clusters` - Show all clusters
- `/cluster <id>` - Expand specific cluster
- `/csearch <query>` - Search clusters
- `/cfile <path>` - Get detailed file info

## Usage

Instead of scanning thousands of files, use the cluster overview to understand the codebase architecture, then drill down to specific areas using the navigation commands.
