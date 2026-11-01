#!/usr/bin/env python3
# Copyright (c) 2026 Alexandru Iosif Mocanu (Sonelu). All rights reserved.
"""
Athena-Web v2.0 - Localhost Full-Stack SOC & Recon Security Platform
Runs locally on http://127.0.0.1:8080 with zero external dependencies (pure Python standard library).

For education & authorized security testing only.
"""

import argparse
import email
import io
import json
import mimetypes
import os
import shlex
import subprocess
import sys
import threading
import time
import uuid
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

VERSION = "2.0"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080

BASE_DIR = Path(__file__).resolve().parent
TOOLS_DIR = BASE_DIR / "tools"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
UPLOADS_DIR = BASE_DIR / "uploads"

# Ensure directories exist
STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Tool catalog matching ATHENA_SPEC.md
TOOLS_CATALOG = {
    # 🔵 Blue Team (Defense)
    "ssh": {
        "name": "SSH & Auth Log Analyzer",
        "team": "blue",
        "script": "blue/log_analyzer.py",
        "desc": "Parse SSH & system auth logs for brute-force bursts, invalid users, and root logins",
        "syntax": "<auth.log>",
        "example": "/var/log/auth.log",
    },
    "fim": {
        "name": "File Integrity Monitor",
        "team": "blue",
        "script": "blue/fim.py",
        "desc": "Cryptographic SHA-256 integrity baseline & unauthorized file modification detector",
        "syntax": "[init|check] <dir>",
        "example": "check /etc",
    },
    "phish": {
        "name": "Phishing Email Analyzer",
        "team": "blue",
        "script": "blue/phishing_analyzer.py",
        "desc": "Forensic email header inspection, SPF/DKIM/DMARC auth, lookalikes & malicious attachments",
        "syntax": "<email.eml>",
        "example": "suspicious_invoice.eml",
    },
    "pcap": {
        "name": "PCAP Threat Hunter",
        "team": "blue",
        "script": "blue/pcap_hunter.py",
        "desc": "Network packet dissection for port scans, plaintext creds (HTTP/FTP), and DNS tunnels",
        "syntax": "<capture.pcap>",
        "example": "traffic.pcapng",
    },
    "triage": {
        "name": "Malware Triage Scanner",
        "team": "blue",
        "script": "blue/malware_triage.py",
        "desc": "Static binary analysis, Shannon entropy, dangerous API imports & suspicious PE/ELF headers",
        "syntax": "<file.exe|elf>",
        "example": "suspect_sample.exe",
    },
    "ioc": {
        "name": "IOC Extractor & Defanger",
        "team": "blue",
        "script": "blue/ioc_extractor.py",
        "desc": "Extract & defang IPv4/v6, URLs, domains, hashes & CVEs into JSON/CSV or STIX 2.1",
        "syntax": "<file|text>",
        "example": "threat_intel_dump.txt",
    },
    "php2shell-detect": {
        "name": "PHP2Shell Web Shell Detector",
        "team": "blue",
        "script": "blue/php2shell_detector.py",
        "desc": "Scan upload folders for polyglot web shells, hidden eval backdoors & Apache/PHP exploit logs",
        "syntax": "<dir|logfile>",
        "example": "/var/www/html/uploads",
    },
    # 🔴 Red Team (Offense)
    "map": {
        "name": "Website Crawler & Site Mapper",
        "team": "red",
        "script": "red/site_mapper.py",
        "desc": "Crawl web applications, map directory trees, discover forms & extract JS API routes/secrets",
        "syntax": "<url> [-m pages]",
        "example": "https://example.com -m 25",
    },
    "headers": {
        "name": "Security Header Scanner",
        "team": "red",
        "script": "red/header_scanner.py",
        "desc": "Audit HTTP security headers, CORS wildcard misconfigurations & TLS posture (Grade A+ to F)",
        "syntax": "<url>",
        "example": "https://example.com",
    },
    "breach": {
        "name": "Password Breach Checker",
        "team": "red",
        "script": "red/breach_checker.py",
        "desc": "Check password exposure in 800M+ breaches via HaveIBeenPwned k-Anonymity SHA-1 API",
        "syntax": "<password>",
        "example": "P@ssw0rd2026",
    },
    "cve": {
        "name": "CVE Dependency Scanner",
        "team": "red",
        "script": "red/cve_scanner.py",
        "desc": "Scan requirements.txt / package.json against OSV.dev & NIST NVD for known vulnerabilities",
        "syntax": "<requirements.txt>",
        "example": "requirements.txt",
    },
    "jwt": {
        "name": "JWT Security Auditor",
        "team": "red",
        "script": "red/jwt_auditor.py",
        "desc": "Audit JSON Web Tokens for alg:none bypass, weak HMAC secrets brute-force & claims tampering",
        "syntax": "<token>",
        "example": "eyJhbGciOi...",
    },
    "tls": {
        "name": "TLS & Certificate Inspector",
        "team": "red",
        "script": "red/tls_inspector.py",
        "desc": "Inspect SSL/TLS certificate expiry, cipher suites, SAN endpoints & AIA intermediate chains",
        "syntax": "<domain[:port]>",
        "example": "example.com",
    },
    "php2shell-audit": {
        "name": "PHP2Shell Exposure Auditor",
        "team": "red",
        "script": "red/php2shell_auditor.py",
        "desc": "Audit web upload forms against MIME mismatches, .htaccess overrides & extension bypasses",
        "syntax": "<url>",
        "example": "https://example.com/upload.php",
    },
}

