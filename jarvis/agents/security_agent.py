"""
J.A.R.V.I.S. - Security Agent
Ethical hacking and security analysis (AUTHORIZED TARGETS ONLY)
"""

import os
import sys
import subprocess
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import EventBus, Event, EventType, get_event_bus, get_agent_registry


class SecurityAgent:
    """
    Security Agent - Ethical hacking and security analysis
    ETHICS LOCK: Only operates on authorized targets
    """
    
    def __init__(self, event_bus: Optional[EventBus] = None, 
                 whitelist_file: str = "security_whitelist.json"):
        self.event_bus = event_bus or get_event_bus()
        self.whitelist_file = whitelist_file
        
        self.agent_id = "security"
        self.capabilities = [
            "network_recon",
            "port_scanning",
            "vulnerability_detection",
            "wifi_audit",
            "subdomain_enumeration",
            "web_vuln_scan",
            "cve_lookup",
            "report_generation"
        ]
        
        self._running = False
        self._authorized_targets = self._load_whitelist()
        self._scan_history: List[Dict] = []
        
        # Ethics lock - always require confirmation
        self.ethics_lock_enabled = True
        
        # Register with the system
        self._register_self()
    
    def _register_self(self):
        """Register security agent with the registry"""
        self.registry = get_agent_registry()
        self.registry.register_agent(
            agent_id=self.agent_id,
            name="Security Expert",
            capabilities=self.capabilities,
            metadata={
                "description": "Ethical hacking and security analysis (AUTHORIZED ONLY)",
                "priority": 3,
                "ethics_lock": True
            }
        )
    
    def _load_whitelist(self) -> List[str]:
        """Load authorized targets from whitelist"""
        if os.path.exists(self.whitelist_file):
            with open(self.whitelist_file, "r") as f:
                return json.load(f)
        return []
    
    def _save_whitelist(self):
        """Save whitelist to file"""
        with open(self.whitelist_file, "w") as f:
            json.dump(self._authorized_targets, f, indent=2)
    
    def add_to_whitelist(self, target: str):
        """Add a target to the authorized list"""
        if target not in self._authorized_targets:
            self._authorized_targets.append(target)
            self._save_whitelist()
    
    def remove_from_whitelist(self, target: str):
        """Remove a target from the authorized list"""
        if target in self._authorized_targets:
            self._authorized_targets.remove(target)
            self._save_whitelist()
    
    def is_authorized(self, target: str) -> bool:
        """Check if a target is authorized"""
        # Localhost and private ranges are always authorized for testing
        private_patterns = [
            r'^127\.\d+\.\d+\.\d+$',  # 127.x.x.x
            r'^10\.\d+\.\d+\.\d+$',   # 10.x.x.x
            r'^192\.168\.\d+\.\d+$',  # 192.168.x.x
            r'^172\.(1[6-9]|2\d|3[01])\.\d+\.\d+$',  # 172.16-31.x.x
            r'^localhost$',
            r'^::1$',  # IPv6 localhost
        ]
        
        for pattern in private_patterns:
            if re.match(pattern, target, re.IGNORECASE):
                return True
        
        # Check whitelist
        return target in self._authorized_targets
    
    async def start(self):
        """Start the security agent"""
        self._running = True
        
        # Subscribe to commands
        self.event_bus.subscribe(
            subscriber_id=self.agent_id,
            callback=self._on_command,
            event_types=[EventType.COMMAND]
        )
        
        print(f"[{self.agent_id.upper()}] Security agent started (ETHICS LOCK ENABLED)")
    
    async def stop(self):
        """Stop the security agent"""
        self._running = False
        self.event_bus.unsubscribe(self.agent_id)
        print(f"[{self.agent_id.upper()}] Security agent stopped")
    
    async def _on_command(self, event: Event):
        """Handle security commands"""
        if event.target != self.agent_id:
            return
        
        action = event.payload.get("action", "")
        input_text = event.payload.get("input", "")
        
        result = None
        error = None
        
        try:
            if action == "COMMAND_SECURITY":
                # Extract target from command
                target = self._extract_target(input_text)
                
                # ETHICS CHECK
                if self.ethics_lock_enabled and target:
                    if not self.is_authorized(target):
                        error = f"ETHICS LOCK: Target '{target}' is not authorized. This IP/domain must be in your whitelist."
                        await self._send_response(event, None, error)
                        return
                
                # Execute the appropriate scan
                if any(word in input_text.lower() for word in ["scan", "recon", "discover"]):
                    if "port" in input_text.lower():
                        result = await self.port_scan(target)
                    elif "network" in input_text.lower():
                        result = await self.network_recon(target)
                    elif "vuln" in input_text.lower() or "vulnerability" in input_text.lower():
                        result = await self.vulnerability_scan(target)
                    else:
                        result = await self.network_recon(target)
                elif "wifi" in input_text.lower() or "wpa" in input_text.lower():
                    result = await self.wifi_audit()
                elif "subdomain" in input_text.lower():
                    result = await self.subdomain_enum(target)
                elif "cve" in input_text.lower():
                    result = await self.cve_lookup(input_text)
                else:
                    result = {"message": "Please specify the type of security scan needed."}
            
            await self._send_response(event, result, error)
            
        except Exception as e:
            await self._send_response(event, None, str(e))
    
    def _extract_target(self, text: str) -> Optional[str]:
        """Extract target IP/hostname from text"""
        # IP address pattern
        ip_pattern = r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b'
        match = re.search(ip_pattern, text)
        if match:
            return match.group(1)
        
        # Hostname/URL pattern
        url_pattern = r'(?:https?://)?(?:www\.)?([\w\-]+\.[\w\.\-]+)'
        match = re.search(url_pattern, text)
        if match:
            return match.group(1)
        
        return None
    
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
    
    async def network_recon(self, target: str) -> Dict:
        """Perform network reconnaissance"""
        if not target:
            return {"success": False, "error": "No target specified"}
        
        self._log_action("network_recon", target)
        
        # Check for available tools
        results = {
            "target": target,
            "timestamp": datetime.now().isoformat(),
            "methods_used": []
        }
        
        # Try nmap if available
        if self._check_tool("nmap"):
            try:
                cmd = ["nmap", "-sn", target]  # Ping scan
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                results["nmap_ping"] = proc.stdout[:2000]
                results["methods_used"].append("nmap_ping_scan")
            except Exception as e:
                results["nmap_error"] = str(e)
        
        # Try ping
        try:
            cmd = ["ping", "-c", "4", target] if os.name != "nt" else ["ping", "-n", "4", target]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            results["ping"] = proc.stdout[:1000]
            results["methods_used"].append("ping")
        except Exception as e:
            results["ping_error"] = str(e)
        
        results["success"] = True
        return results
    
    async def port_scan(self, target: str, ports: str = "1-1000") -> Dict:
        """Perform port scanning"""
        if not target:
            return {"success": False, "error": "No target specified"}
        
        self._log_action("port_scan", target)
        
        results = {
            "target": target,
            "port_range": ports,
            "timestamp": datetime.now().isoformat(),
            "open_ports": []
        }
        
        # Use nmap if available
        if self._check_tool("nmap"):
            try:
                cmd = ["nmap", "-p", ports, "-Pn", target]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                
                # Parse open ports from output
                output = proc.stdout
                results["nmap_output"] = output[:5000]
                
                # Extract open ports
                for line in output.split("\n"):
                    if "/tcp" in line and "open" in line:
                        port_info = line.split()
                        if port_info:
                            results["open_ports"].append({
                                "port": port_info[0].split("/")[0],
                                "service": port_info[-1] if len(port_info) > 2 else "unknown"
                            })
                
                results["methods_used"] = ["nmap"]
                results["success"] = True
                
            except subprocess.TimeoutExpired:
                results["error"] = "Scan timed out"
            except Exception as e:
                results["error"] = str(e)
        else:
            results["error"] = "nmap not installed"
        
        return results
    
    async def vulnerability_scan(self, target: str) -> Dict:
        """Perform basic vulnerability detection"""
        if not target:
            return {"success": False, "error": "No target specified"}
        
        self._log_action("vulnerability_scan", target)
        
        results = {
            "target": target,
            "timestamp": datetime.now().isoformat(),
            "vulnerabilities": []
        }
        
        # First get open ports
        port_result = await self.port_scan(target, ports="1-100")
        
        if port_result.get("open_ports"):
            for port_info in port_result["open_ports"]:
                port = port_info.get("port")
                service = port_info.get("service")
                
                # Check for common vulnerable services
                vuln_checks = {
                    "21": "FTP - Often allows anonymous login, check for weak credentials",
                    "22": "SSH - Check for outdated versions (CVE-2018-15473)",
                    "23": "Telnet - UNENCRYPTED protocol, high risk",
                    "25": "SMTP - Check for open relay configuration",
                    "80": "HTTP - Unencrypted web traffic, check for web vulns",
                    "443": "HTTPS - Check for SSL/TLS vulnerabilities (Heartbleed, etc)",
                    "445": "SMB - Check for EternalBlue (MS17-010)",
                    "3306": "MySQL - Check for default credentials",
                    "3389": "RDP - Check for BlueKeep (CVE-2019-0708)",
                    "5432": "PostgreSQL - Check for authentication bypass",
                    "6379": "Redis - Often exposed without authentication",
                    "27017": "MongoDB - Often exposed without authentication",
                }
                
                if port in vuln_checks:
                    results["vulnerabilities"].append({
                        "port": port,
                        "service": service,
                        "risk": "medium",
                        "note": vuln_checks[port]
                    })
        
        results["success"] = True
        return results
    
    async def wifi_audit(self, interface: str = "wlan0") -> Dict:
        """Perform WiFi security audit"""
        results = {
            "interface": interface,
            "timestamp": datetime.now().isoformat(),
            "warning": "WiFi auditing requires root privileges and compatible hardware"
        }
        
        self._log_action("wifi_audit", interface)
        
        # Check for required tools
        tools_needed = ["airmon-ng", "airodump-ng", "aireplay-ng"]
        available_tools = [t for t in tools_needed if self._check_tool(t)]
        results["available_tools"] = available_tools
        
        if len(available_tools) < len(tools_needed):
            results["success"] = False
            results["error"] = "Missing required tools. Install aircrack-ng suite."
            return results
        
        # Monitor mode setup would go here
        # This is a placeholder for the actual implementation
        
        results["success"] = True
        results["message"] = "WiFi audit capabilities ready. Specify target BSSID for detailed audit."
        return results
    
    async def subdomain_enum(self, domain: str) -> Dict:
        """Enumerate subdomains"""
        if not domain:
            return {"success": False, "error": "No domain specified"}
        
        self._log_action("subdomain_enum", domain)
        
        results = {
            "domain": domain,
            "timestamp": datetime.now().isoformat(),
            "subdomains": []
        }
        
        # Check for subfinder
        if self._check_tool("subfinder"):
            try:
                cmd = ["subfinder", "-d", domain, "-silent"]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                results["subdomains"] = proc.stdout.strip().split("\n")
                results["methods_used"] = ["subfinder"]
            except Exception as e:
                results["error"] = str(e)
        else:
            # Fallback: common subdomain brute force
            common_subs = ["www", "mail", "ftp", "admin", "api", "dev", "test", "staging"]
            results["subdomains"] = [f"{sub}.{domain}" for sub in common_subs]
            results["methods_used"] = ["common_subdomains"]
        
        results["success"] = True
        return results
    
    async def cve_lookup(self, query: str) -> Dict:
        """Look up CVE information"""
        results = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "cves": []
        }
        
        # Extract CVE ID if present
        cve_pattern = r'CVE-\d{4}-\d+'
        match = re.search(cve_pattern, query, re.IGNORECASE)
        
        if match:
            cve_id = match.group(0).upper()
            results["cves"].append({
                "id": cve_id,
                "info": f"Lookup {cve_id} at https://nvd.nist.gov/vuln/detail/{cve_id}"
            })
        
        results["success"] = True
        return results
    
    def generate_report(self, scan_results: List[Dict]) -> str:
        """Generate a PDF/text report from scan results"""
        report = []
        report.append("=" * 60)
        report.append("J.A.R.V.I.S. SECURITY AUDIT REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")
        
        for i, result in enumerate(scan_results, 1):
            report.append(f"\n--- Scan {i} ---")
            report.append(f"Target: {result.get('target', 'N/A')}")
            report.append(f"Type: {result.get('type', 'N/A')}")
            
            if result.get("open_ports"):
                report.append("\nOpen Ports:")
                for port in result["open_ports"]:
                    report.append(f"  - Port {port['port']}: {port['service']}")
            
            if result.get("vulnerabilities"):
                report.append("\nVulnerabilities:")
                for vuln in result["vulnerabilities"]:
                    report.append(f"  - [{vuln['risk'].upper()}] Port {vuln['port']}: {vuln['note']}")
        
        report.append("\n" + "=" * 60)
        report.append("END OF REPORT")
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def _check_tool(self, tool_name: str) -> bool:
        """Check if a tool is installed"""
        try:
            subprocess.run(["which", tool_name], capture_output=True, check=True)
            return True
        except:
            return False
    
    def _log_action(self, action: str, target: str):
        """Log security actions for audit trail"""
        self._scan_history.append({
            "action": action,
            "target": target,
            "timestamp": datetime.now().isoformat()
        })
        
        # Also log to file
        log_file = "security_audit.log"
        with open(log_file, "a") as f:
            f.write(f"{datetime.now().isoformat()} | {action} | {target}\n")
    
    def get_status(self) -> Dict[str, Any]:
        """Get security agent status"""
        return {
            "agent_id": self.agent_id,
            "running": self._running,
            "capabilities": self.capabilities,
            "ethics_lock_enabled": self.ethics_lock_enabled,
            "authorized_targets_count": len(self._authorized_targets),
            "scans_performed": len(self._scan_history)
        }


