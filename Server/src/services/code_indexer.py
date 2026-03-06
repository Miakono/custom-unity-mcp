"""
Local Code Intelligence - C# Code Indexing Service

This module provides local code indexing and search capabilities for Unity C# projects
WITHOUT requiring Unity to be running. It uses file system operations only.

Features:
- Parse C# files to extract symbols (classes, methods, properties, fields)
- Build and maintain a searchable index of the codebase
- Support incremental updates
- Cache index in JSON for persistence
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("mcp-for-unity-server")


@dataclass
class Symbol:
    """Represents a C# symbol (class, method, property, field, etc.)."""
    name: str
    type: str  # 'class', 'interface', 'struct', 'enum', 'method', 'property', 'field', 'event', 'delegate'
    file_path: str
    line_number: int
    column: int = 0
    end_line: int = 0
    namespace: str = ""
    parent: str = ""  # Parent class/struct name for nested symbols
    modifiers: list[str] = field(default_factory=list)  # public, private, static, etc.
    return_type: str = ""  # For methods, properties, fields
    parameters: list[dict[str, str]] = field(default_factory=list)  # For methods
    attributes: list[str] = field(default_factory=list)  # [SerializeField], etc.
    summary: str = ""  # XML documentation summary
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Symbol:
        return cls(**data)


@dataclass
class FileIndex:
    """Index data for a single file."""
    file_path: str
    file_hash: str
    last_modified: float
    symbols: list[Symbol] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "file_hash": self.file_hash,
            "last_modified": self.last_modified,
            "symbols": [s.to_dict() for s in self.symbols]
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FileIndex:
        return cls(
            file_path=data["file_path"],
            file_hash=data["file_hash"],
            last_modified=data["last_modified"],
            symbols=[Symbol.from_dict(s) for s in data.get("symbols", [])]
        )