# Aliases to guarantee web/CLI naming compatibility
TOOL_ALIASES = {
    "mapper": "map",
    "site_mapper": "map",
    "sitemapper": "map",
    "header": "headers",
    "security_headers": "headers",
    "header_scanner": "headers",
    "phishing": "phish",
    "phishing_analyzer": "phish",
    "malware": "triage",
    "malware_triage": "triage",
    "php2shell_detector": "php2shell-detect",
    "php2shell_detect": "php2shell-detect",
    "php2shell-detector": "php2shell-detect",
    "php2shell_auditor": "php2shell-audit",
    "php2shell_audit": "php2shell-audit",
    "php2shell-auditor": "php2shell-audit",
    "ioc_extractor": "ioc",
    "pcap_hunter": "pcap",
    "log_analyzer": "ssh",
    "ssh_analyzer": "ssh",
    "cve_scanner": "cve",
    "jwt_auditor": "jwt",
    "tls_inspector": "tls",
    "breach_checker": "breach",
}

# Strict whitelist of allowed file extensions per tool to prevent invalid artifact uploads
TOOL_ALLOWED_EXTENSIONS = {
    # Blue Team
    "phish": {".eml", ".msg", ".mbox", ".txt"},
    "pcap": {".pcap", ".pcapng", ".cap"},
    "ssh": {".log", ".txt"},
    "fim": {".json", ".txt", ".db", ".hash", ".baseline"},
    "triage": {".exe", ".dll", ".sys", ".elf", ".bin", ".so", ".sh", ".ps1", ".bat", ".cmd", ".vbs", ".py", ".apk", ".msi", ".scr", ".com"},
    "ioc": {".txt", ".log", ".csv", ".json", ".eml", ".md"},
    "php2shell-detect": {".log", ".txt", ".php", ".phtml", ".php3", ".php4", ".php5", ".htaccess"},
    # Red Team
    "cve": {".txt", ".json", ".xml", ".lock", ".toml", ".pip", ".req"},
}

# In-memory asynchronous job manager
JOBS_LOCK = threading.Lock()
JOBS: dict[str, dict] = {}


