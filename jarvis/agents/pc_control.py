"""
J.A.R.V.I.S. - PC Control Agent
Mouse, keyboard, window, and application automation
"""

import os
import sys
import time
import subprocess
import platform
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import EventBus, Event, EventType, get_event_bus, get_agent_registry


# Try to import GUI automation libraries
try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
    pyautogui.FAILSAFE = True  # Move mouse to corner to abort
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    print("pyautogui not available, GUI control disabled")

try:
    from pynput import mouse, keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    print("pynput not available, input listening disabled")

try:
    import pygetwindow as gw
    PYGETWINDOW_AVAILABLE = True
except ImportError:
    PYGETWINDOW_AVAILABLE = False
    print("pygetwindow not available, window control disabled")


@dataclass
class WindowInfo:
    """Information about a window"""
    title: str
    left: int
    top: int
    width: int
    height: int
    is_minimized: bool
    is_maximized: bool


class AppResolver:
    """Resolves application names to executables"""
    
    # Common application mappings
    APP_MAPPINGS = {
        "chrome": ["chrome", "google chrome", "chromium"],
        "firefox": ["firefox", "mozilla firefox"],
        "edge": ["msedge", "microsoft edge"],
        "vscode": ["code", "visual studio code", "vs code"],
        "terminal": ["gnome-terminal", "konsole", "xterm", "cmd", "powershell"],
        "notepad": ["notepad", "notepad++", "nvim", "vim"],
        "calculator": ["calc", "calculator", "kcalc"],
        "files": ["nautilus", "explorer", "thunar", "dolphin"],
        "spotify": ["spotify"],
        "discord": ["discord"],
        "slack": ["slack"],
        "zoom": ["zoom"],
    }
    
    def __init__(self):
        self.system = platform.system()
        self._executable_cache = {}
    
    def resolve(self, app_name: str) -> Optional[str]:
        """Resolve an app name to its executable path"""
        app_name_lower = app_name.lower().strip()
        
        # Check cache first
        if app_name_lower in self._executable_cache:
            return self._executable_cache[app_name_lower]
        
        # Find matching app pattern
        for canonical, aliases in self.APP_MAPPINGS.items():
            if app_name_lower == canonical or app_name_lower in aliases:
                # Try to find the executable
                exe_path = self._find_executable(canonical)
                if exe_path:
                    self._executable_cache[app_name_lower] = exe_path
                    return exe_path
        
        # Try direct match
        exe_path = self._find_executable(app_name_lower)
        if exe_path:
            self._executable_cache[app_name_lower] = exe_path
            return exe_path
        
        return None
    
    def _find_executable(self, name: str) -> Optional[str]:
        """Find executable in system PATH"""
        if self.system == "Windows":
            # Try with .exe extension
            exe_name = f"{name}.exe" if not name.endswith(".exe") else name
            
            # Check common installation paths
            common_paths = [
                os.path.join(os.environ.get("PROGRAMFILES", ""), name),
                os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), name),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", name),
            ]
            
            for path in common_paths:
                if os.path.exists(path):
                    return path
            
            # Search in PATH
            return self._which(exe_name)
        else:
            # Linux/Mac - use which
            return self._which(name)
    
    def _which(self, program: str) -> Optional[str]:
        """Cross-platform which command"""
        def is_exe(fpath):
            return os.path.isfile(fpath) and os.access(fpath, os.X_OK)
        
        fpath, fname = os.path.split(program)
        if fpath:
            if is_exe(program):
                return program
        else:
            for path in os.environ.get("PATH", "").split(os.pathsep):
                exe_file = os.path.join(path, program)
                if is_exe(exe_file):
                    return exe_file
        
        return None