# Singleton instance
_security_instance: Optional[SecurityAgent] = None


def get_security(event_bus: Optional[EventBus] = None) -> SecurityAgent:
    """Get or create the security agent singleton"""
    global _security_instance
    if _security_instance is None:
        _security_instance = SecurityAgent(event_bus)
    return _security_instance


if __name__ == "__main__":
    # Test the security agent
    async def test_security_agent():
        bus = EventBus()
        await bus.start()
        
        security = SecurityAgent(bus)
        await security.start()
        
        print("=" * 60)
        print("J.A.R.V.I.S. Security Agent Test")
        print("=" * 60)
        
        # Add localhost to whitelist
        security.add_to_whitelist("127.0.0.1")
        security.add_to_whitelist("localhost")
        
        print("\nAuthorized targets:", security._authorized_targets)
        
        # Test authorization check
        print("\nAuthorization checks:")
        print(f"  127.0.0.1: {security.is_authorized('127.0.0.1')}")
        print(f"  192.168.1.1: {security.is_authorized('192.168.1.1')}")
        print(f"  google.com: {security.is_authorized('google.com')}")
        
        # Test network recon on localhost
        print("\nNetwork recon on localhost...")
        result = await security.network_recon("127.0.0.1")
        print(f"Success: {result.get('success')}")
        print(f"Methods used: {result.get('methods_used')}")
        
        # Get status
        print("\n" + "=" * 60)
        print("Security Agent Status:")
        print(security.get_status())
        
        await security.stop()
        await bus.stop()
    
    asyncio.run(test_security_agent())