def execute_job(job_id: str, tool_key: str, args: list[str]) -> None:
    """Asynchronous background worker that executes a tool and captures streaming stdout."""
    script_rel = TOOLS_CATALOG[tool_key]["script"]
    script_path = TOOLS_DIR / script_rel

    with JOBS_LOCK:
        JOBS[job_id]["status"] = "running"
        JOBS[job_id]["started_at"] = time.time()

    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("NO_COLOR", "1")  # Clean plain text for web rendering

    cmd = [sys.executable, str(script_path), *args]
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )

        output_lines = []
        if proc.stdout:
            for line in iter(proc.stdout.readline, ""):
                output_lines.append(line)
                with JOBS_LOCK:
                    JOBS[job_id]["output"] = "".join(output_lines)

        proc.wait()
        exit_code = proc.returncode

        with JOBS_LOCK:
            JOBS[job_id]["status"] = "completed"
            JOBS[job_id]["exit_code"] = exit_code
            JOBS[job_id]["finished_at"] = time.time()
            JOBS[job_id]["duration"] = round(JOBS[job_id]["finished_at"] - JOBS[job_id]["started_at"], 2)

    except Exception as exc:
        with JOBS_LOCK:
            JOBS[job_id]["status"] = "failed"
            JOBS[job_id]["error"] = str(exc)
            JOBS[job_id]["finished_at"] = time.time()


