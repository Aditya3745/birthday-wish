"""
J.A.R.V.I.S. - Code Agent
Write, run, debug, and refactor code in any language
"""

import os
import sys
import subprocess
import tempfile
import shutil
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import EventBus, Event, EventType, get_event_bus, get_agent_registry


@dataclass
class CodeFile:
    """Represents a code file"""
    path: str
    content: str
    language: str
    
    def to_dict(self) -> Dict:
        return {
            "path": self.path,
            "content": self.content,
            "language": self.language
        }


@dataclass
class ExecutionResult:
    """Result of code execution"""
    success: bool
    output: str
    error: str
    exit_code: int
    execution_time: float


class CodeAgent:
    """
    Code Agent - Writes, runs, debugs, and refactors code
    Supports multiple languages with auto-execution and debugging
    """
    
    SUPPORTED_LANGUAGES = {
        "python": {
            "extensions": [".py"],
            "run_command": "python",
            "check_syntax": "python -m py_compile",
        },
        "javascript": {
            "extensions": [".js"],
            "run_command": "node",
            "check_syntax": "node --check",
        },
        "typescript": {
            "extensions": [".ts"],
            "run_command": "ts-node",
            "check_syntax": "tsc --noEmit",
        },
        "bash": {
            "extensions": [".sh", ".bash"],
            "run_command": "bash",
            "check_syntax": "bash -n",
        },
        "html": {
            "extensions": [".html", ".htm"],
            "run_command": None,  # Can't execute directly
        },
        "css": {
            "extensions": [".css"],
            "run_command": None,
        },
        "sql": {
            "extensions": [".sql"],
            "run_command": None,
        },
        "c++": {
            "extensions": [".cpp", ".cc", ".cxx"],
            "run_command": "g++",
            "compile_command": "g++ -o {output} {input}",
        },
        "java": {
            "extensions": [".java"],
            "run_command": "java",
            "compile_command": "javac",
        },
        "go": {
            "extensions": [".go"],
            "run_command": "go run",
        },
        "rust": {
            "extensions": [".rs"],
            "run_command": "rustc",
        },
    }
    
    def __init__(self, event_bus: Optional[EventBus] = None, 
                 workspace_dir: str = "code_workspace"):
        self.event_bus = event_bus or get_event_bus()
        self.workspace_dir = workspace_dir
        
        # Create workspace directory
        os.makedirs(workspace_dir, exist_ok=True)
        
        self.agent_id = "code"
        self.capabilities = [
            "code_generation",
            "code_execution",
            "debugging",
            "refactoring",
            "code_review",
            "project_creation",
            "dependency_management"
        ]
        
        self._running = False
        self._execution_history: List[Dict] = []
        
        # Register with the system
        self._register_self()
    
    def _register_self(self):
        """Register code agent with the registry"""
        self.registry = get_agent_registry()
        self.registry.register_agent(
            agent_id=self.agent_id,
            name="Code Expert",
            capabilities=self.capabilities,
            metadata={
                "description": "Writes, runs, debugs, and refactors code",
                "priority": 3,
                "supported_languages": list(self.SUPPORTED_LANGUAGES.keys())
            }
        )
    
    async def start(self):
        """Start the code agent"""
        self._running = True
        
        # Subscribe to commands
        self.event_bus.subscribe(
            subscriber_id=self.agent_id,
            callback=self._on_command,
            event_types=[EventType.COMMAND]
        )
        
        print(f"[{self.agent_id.upper()}] Code agent started")
    
    async def stop(self):
        """Stop the code agent"""
        self._running = False
        self.event_bus.unsubscribe(self.agent_id)
        print(f"[{self.agent_id.upper()}] Code agent stopped")
    
    async def _on_command(self, event: Event):
        """Handle code commands"""
        if event.target != self.agent_id:
            return
        
        action = event.payload.get("action", "")
        input_text = event.payload.get("input", "")
        
        result = None
        error = None
        
        try:
            if action == "COMMAND_CODE":
                # Parse the request
                if any(word in input_text.lower() for word in ["write", "create", "generate"]):
                    result = await self.generate_code(input_text)
                elif any(word in input_text.lower() for word in ["run", "execute", "test"]):
                    result = await self.execute_code(input_text)
                elif any(word in input_text.lower() for word in ["fix", "debug", "error"]):
                    result = await self.debug_code(input_text)
                elif any(word in input_text.lower() for word in ["refactor", "optimize", "improve"]):
                    result = await self.refactor_code(input_text)
                elif any(word in input_text.lower() for word in ["review", "analyze"]):
                    result = await self.review_code(input_text)
                else:
                    result = await self.generate_code(input_text)
            
            await self._send_response(event, result, error)
            
        except Exception as e:
            await self._send_response(event, None, str(e))
    
    async def _send_response(self, event: Event, result: Any, error: Optional[str]):
        """Send response back through event bus"""
        event_type = EventType.TASK_COMPLETE if not error else EventType.ERROR
        
        response_event = Event(
            type=event_type,
            source=self.agent_id,
            correlation_id=event.correlation_id,
            payload={
                "task_id": event.payload.get("task_id"),
                "result": result,
                "error": error,
                "conversation_id": event.payload.get("conversation_id")
            }
        )
        await self.event_bus.publish(response_event)
    
    async def generate_code(self, description: str, language: str = "python") -> Dict:
        """Generate code from description"""
        # In production, this would call the brain/LLM
        # For now, provide template-based generation
        
        templates = {
            "python": {
                "function": '''def {name}({params}):
    """{docstring}"""
    # TODO: Implement logic here
    pass


if __name__ == "__main__":
    # Test the function
    result = {name}()
    print(result)
''',
                "class": '''class {name}:
    """{docstring}"""
    
    def __init__(self):
        # Initialize attributes here
        pass
    
    def method(self):
        # Implement method here
        pass
''',
                "script": '''#!/usr/bin/env python3
"""
{description}
"""

import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    logger.info("Starting program")
    # TODO: Implement main logic
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''
            }
        }
        
        # Detect what type of code to generate
        code_type = "script"
        if "function" in description.lower() or "def " in description.lower():
            code_type = "function"
        elif "class" in description.lower():
            code_type = "class"
        
        # Generate code
        if language.lower() in templates and code_type in templates[language.lower()]:
            template = templates[language.lower()][code_type]
            code = template.format(
                name="generated_function",
                params="",
                docstring=description,
                description=description
            )
        else:
            # Generic code generation placeholder
            code = f"# Generated code for: {description}\n# Language: {language}\n\nprint('Hello, World!')\n"
        
        # Save to file
        ext = self.SUPPORTED_LANGUAGES.get(language.lower(), {}).get("extensions", [".txt"])[0]
        filename = f"generated_{len(self._execution_history)}{ext}"
        filepath = os.path.join(self.workspace_dir, filename)
        
        with open(filepath, "w") as f:
            f.write(code)
        
        return {
            "success": True,
            "message": f"Generated {language} code",
            "code": code,
            "file_path": filepath,
            "language": language
        }
    
    async def execute_code(self, code_or_file: str, language: str = "python") -> Dict:
        """Execute code and capture output"""
        # Check if it's a file path or code
        if os.path.exists(code_or_file):
            filepath = code_or_file
            with open(filepath, "r") as f:
                code = f.read()
        else:
            # Save code to temp file
            ext = self.SUPPORTED_LANGUAGES.get(language.lower(), {}).get("extensions", [".txt"])[0]
            fd, filepath = tempfile.mkstemp(suffix=ext, dir=self.workspace_dir)
            with os.fdopen(fd, "w") as f:
                f.write(code_or_file)
        
        # Get language config
        lang_config = self.SUPPORTED_LANGUAGES.get(language.lower())
        if not lang_config:
            return {"success": False, "error": f"Unsupported language: {language}"}
        
        run_command = lang_config.get("run_command")
        if not run_command:
            return {"success": False, "error": f"Cannot execute {language} directly"}
        
        try:
            import time
            start_time = time.time()
            
            # Execute the code
            result = subprocess.run(
                [run_command, filepath],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.workspace_dir
            )
            
            execution_time = time.time() - start_time
            
            exec_result = ExecutionResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr,
                exit_code=result.returncode,
                execution_time=execution_time
            )
            
            # Store in history
            self._execution_history.append({
                "file": filepath,
                "language": language,
                "result": exec_result.success
            })
            
            return {
                "success": exec_result.success,
                "output": exec_result.output,
                "error": exec_result.error,
                "exit_code": exec_result.exit_code,
                "execution_time": exec_result.execution_time
            }
            
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Execution timed out (30s limit)"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def debug_code(self, code_or_error: str, language: str = "python") -> Dict:
        """Debug code by analyzing errors and suggesting fixes"""
        # This would use LLM in production
        # For now, provide basic error analysis
        
        error_patterns = {
            "SyntaxError": "Check for missing colons, parentheses, or quotes",
            "IndentationError": "Ensure consistent indentation (use spaces or tabs, not both)",
            "NameError": "Variable or function is not defined - check spelling and scope",
            "TypeError": "Operation performed on incompatible types",
            "ValueError": "Function received argument of correct type but inappropriate value",
            "IndexError": "List or array index out of range",
            "KeyError": "Dictionary key doesn't exist",
            "ImportError": "Module cannot be imported - check installation",
            "AttributeError": "Object doesn't have the specified attribute",
        }
        
        suggestions = []
        for error_type, suggestion in error_patterns.items():
            if error_type in code_or_error:
                suggestions.append(f"{error_type}: {suggestion}")
        
        if not suggestions:
            suggestions.append("Unable to identify specific error pattern. Please provide more context.")
        
        return {
            "success": True,
            "analysis": "Error analysis complete",
            "suggestions": suggestions,
            "original_error": code_or_error[:500]
        }
    
    async def refactor_code(self, code: str, goal: str = "optimize") -> Dict:
        """Refactor existing code"""
        # Would use LLM in production
        return {
            "success": True,
            "message": "Refactoring would be performed by LLM",
            "original_code": code[:200],
            "goal": goal
        }
    
    async def review_code(self, code: str, language: str = "python") -> Dict:
        """Review code for bugs and improvements"""
        issues = []
        
        # Basic static analysis
        lines = code.split("\n")
        
        # Check for common issues
        for i, line in enumerate(lines, 1):
            if "eval(" in line or "exec(" in line:
                issues.append({
                    "line": i,
                    "severity": "high",
                    "message": "Avoid using eval/exec - security risk"
                })
            
            if "# TODO" in line or "# FIXME" in line:
                issues.append({
                    "line": i,
                    "severity": "low",
                    "message": "Incomplete code marker found"
                })
            
            if len(line) > 100:
                issues.append({
                    "line": i,
                    "severity": "info",
                    "message": "Line exceeds 100 characters"
                })
        
        return {
            "success": True,
            "issues_found": len(issues),
            "issues": issues,
            "lines_of_code": len(lines)
        }
    
    async def create_project(self, name: str, project_type: str = "python") -> Dict:
        """Create a new project structure"""
        project_dir = os.path.join(self.workspace_dir, name)
        os.makedirs(project_dir, exist_ok=True)
        
        structures = {
            "python": {
                "files": [
                    ("README.md", f"# {name}\n\nProject description here\n"),
                    ("main.py", "#!/usr/bin/env python3\n\n\ndef main():\n    pass\n\n\nif __name__ == '__main__':\n    main()\n"),
                    ("requirements.txt", ""),
                    (".gitignore", "__pycache__/\n*.pyc\n.env\nvenv/\n"),
                ],
                "dirs": ["tests", "src", "docs"]
            },
            "node": {
                "files": [
                    ("README.md", f"# {name}\n"),
                    ("index.js", "// Main entry point\n"),
                    ("package.json", f'{{\n  "name": "{name}",\n  "version": "1.0.0"\n}}\n'),
                    (".gitignore", "node_modules/\n.env\n"),
                ],
                "dirs": ["src", "test"]
            }
        }
        
        structure = structures.get(project_type, structures["python"])
        
        created_files = []
        created_dirs = []
        
        # Create directories
        for dirname in structure.get("dirs", []):
            dirpath = os.path.join(project_dir, dirname)
            os.makedirs(dirpath, exist_ok=True)
            created_dirs.append(dirpath)
        
        # Create files
        for filename, content in structure.get("files", []):
            filepath = os.path.join(project_dir, filename)
            with open(filepath, "w") as f:
                f.write(content)
            created_files.append(filepath)
        
        return {
            "success": True,
            "message": f"Created {project_type} project '{name}'",
            "project_path": project_dir,
            "created_files": created_files,
            "created_dirs": created_dirs
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get code agent status"""
        return {
            "agent_id": self.agent_id,
            "running": self._running,
            "capabilities": self.capabilities,
            "supported_languages": list(self.SUPPORTED_LANGUAGES.keys()),
            "workspace_dir": self.workspace_dir,
            "execution_count": len(self._execution_history)
        }


# Singleton instance
_code_instance: Optional[CodeAgent] = None


def get_code(event_bus: Optional[EventBus] = None) -> CodeAgent:
    """Get or create the code agent singleton"""
    global _code_instance
    if _code_instance is None:
        _code_instance = CodeAgent(event_bus)
    return _code_instance


if __name__ == "__main__":
    # Test the code agent
    async def test_code_agent():
        bus = EventBus()
        await bus.start()
        
        code_agent = CodeAgent(bus)
        await code_agent.start()
        
        print("=" * 60)
        print("J.A.R.V.I.S. Code Agent Test")
        print("=" * 60)
        
        # Test code generation
        print("\nGenerating Python function...")
        result = await code_agent.generate_code(
            "A function that calculates fibonacci numbers",
            language="python"
        )
        print(f"Generated: {result['success']}")
        print(f"Code:\n{result['code']}")
        
        # Test code execution
        print("\nExecuting simple Python code...")
        result = await code_agent.execute_code(
            "print('Hello from JARVIS!')\nfor i in range(3):\n    print(i)",
            language="python"
        )
        print(f"Output: {result.get('output', 'N/A')}")
        
        # Test code review
        print("\nReviewing code...")
        sample_code = """
def bad_func():
    x = eval(input("Enter: "))
    return x
# TODO: fix this
"""
        result = await code_agent.review_code(sample_code)
        print(f"Issues found: {result['issues_found']}")
        for issue in result['issues']:
            print(f"  - Line {issue['line']}: {issue['message']}")
        
        # Get status
        print("\n" + "=" * 60)
        print("Code Agent Status:")
        print(code_agent.get_status())
        
        await code_agent.stop()
        await bus.stop()
        
        # Cleanup
        if os.path.exists("code_workspace"):
            shutil.rmtree("code_workspace")
    
    asyncio.run(test_code_agent())