@dataclass
class CodeIndex:
    """Complete codebase index."""
    version: str = "1.0"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    project_root: str = ""
    files: dict[str, FileIndex] = field(default_factory=dict)  # file_path -> FileIndex
    
    # Lookup tables for fast searching
    symbol_by_name: dict[str, list[str]] = field(default_factory=dict)  # name -> [file_paths]
    symbol_by_type: dict[str, list[str]] = field(default_factory=dict)  # type -> [file_paths]
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "project_root": self.project_root,
            "files": {k: v.to_dict() for k, v in self.files.items()}
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CodeIndex:
        index = cls(
            version=data.get("version", "1.0"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            project_root=data.get("project_root", "")
        )
        for file_path, file_data in data.get("files", {}).items():
            index.files[file_path] = FileIndex.from_dict(file_data)
        index._rebuild_lookup_tables()
        return index
    
    def _rebuild_lookup_tables(self) -> None:
        """Rebuild symbol lookup tables."""
        self.symbol_by_name.clear()
        self.symbol_by_type.clear()
        for file_path, file_index in self.files.items():
            for symbol in file_index.symbols:
                # Index by name
                if symbol.name not in self.symbol_by_name:
                    self.symbol_by_name[symbol.name] = []
                if file_path not in self.symbol_by_name[symbol.name]:
                    self.symbol_by_name[symbol.name].append(file_path)
                
                # Index by type
                if symbol.type not in self.symbol_by_type:
                    self.symbol_by_type[symbol.type] = []
                if file_path not in self.symbol_by_type[symbol.type]:
                    self.symbol_by_type[symbol.type].append(file_path)


class CSharpParser:
    """Parser for C# source files using regex-based extraction."""
    
    # Regex patterns for C# constructs
    PATTERNS = {
        # XML Documentation comments
        'xml_doc': re.compile(r'///\s*<summary>(.*?)</summary>', re.DOTALL | re.IGNORECASE),
        
        # Attributes
        'attribute': re.compile(r'^\s*\[([^\]]+)\]', re.MULTILINE),
        
        # Namespace
        'namespace': re.compile(r'^\s*namespace\s+([\w.]+)', re.MULTILINE),
        
        # Class declaration (including generic classes)
        'class': re.compile(
            r'^\s*((?:public|private|protected|internal|static|abstract|sealed|partial|\s)*)\s*'
            r'class\s+([\w]+(?:<[^>]+>)?)',
            re.MULTILINE
        ),
        
        # Interface declaration
        'interface': re.compile(
            r'^\s*((?:public|private|protected|internal|partial|\s)*)\s*'
            r'interface\s+([\w]+(?:<[^>]+>)?)',
            re.MULTILINE
        ),
        
        # Struct declaration
        'struct': re.compile(
            r'^\s*((?:public|private|protected|internal|readonly|ref|partial|\s)*)\s*'
            r'struct\s+([\w]+(?:<[^>]+>)?)',
            re.MULTILINE
        ),
        
        # Enum declaration
        'enum': re.compile(
            r'^\s*((?:public|private|protected|internal|\s)*)\s*'
            r'enum\s+([\w]+)',
            re.MULTILINE
        ),
        
        # Method declaration (simplified - may not catch all edge cases)
        'method': re.compile(
            r'^\s*((?:public|private|protected|internal|static|abstract|virtual|override|sealed|async|\s)*)\s*'
            r'([\w<>,\s\[\]]+)\s+'  # return type
            r'([\w]+)\s*'
            r'\(([^)]*)\)\s*',  # parameters
            re.MULTILINE
        ),
        
        # Property declaration
        'property': re.compile(
            r'^\s*((?:public|private|protected|internal|static|virtual|override|abstract|sealed|\s)*)\s*'
            r'([\w<>,\s\[\]]+)\s+'  # type
            r'([\w]+)\s*'
            r'\{\s*(?:get|set)',  # property body
            re.MULTILINE
        ),
        
        # Field declaration
        'field': re.compile(
            r'^\s*((?:public|private|protected|internal|static|readonly|const|volatile|\s)*)\s*'
            r'([\w<>,\s\[\]]+)\s+'  # type
            r'([\w]+)\s*(?:=|;)',  # name
            re.MULTILINE
        ),
        
        # Event declaration
        'event': re.compile(
            r'^\s*((?:public|private|protected|internal|static|virtual|override|abstract|sealed|\s)*)\s*'
            r'event\s+'
            r'([\w<>,\s\[\]]+)\s+'  # delegate type
            r'([\w]+)',  # name
            re.MULTILINE
        ),
        
        # Delegate declaration
        'delegate': re.compile(
            r'^\s*((?:public|private|protected|internal|\s)*)\s*'
            r'delegate\s+'
            r'([\w<>,\s\[\]]+)\s+'  # return type
            r'([\w]+)\s*\(',  # name
            re.MULTILINE
        ),
    }
    
    @classmethod
    def compute_file_hash(cls, file_path: str) -> str:
        """Compute MD5 hash of file contents."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.warning(f"Failed to hash file {file_path}: {e}")
            return ""
    
    @classmethod
    def parse_file(cls, file_path: str) -> FileIndex:
        """Parse a C# file and extract all symbols."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception as e:
            logger.warning(f"Failed to read file {file_path}: {e}")
            return FileIndex(
                file_path=file_path,
                file_hash="",
                last_modified=0,
                symbols=[]
            )
        
        file_hash = cls.compute_file_hash(file_path)
        last_modified = os.path.getmtime(file_path)
        symbols: list[Symbol] = []
        
        # Track current namespace and class context
        current_namespace = ""
        current_class = ""
        
        # Parse namespace
        for match in cls.PATTERNS['namespace'].finditer(content):
            current_namespace = match.group(1).strip()
        
        # Build line number mapping
        line_starts = [0]
        for i, char in enumerate(content):
            if char == '\n':
                line_starts.append(i + 1)
        
        def get_line_col(pos: int) -> tuple[int, int]:
            """Get 1-based line and column from character position."""
            for i, start in enumerate(line_starts):
                if start > pos:
                    line = i
                    col = pos - line_starts[i-1] + 1 if i > 0 else pos + 1
                    return line, col
            line = len(line_starts)
            col = pos - line_starts[-1] + 1 if line_starts else pos + 1
            return line, col
        
        def extract_modifiers(modifier_str: str) -> list[str]:
            """Extract individual modifiers from a string."""
            return [m for m in modifier_str.strip().split() if m]
        
        def parse_parameters(param_str: str) -> list[dict[str, str]]:
            """Parse method parameters."""
            params = []
            if not param_str.strip():
                return params
            
            # Simple parameter parsing - handles basic cases
            # Doesn't handle complex generics well
            for param in param_str.split(','):
                param = param.strip()
                if not param:
                    continue
                parts = param.rsplit(' ', 1)
                if len(parts) == 2:
                    params.append({
                        "type": parts[0].strip(),
                        "name": parts[1].strip()
                    })
                else:
                    params.append({"type": param, "name": ""})
            return params
        
        # Parse classes
        for match in cls.PATTERNS['class'].finditer(content):
            pos = match.start()
            line, col = get_line_col(pos)
            modifiers = extract_modifiers(match.group(1))
            class_name = match.group(2).strip()
            
            symbols.append(Symbol(
                name=class_name,
                type="class",
                file_path=file_path,
                line_number=line,
                column=col,
                namespace=current_namespace,
                modifiers=modifiers
            ))
            current_class = class_name
        
        # Parse interfaces
        for match in cls.PATTERNS['interface'].finditer(content):
            pos = match.start()
            line, col = get_line_col(pos)
            modifiers = extract_modifiers(match.group(1))
            interface_name = match.group(2).strip()
            
            symbols.append(Symbol(
                name=interface_name,
                type="interface",
                file_path=file_path,
                line_number=line,
                column=col,
                namespace=current_namespace,
                modifiers=modifiers
            ))
        
        # Parse structs
        for match in cls.PATTERNS['struct'].finditer(content):
            pos = match.start()
            line, col = get_line_col(pos)
            modifiers = extract_modifiers(match.group(1))
            struct_name = match.group(2).strip()
            
            symbols.append(Symbol(
                name=struct_name,
                type="struct",
                file_path=file_path,
                line_number=line,
                column=col,
                namespace=current_namespace,
                modifiers=modifiers
            ))
        
        # Parse enums
        for match in cls.PATTERNS['enum'].finditer(content):
            pos = match.start()
            line, col = get_line_col(pos)
            modifiers = extract_modifiers(match.group(1))
            enum_name = match.group(2).strip()
            
            symbols.append(Symbol(
                name=enum_name,
                type="enum",
                file_path=file_path,
                line_number=line,
                column=col,
                namespace=current_namespace,
                modifiers=modifiers
            ))
        
        # Parse delegates
        for match in cls.PATTERNS['delegate'].finditer(content):
            pos = match.start()
            line, col = get_line_col(pos)
            modifiers = extract_modifiers(match.group(1))
            return_type = match.group(2).strip()
            delegate_name = match.group(3).strip()
            
            symbols.append(Symbol(
                name=delegate_name,
                type="delegate",
                file_path=file_path,
                line_number=line,
                column=col,
                namespace=current_namespace,
                modifiers=modifiers,
                return_type=return_type
            ))
        
        # Parse methods
        for match in cls.PATTERNS['method'].finditer(content):
            pos = match.start()
            line, col = get_line_col(pos)
            modifiers = extract_modifiers(match.group(1))
            return_type = match.group(2).strip()
            method_name = match.group(3).strip()
            params_str = match.group(4).strip()
            
            # Skip if it looks like a property or event
            if method_name in ['get', 'set', 'add', 'remove']:
                continue
            
            symbols.append(Symbol(
                name=method_name,
                type="method",
                file_path=file_path,
                line_number=line,
                column=col,
                namespace=current_namespace,
                parent=current_class,
                modifiers=modifiers,
                return_type=return_type,
                parameters=parse_parameters(params_str)
            ))
        
        # Parse properties
        for match in cls.PATTERNS['property'].finditer(content):
            pos = match.start()
            line, col = get_line_col(pos)
            modifiers = extract_modifiers(match.group(1))
            prop_type = match.group(2).strip()
            prop_name = match.group(3).strip()
            
            symbols.append(Symbol(
                name=prop_name,
                type="property",
                file_path=file_path,
                line_number=line,
                column=col,
                namespace=current_namespace,
                parent=current_class,
                modifiers=modifiers,
                return_type=prop_type
            ))
        
        # Parse fields
        for match in cls.PATTERNS['field'].finditer(content):
            pos = match.start()
            line, col = get_line_col(pos)
            modifiers = extract_modifiers(match.group(1))
            field_type = match.group(2).strip()
            field_name = match.group(3).strip()
            
            # Skip if it looks like an event or method
            if 'event' in field_type.lower():
                continue
            
            symbols.append(Symbol(
                name=field_name,
                type="field",
                file_path=file_path,
                line_number=line,
                column=col,
                namespace=current_namespace,
                parent=current_class,
                modifiers=modifiers,
                return_type=field_type
            ))
        
        # Parse events
        for match in cls.PATTERNS['event'].finditer(content):
            pos = match.start()
            line, col = get_line_col(pos)
            modifiers = extract_modifiers(match.group(1))
            event_type = match.group(2).strip()
            event_name = match.group(3).strip()
            
            symbols.append(Symbol(
                name=event_name,
                type="event",
                file_path=file_path,
                line_number=line,
                column=col,
                namespace=current_namespace,
                parent=current_class,
                modifiers=modifiers,
                return_type=event_type
            ))
        
        return FileIndex(
            file_path=file_path,
            file_hash=file_hash,
            last_modified=last_modified,
            symbols=symbols
        )


class CodeIndexManager:
    """Manager for building and querying the code index."""
    
    def __init__(self, project_root: str | None = None, cache_dir: str | None = None):
        self.project_root = project_root or os.getcwd()
        self.cache_dir = cache_dir or os.path.expanduser("~/.unity-mcp/code-index")
        self.index: CodeIndex = CodeIndex(project_root=self.project_root)
        self._index_loaded = False
        
        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _get_cache_file_path(self) -> str:
        """Get the path to the cache file for current project."""
        # Use project path hash to create unique cache file
        project_hash = hashlib.md5(self.project_root.encode()).hexdigest()[:12]
        return os.path.join(self.cache_dir, f"index_{project_hash}.json")
    
    def load_index(self) -> bool:
        """Load index from cache file. Returns True if successful."""
        cache_file = self._get_cache_file_path()
        if not os.path.exists(cache_file):
            return False
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.index = CodeIndex.from_dict(data)
            self._index_loaded = True
            logger.info(f"Loaded code index from {cache_file}")
            return True
        except Exception as e:
            logger.warning(f"Failed to load index from cache: {e}")
            return False
    
    def save_index(self) -> bool:
        """Save index to cache file. Returns True if successful."""
        cache_file = self._get_cache_file_path()
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.index.to_dict(), f, indent=2)
            logger.info(f"Saved code index to {cache_file}")
            return True
        except Exception as e:
            logger.warning(f"Failed to save index to cache: {e}")
            return False
    
    def find_cs_files(self, include_packages: bool = False) -> list[str]:
        """Find all C# files in the project."""
        cs_files: list[str] = []
        
        # Assets folder
        assets_dir = os.path.join(self.project_root, "Assets")
        if os.path.isdir(assets_dir):
            for root, dirs, files in os.walk(assets_dir):
                # Skip certain directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['obj', 'bin', 'Library', 'Temp']]
                for file in files:
                    if file.endswith('.cs'):
                        cs_files.append(os.path.join(root, file))
        
        # Packages folder (optional)
        if include_packages:
            packages_dir = os.path.join(self.project_root, "Packages")
            if os.path.isdir(packages_dir):
                for root, dirs, files in os.walk(packages_dir):
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                    for file in files:
                        if file.endswith('.cs'):
                            cs_files.append(os.path.join(root, file))
        
        return cs_files
    
    def build_index(self, include_packages: bool = False, force_rebuild: bool = False) -> dict[str, Any]:
        """Build the complete code index."""
        if not force_rebuild and self.load_index():
            # Check for modifications and update incrementally
            return self.update_index(include_packages)
        
        logger.info(f"Building code index for {self.project_root}")
        
        cs_files = self.find_cs_files(include_packages)
        total_files = len(cs_files)
        processed = 0
        errors = 0
        
        self.index = CodeIndex(
            version="1.0",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            project_root=self.project_root,
            files={}
        )
        
        for file_path in cs_files:
            try:
                file_index = CSharpParser.parse_file(file_path)
                self.index.files[file_path] = file_index
                processed += 1
            except Exception as e:
                logger.warning(f"Failed to parse {file_path}: {e}")
                errors += 1
        
        self.index._rebuild_lookup_tables()
        self._index_loaded = True
        self.save_index()
        
        symbol_count = sum(len(f.symbols) for f in self.index.files.values())
        
        return {
            "success": True,
            "files_processed": processed,
            "files_total": total_files,
            "errors": errors,
            "symbols_indexed": symbol_count
        }
    
    def update_index(self, include_packages: bool = False) -> dict[str, Any]:
        """Incrementally update the index based on file modifications."""
        if not self._index_loaded:
            self.load_index()
        
        cs_files = self.find_cs_files(include_packages)
        
        added = 0
        updated = 0
        removed = 0
        errors = 0
        
        # Check for new or modified files
        current_files = set(cs_files)
        indexed_files = set(self.index.files.keys())
        
        # Remove files that no longer exist
        for file_path in indexed_files - current_files:
            del self.index.files[file_path]
            removed += 1
        
        # Add or update files
        for file_path in current_files:
            try:
                current_hash = CSharpParser.compute_file_hash(file_path)
                
                if file_path not in self.index.files:
                    # New file
                    file_index = CSharpParser.parse_file(file_path)
                    self.index.files[file_path] = file_index
                    added += 1
                elif self.index.files[file_path].file_hash != current_hash:
                    # Modified file
                    file_index = CSharpParser.parse_file(file_path)
                    self.index.files[file_path] = file_index
                    updated += 1
            except Exception as e:
                logger.warning(f"Failed to update {file_path}: {e}")
                errors += 1
        
        self.index.updated_at = datetime.now().isoformat()
        self.index._rebuild_lookup_tables()
        self.save_index()
        
        symbol_count = sum(len(f.symbols) for f in self.index.files.values())
        
        return {
            "success": True,
            "files_added": added,
            "files_updated": updated,
            "files_removed": removed,
            "errors": errors,
            "total_symbols": symbol_count
        }
    
    def search_code(
        self,
        pattern: str,
        regex: bool = True,
        ignore_case: bool = True,
        file_pattern: str | None = None,
        max_results: int = 100,
        offset: int = 0
    ) -> dict[str, Any]:
        """Search across all C# files using regex or text search."""
        if not self._index_loaded:
            self.load_index()
        
        results: list[dict[str, Any]] = []
        
        # Compile regex if needed
        flags = re.IGNORECASE if ignore_case else 0
        if regex:
            try:
                compiled_pattern = re.compile(pattern, flags)
            except re.error as e:
                return {"success": False, "error": f"Invalid regex pattern: {e}"}
        else:
            compiled_pattern = re.compile(re.escape(pattern), flags)
        
        # Filter files by pattern if specified
        files_to_search = list(self.index.files.keys())
        if file_pattern:
            file_regex = re.compile(file_pattern, re.IGNORECASE)
            files_to_search = [f for f in files_to_search if file_regex.search(f)]
        
        for file_path in files_to_search:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                
                # Search in content
                for match in compiled_pattern.finditer(content):
                    # Find line number
                    line_num = content[:match.start()].count('\n') + 1
                    line_start = content.rfind('\n', 0, match.start()) + 1
                    line_end = content.find('\n', match.start())
                    if line_end == -1:
                        line_end = len(content)
                    
                    line_content = content[line_start:line_end].strip()
                    
                    results.append({
                        "file_path": file_path,
                        "line_number": line_num,
                        "column": match.start() - line_start + 1,
                        "match": match.group(0),
                        "line_content": line_content
                    })
                    
                    if len(results) >= max_results + offset:
                        break
                        
            except Exception as e:
                logger.warning(f"Failed to search {file_path}: {e}")
        
        total = len(results)
        paginated_results = results[offset:offset + max_results] if offset < len(results) else []
        
        return {
            "success": True,
            "results": paginated_results,
            "total": total,
            "offset": offset,
            "limit": max_results,
            "has_more": total > offset + max_results
        }
    
    def find_symbol(
        self,
        name: str,
        symbol_type: str | None = None,
        exact_match: bool = True
    ) -> dict[str, Any]:
        """Find symbol definitions by name."""
        if not self._index_loaded:
            self.load_index()
        
        results: list[dict[str, Any]] = []
        
        for file_path, file_index in self.index.files.items():
            for symbol in file_index.symbols:
                # Match by name
                name_matches = (
                    symbol.name == name if exact_match
                    else name.lower() in symbol.name.lower()
                )
                
                # Match by type if specified
                type_matches = symbol_type is None or symbol.type == symbol_type
                
                if name_matches and type_matches:
                    results.append(symbol.to_dict())
        
        return {
            "success": True,
            "results": results,
            "count": len(results)
        }
    
    def find_references(
        self,
        symbol_name: str,
        max_results: int = 100,
        offset: int = 0
    ) -> dict[str, Any]:
        """Find all references to a symbol."""
        if not self._index_loaded:
            self.load_index()
        
        # First find the symbol definition
        symbol_info = self.find_symbol(symbol_name, exact_match=True)
        if not symbol_info["results"]:
            return {
                "success": True,
                "results": [],
                "total": 0,
                "message": f"Symbol '{symbol_name}' not found in index"
            }
        
        # Search for references
        results: list[dict[str, Any]] = []
        
        # Use word boundary for more accurate matching
        pattern = r'\b' + re.escape(symbol_name) + r'\b'
        compiled = re.compile(pattern)
        
        for file_path in self.index.files.keys():
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                
                for match in compiled.finditer(content):
                    line_num = content[:match.start()].count('\n') + 1
                    line_start = content.rfind('\n', 0, match.start()) + 1
                    line_end = content.find('\n', match.start())
                    if line_end == -1:
                        line_end = len(content)
                    
                    line_content = content[line_start:line_end].strip()
                    
                    # Skip definition lines (heuristic)
                    if any(keyword in line_content for keyword in ['class ', 'struct ', 'interface ', 'enum ', 'void ', 'public ', 'private ', 'protected ']):
                        if symbol_name in line_content.split(':' if ':' in line_content else '{')[0]:
                            continue
                    
                    results.append({
                        "file_path": file_path,
                        "line_number": line_num,
                        "column": match.start() - line_start + 1,
                        "context": line_content
                    })
                    
                    if len(results) >= max_results + offset:
                        break
                        
            except Exception as e:
                logger.warning(f"Failed to search references in {file_path}: {e}")
        
        total = len(results)
        paginated_results = results[offset:offset + max_results] if offset < len(results) else []
        
        return {
            "success": True,
            "symbol": symbol_info["results"][0] if symbol_info["results"] else None,
            "results": paginated_results,
            "total": total,
            "offset": offset,
            "limit": max_results,
            "has_more": total > offset + max_results
        }
    
    def get_symbols(
        self,
        file_path: str | None = None,
        symbol_type: str | None = None,
        namespace: str | None = None,
        max_results: int = 100,
        offset: int = 0
    ) -> dict[str, Any]:
        """List all symbols in a file or across the entire codebase."""
        if not self._index_loaded:
            self.load_index()
        
        results: list[dict[str, Any]] = []
        
        files_to_search = [file_path] if file_path else list(self.index.files.keys())
        
        for fp in files_to_search:
            if fp not in self.index.files:
                continue
            
            file_index = self.index.files[fp]
            for symbol in file_index.symbols:
                # Apply filters
                if symbol_type and symbol.type != symbol_type:
                    continue
                if namespace and symbol.namespace != namespace:
                    continue
                
                results.append(symbol.to_dict())
        
        total = len(results)
        paginated_results = results[offset:offset + max_results] if offset < len(results) else []
        
        return {
            "success": True,
            "results": paginated_results,
            "total": total,
            "offset": offset,
            "limit": max_results,
            "has_more": total > offset + max_results
        }
    
    def get_index_status(self) -> dict[str, Any]:
        """Get current index status and statistics."""
        if not self._index_loaded:
            loaded = self.load_index()
        else:
            loaded = True
        
        file_count = len(self.index.files)
        symbol_count = sum(len(f.symbols) for f in self.index.files.values())
        
        symbol_types: dict[str, int] = {}
        for file_index in self.index.files.values():
            for symbol in file_index.symbols:
                symbol_types[symbol.type] = symbol_types.get(symbol.type, 0) + 1
        
        return {
            "success": True,
            "loaded": loaded,
            "project_root": self.project_root,
            "cache_file": self._get_cache_file_path(),
            "files_indexed": file_count,
            "total_symbols": symbol_count,
            "symbol_types": symbol_types,
            "created_at": self.index.created_at,
            "updated_at": self.index.updated_at
        }
    
    def clear_index(self) -> dict[str, Any]:
        """Clear the current index and cache."""
        cache_file = self._get_cache_file_path()
        if os.path.exists(cache_file):
            try:
                os.remove(cache_file)
            except Exception as e:
                logger.warning(f"Failed to remove cache file: {e}")
        
        self.index = CodeIndex(project_root=self.project_root)
        self._index_loaded = False
        
        return {
            "success": True,
            "message": "Index cleared successfully"
        }


# Global instance for reuse
_index_managers: dict[str, CodeIndexManager] = {}


def get_index_manager(project_root: str | None = None) -> CodeIndexManager:
    """Get or create an index manager for a project."""
    root = project_root or os.getcwd()
    if root not in _index_managers:
        _index_managers[root] = CodeIndexManager(root)
    return _index_managers[root]