class AthenaHTTPRequestHandler(SimpleHTTPRequestHandler):
    """Custom multi-threaded HTTP request handler for Athena-Web."""

    server_version = f"Athena-Web/{VERSION}"

    def end_headers(self):
        # Security headers for local application
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    def do_GET(self):
        url = urlparse(self.path)
        path = url.path.rstrip("/")

        # 🟣 Route: Landing Portal (The Hub)
        if path == "" or path == "/index":
            self.serve_template("index.html")
            return

        # 🔴 Route: Offensive Wing (Red Team)
        if path == "/red":
            self.serve_template("red.html")
            return

        # 🔵 Route: Defensive Wing (Blue Team)
        if path == "/blue":
            self.serve_template("blue.html")
            return

        # 🦉 Route: Hidden Easter Egg Credits (/secret)
        if path == "/secret":
            self.serve_template("secret.html")
            return

        # 🤖 Route: robots.txt (CTF / Recon Easter Egg hint for site_mapper)
        if path == "/robots.txt":
            robots_txt = (
                "User-agent: *\n"
                "Allow: /\n"
                "Allow: /red\n"
                "Allow: /blue\n"
                "# Curious operators who enumerate find the truth:\n"
                "Disallow: /secret\n"
            ).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(robots_txt)))
            self.end_headers()
            self.wfile.write(robots_txt)
            return

        # 🔌 REST API: System Status & Health
        if path == "/api/status":
            self.send_json(
                {
                    "status": "online",
                    "suite": "Athena Purple Team Platform",
                    "version": VERSION,
                    "active_jobs": sum(1 for j in JOBS.values() if j.get("status") == "running"),
                    "total_jobs": len(JOBS),
                    "tools_count": len(TOOLS_CATALOG),
                    "server_time": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                }
            )
            return

        # 🔌 REST API: Tools Catalog
        if path == "/api/tools":
            self.send_json(TOOLS_CATALOG)
            return

        # 🔌 REST API: Job Status Polling
        if path.startswith("/api/job/"):
            job_id = path.split("/api/job/", 1)[-1]
            with JOBS_LOCK:
                job = JOBS.get(job_id)
            if not job:
                self.send_error(HTTPStatus.NOT_FOUND, "Job not found")
                return
            self.send_json(job)
            return

        # 📁 Static Files (CSS, JS, SVG)
        if path.startswith("/static/"):
            rel_file = unquote(path.removeprefix("/static/").lstrip("/"))
            file_path = (STATIC_DIR / rel_file).resolve()
            if file_path.is_file() and str(file_path).startswith(str(STATIC_DIR.resolve())):
                self.serve_file(file_path)
                return
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        # 🖼️ Logos Directory
        if path.startswith("/logos/"):
            rel_file = unquote(path.removeprefix("/logos/").lstrip("/"))
            file_path = (BASE_DIR / "logos" / rel_file).resolve()
            if file_path.is_file() and str(file_path).startswith(str((BASE_DIR / "logos").resolve())):
                self.serve_file(file_path)
                return
            self.send_error(HTTPStatus.NOT_FOUND, "Logo not found")
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_POST(self):
        url = urlparse(self.path)
        path = url.path.rstrip("/")

        # 🚀 REST API: Execute Tool Subprocess
        if path == "/api/run":
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0 or length > 1_000_000:
                self.send_error(HTTPStatus.BAD_REQUEST, "Invalid content length")
                return

            try:
                raw_data = self.rfile.read(length).decode("utf-8")
                payload = json.loads(raw_data)
            except Exception as e:
                self.send_json({"error": f"Invalid JSON payload: {e}"}, status=400)
                return

            tool_key = payload.get("tool", "").strip().lower()
            tool_key = TOOL_ALIASES.get(tool_key, tool_key)
            if tool_key not in TOOLS_CATALOG:
                self.send_json({"error": f"Unknown tool: '{tool_key}'"}, status=400)
                return

            is_demo = bool(payload.get("demo", False))
            raw_args = payload.get("args", [])

            if is_demo:
                args = ["--demo"]
            elif isinstance(raw_args, list):
                args = [str(a) for a in raw_args if str(a).strip()]
            elif isinstance(raw_args, str) and raw_args.strip():
                args = shlex.split(raw_args, posix=(os.name != "nt"))
            else:
                args = ["--demo"]

            job_id = uuid.uuid4().hex[:12]
            with JOBS_LOCK:
                JOBS[job_id] = {
                    "id": job_id,
                    "tool": tool_key,
                    "tool_name": TOOLS_CATALOG[tool_key]["name"],
                    "team": TOOLS_CATALOG[tool_key]["team"],
                    "args": args,
                    "status": "queued",
                    "output": "",
                    "exit_code": None,
                    "created_at": time.time(),
                }

            # Launch background worker
            thread = threading.Thread(target=execute_job, args=(job_id, tool_key, args), daemon=True)
            thread.start()

            self.send_json({"job_id": job_id, "status": "queued", "tool": tool_key})
            return

        # 📤 REST API: File Upload for Forensic Triage
        if path == "/api/upload":
            content_type = self.headers.get("Content-Type", "")
            if not content_type.startswith("multipart/form-data"):
                self.send_json({"error": "Expected multipart/form-data"}, status=400)
                return

            length = int(self.headers.get("Content-Length", 0))
            if length <= 0 or length > 50_000_000:
                self.send_error(HTTPStatus.BAD_REQUEST, "Invalid content length (max 50MB)")
                return

            try:
                raw_body = self.rfile.read(length)
                msg_bytes = f"Content-Type: {content_type}\r\n\r\n".encode("utf-8") + raw_body
                msg = email.message_from_bytes(msg_bytes)

                fields: dict[str, str] = {}
                file_parts: list[tuple[str, bytes]] = []

                if msg.is_multipart():
                    for part in msg.get_payload():
                        filename = part.get_filename()
                        name = part.get_param("name", header="content-disposition")
                        if filename:
                            file_parts.append((filename, part.get_payload(decode=True) or b""))
                        else:
                            p = part.get_payload(decode=True)
                            if p and name:
                                fields[name] = p.decode("utf-8", errors="replace").strip()

                if not file_parts:
                    self.send_json({"error": "No file field found in upload"}, status=400)
                    return

                tool_key = fields.get("tool", "").strip().lower()
                canonical_tool = TOOL_ALIASES.get(tool_key, tool_key)

                raw_filename, file_bytes = file_parts[0]
                safe_name = Path(raw_filename).name.replace(" ", "_")
                lower_name = safe_name.lower()
                ext = Path(safe_name).suffix.lower()

                # Strict file extension validation if tool specified or known
                if canonical_tool and canonical_tool in TOOL_ALLOWED_EXTENSIONS:
                    allowed = TOOL_ALLOWED_EXTENSIONS[canonical_tool]
                    is_valid = False
                    if canonical_tool == "ssh" and lower_name in {"auth.log", "syslog", "secure", "messages"}:
                        is_valid = True
                    elif ext in allowed:
                        is_valid = True

                    if not is_valid:
                        allowed_str = ", ".join(sorted(allowed))
                        self.send_json({
                            "status": "error",
                            "error": f"Invalid file type '{ext or lower_name}' for {tool_key}. Allowed extensions: {allowed_str}"
                        }, status=400)
                        return

                # Global sanity check: reject non-forensic media files
                disallowed_media = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".mp4", ".mp3", ".wav", ".avi"}
                if ext in disallowed_media and canonical_tool != "triage":
                    self.send_json({
                        "status": "error",
                        "error": f"Invalid artifact: '{ext}' image/media files are not permitted."
                    }, status=400)
                    return

                save_path = UPLOADS_DIR / f"{uuid.uuid4().hex[:8]}_{safe_name}"
                with open(save_path, "wb") as f:
                    f.write(file_bytes)

                self.send_json({
                    "status": "success",
                    "filename": safe_name,
                    "server_path": str(save_path.resolve()),
                    "path": str(save_path.resolve()),
                    "size_bytes": len(file_bytes),
                })
            except Exception as e:
                self.send_json({"error": f"Upload failed: {e}"}, status=500)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def serve_template(self, filename: str) -> None:
        """Serve an HTML template file."""
        tmpl = TEMPLATES_DIR / filename
        if not tmpl.is_file():
            # Return placeholder HTML until templates are built in subsequent steps
            content = f"""<!DOCTYPE html>
<html>
<head><title>Athena - {filename}</title></head>
<body style="background:#08020e; color:#fff; font-family:sans-serif; text-align:center; padding:50px;">
  <h1 style="color:#d946ef;">Athena Purple Team Suite</h1>
  <p>Template <code>{filename}</code> is being authored in Step 2.2 / 2.3 / 2.4.</p>
</body></html>"""
            data = content.encode("utf-8")
        else:
            data = tmpl.read_bytes()

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        self.wfile.write(data)

    def serve_file(self, file_path: Path) -> None:
        """Serve a static asset with inferred MIME type."""
        mime, _ = mimetypes.guess_type(str(file_path))
        mime = mime or "application/octet-stream"
        data = file_path.read_bytes()

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, payload: dict, status: int = 200) -> None:
        """Helper to send a JSON response."""
        data = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        # Clean terminal logging
        sys.stderr.write(f"[{time.strftime('%H:%M:%S')}] {args[0]} - {args[1]}\n")