class PCControlAgent:
    """
    PC Control Agent - Handles mouse, keyboard, window, and application control
    """
    
    def __init__(self, event_bus: Optional[EventBus] = None, safe_mode: bool = True):
        self.event_bus = event_bus or get_event_bus()
        self.safe_mode = safe_mode  # Require confirmation for destructive actions
        
        self.agent_id = "pc_control"
        self.capabilities = [
            "mouse_control",
            "keyboard_control",
            "window_management",
            "application_launching",
            "clipboard_operations",
            "screen_capture"
        ]
        
        self.app_resolver = AppResolver()
        self._running = False
        self._confirmation_pending = False
        
        # Register with the system
        self._register_self()
    
    def _register_self(self):
        """Register pc_control agent with the registry"""
        self.registry = get_agent_registry()
        self.registry.register_agent(
            agent_id=self.agent_id,
            name="PC Control",
            capabilities=self.capabilities,
            metadata={
                "description": "Controls mouse, keyboard, windows, and applications",
                "priority": 3,
                "safe_mode": self.safe_mode
            }
        )
    
    async def start(self):
        """Start the PC control agent"""
        self._running = True
        
        # Subscribe to commands
        self.event_bus.subscribe(
            subscriber_id=self.agent_id,
            callback=self._on_command,
            event_types=[EventType.COMMAND]
        )
        
        print(f"[{self.agent_id.upper()}] PC Control agent started (safe_mode={self.safe_mode})")
    
    async def stop(self):
        """Stop the PC control agent"""
        self._running = False
        self.event_bus.unsubscribe(self.agent_id)
        print(f"[{self.agent_id.upper()}] PC Control agent stopped")
    
    async def _on_command(self, event: Event):
        """Handle PC control commands"""
        if event.target != self.agent_id:
            return
        
        action = event.payload.get("action", "")
        parameters = event.payload.get("parameters", {})
        
        result = None
        error = None
        
        try:
            if action == "COMMAND_PC" or True:  # Handle all PC commands
                parsed = parameters
                cmd_action = parsed.get("action")
                target = parsed.get("target")
                
                if cmd_action == "OPEN":
                    result = await self.open_application(target)
                elif cmd_action == "CLOSE":
                    result = await self.close_application(target)
                elif cmd_action == "CLICK":
                    result = await self.mouse_click()
                elif cmd_action == "TYPE":
                    text = parsed.get("parameters", {}).get("text", target)
                    result = await self.type_text(text)
                elif cmd_action == "PRESS_KEY":
                    key = parsed.get("parameters", {}).get("key", target)
                    result = await self.press_key(key)
                elif cmd_action == "MOVE_MOUSE":
                    coords = parsed.get("parameters", {}).get("coordinates", {})
                    result = await self.move_mouse(coords.get("x"), coords.get("y"))
                else:
                    # Try to handle natural language commands
                    result = await self._handle_natural_command(event.payload.get("input", ""))
            
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
    
    async def _handle_natural_command(self, command: str) -> Dict:
        """Handle natural language PC commands"""
        command_lower = command.lower()
        
        # Open application
        open_match = re.search(r'open\s+(\w+(?:\s+\w+)*)', command_lower)
        if open_match:
            app_name = open_match.group(1).strip()
            return await self.open_application(app_name)
        
        # Close application
        close_match = re.search(r'(?:close|kill|quit|exit)\s+(\w+(?:\s+\w+)*)', command_lower)
        if close_match:
            app_name = close_match.group(1).strip()
            return await self.close_application(app_name)
        
        # Type text
        type_match = re.search(r'type\s+[\'"](.+)[\'"]', command_lower)
        if type_match:
            text = type_match.group(1)
            return await self.type_text(text)
        
        # Press key
        key_match = re.search(r'press\s+(?:the\s+)?(\w+)\s+(?:key|button)', command_lower)
        if key_match:
            key = key_match.group(1)
            return await self.press_key(key)
        
        return {"message": "Command recognized but action unclear, sir."}
    
    async def open_application(self, app_name: str) -> Dict:
        """Open an application"""
        if not app_name:
            return {"success": False, "message": "No application specified"}
        
        exe_path = self.app_resolver.resolve(app_name)
        
        if exe_path:
            try:
                subprocess.Popen([exe_path], shell=(platform.system() == "Windows"))
                return {"success": True, "message": f"Opening {app_name}, sir."}
            except Exception as e:
                return {"success": False, "message": f"Failed to open {app_name}: {str(e)}"}
        else:
            # Try to run directly
            try:
                subprocess.Popen([app_name], shell=True)
                return {"success": True, "message": f"Launching {app_name}, sir."}
            except Exception as e:
                return {"success": False, "message": f"Application '{app_name}' not found"}
    
    async def close_application(self, app_name: str) -> Dict:
        """Close an application"""
        if not app_name:
            return {"success": False, "message": "No application specified"}
        
        if self.safe_mode:
            return {"success": False, "message": f"Safe mode: Please confirm you want to close {app_name}"}
        
        try:
            if platform.system() == "Windows":
                subprocess.run(["taskkill", "/IM", f"{app_name}.exe", "/F"], 
                             capture_output=True, timeout=5)
            else:
                subprocess.run(["pkill", "-f", app_name], capture_output=True, timeout=5)
            
            return {"success": True, "message": f"Closing {app_name}, sir."}
        except Exception as e:
            return {"success": False, "message": f"Failed to close {app_name}: {str(e)}"}
    
    async def mouse_click(self, x: Optional[int] = None, y: Optional[int] = None, 
                         button: str = "left", clicks: int = 1) -> Dict:
        """Click the mouse"""
        if not PYAUTOGUI_AVAILABLE:
            return {"success": False, "message": "GUI control not available"}
        
        try:
            if x is not None and y is not None:
                pyautogui.moveTo(x, y, duration=0.2)
            
            pyautogui.click(clicks=clicks, button=button)
            return {"success": True, "message": f"Clicked at ({x}, {y})" if x and y else "Clicked"}
        except Exception as e:
            return {"success": False, "message": f"Mouse click failed: {str(e)}"}
    
    async def move_mouse(self, x: int, y: int, duration: float = 0.2) -> Dict:
        """Move the mouse to coordinates"""
        if not PYAUTOGUI_AVAILABLE:
            return {"success": False, "message": "GUI control not available"}
        
        try:
            pyautogui.moveTo(x, y, duration=duration)
            return {"success": True, "message": f"Moved mouse to ({x}, {y})"}
        except Exception as e:
            return {"success": False, "message": f"Mouse move failed: {str(e)}"}
    
    async def type_text(self, text: str, interval: float = 0.05) -> Dict:
        """Type text using keyboard"""
        if not PYAUTOGUI_AVAILABLE:
            return {"success": False, "message": "GUI control not available"}
        
        try:
            pyautogui.write(text, interval=interval)
            return {"success": True, "message": f"Typed: {text[:30]}..."}
        except Exception as e:
            return {"success": False, "message": f"Type failed: {str(e)}"}
    
    async def press_key(self, key: str, modifiers: Optional[List[str]] = None) -> Dict:
        """Press a keyboard key"""
        if not PYAUTOGUI_AVAILABLE:
            return {"success": False, "message": "GUI control not available"}
        
        try:
            if modifiers:
                pyautogui.hotkey(*modifiers, key)
            else:
                pyautogui.press(key)
            return {"success": True, "message": f"Pressed {key}"}
        except Exception as e:
            return {"success": False, "message": f"Key press failed: {str(e)}"}
    
    async def scroll(self, amount: int, x: Optional[int] = None, 
                    y: Optional[int] = None) -> Dict:
        """Scroll the mouse wheel"""
        if not PYAUTOGUI_AVAILABLE:
            return {"success": False, "message": "GUI control not available"}
        
        try:
            if x and y:
                pyautogui.scroll(amount, x=x, y=y)
            else:
                pyautogui.scroll(amount)
            return {"success": True, "message": f"Scrolled {amount}"}
        except Exception as e:
            return {"success": False, "message": f"Scroll failed: {str(e)}"}
    
    async def get_active_window(self) -> Optional[WindowInfo]:
        """Get information about the active window"""
        if not PYGETWINDOW_AVAILABLE:
            return None
        
        try:
            window = gw.getActiveWindow()
            if window:
                return WindowInfo(
                    title=window.title,
                    left=window.left,
                    top=window.top,
                    width=window.width,
                    height=window.height,
                    is_minimized=window.isMinimized,
                    is_maximized=window.isMaximized
                )
        except Exception:
            pass
        
        return None
    
    async def list_windows(self) -> List[Dict]:
        """List all open windows"""
        if not PYGETWINDOW_AVAILABLE:
            return []
        
        try:
            windows = gw.getAllTitles()
            return [{"title": w} for w in windows if w]
        except Exception:
            return []
    
    async def screenshot(self, region: Optional[Tuple[int, int, int, int]] = None) -> Dict:
        """Take a screenshot"""
        if not PYAUTOGUI_AVAILABLE:
            return {"success": False, "message": "GUI control not available"}
        
        try:
            if region:
                screenshot = pyautogui.screenshot(region=region)
            else:
                screenshot = pyautogui.screenshot()
            
            # Save screenshot
            filename = f"screenshot_{int(time.time())}.png"
            screenshot.save(filename)
            
            return {"success": True, "message": f"Screenshot saved to {filename}"}
        except Exception as e:
            return {"success": False, "message": f"Screenshot failed: {str(e)}"}
    
    def get_status(self) -> Dict[str, Any]:
        """Get PC control agent status"""
        return {
            "agent_id": self.agent_id,
            "running": self._running,
            "capabilities": self.capabilities,
            "safe_mode": self.safe_mode,
            "pyautogui_available": PYAUTOGUI_AVAILABLE,
            "pynput_available": PYNPUT_AVAILABLE,
            "pygetwindow_available": PYGETWINDOW_AVAILABLE
        }


# Singleton instance
_pc_control_instance: Optional[PCControlAgent] = None


def get_pc_control(event_bus: Optional[EventBus] = None) -> PCControlAgent:
    """Get or create the PC control agent singleton"""
    global _pc_control_instance
    if _pc_control_instance is None:
        _pc_control_instance = PCControlAgent(event_bus)
    return _pc_control_instance


if __name__ == "__main__":
    # Test the PC control agent
    async def test_pc_control():
        bus = EventBus()
        await bus.start()
        
        pc_control = PCControlAgent(bus, safe_mode=False)
        await pc_control.start()
        
        print("=" * 60)
        print("J.A.R.V.I.S. PC Control Agent Test")
        print("=" * 60)
        
        # Test app resolution
        print("\nApp Resolution Tests:")
        test_apps = ["chrome", "firefox", "vscode", "terminal", "notepad"]
        for app in test_apps:
            resolved = pc_control.app_resolver.resolve(app)
            print(f"  {app}: {resolved}")
        
        # Get status
        print("\n" + "=" * 60)
        print("PC Control Agent Status:")
        print(pc_control.get_status())
        
        await pc_control.stop()
        await bus.stop()
    
    asyncio.run(test_pc_control())