def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    """Starts the multi-threaded HTTP server."""
    # Ensure UTF-8 console output
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    server_address = (host, port)
    try:
        httpd = ThreadingHTTPServer(server_address, AthenaHTTPRequestHandler)
    except OSError as e:
        print(f"[!] Error: Could not bind to http://{host}:{port}/ ({e})")
        print("    Another process may be using port 8080. Try: python app.py --port 8081")
        sys.exit(1)

    print(
        f"""
      █████╗ ████████╗██╗  ██╗███████╗███╗   ██╗ █████╗ 
     ██╔══██╗╚══██╔══╝██║  ██║██╔════╝████╗  ██║██╔══██╗
     ███████║   ██║   ███████║█████╗  ██╔██╗ ██║███████║
     ██╔══██║   ██║   ██╔══██║██╔══╝  ██║╚██╗██║██╔══██║
     ██║  ██║   ██║   ██║  ██║███████╗██║ ╚████║██║  ██║
     ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝╚═╝  ╚═╝
              [ Athena Purple Team Suite v2.0 ]
             -- Offensive & Defensive Security --

[*] Server Address : http://{host}:{port}/
[*] Mode           : Localhost Air-Gapped (Zero Cloud Data Leaks)
[*] Multi-Threading: Active (ThreadingHTTPServer)
[*] Tools Loaded   : {len(TOOLS_CATALOG)} (7 Defensive + 7 Offensive)

Press Ctrl+C to stop the server.
"""
    )

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Shutting down Athena-Web server cleanly...")
        httpd.server_close()
        print("[*] Server stopped. Goodbye.")


def main():
    parser = argparse.ArgumentParser(description="Athena-Web: Localhost Purple Team Security Platform")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Host address to bind (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port number to bind (default: {DEFAULT_PORT})")
    args = parser.parse_args()

    run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
