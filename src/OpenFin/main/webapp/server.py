"""OpenFin Webapp — HTTP Server + API Bridge

Serves the frontend SPA and exposes REST API endpoints that connect
the frontend to the backend OpenFin agents (Agent 1, Agent 2) and filesystem.

Usage:
    python server.py                    # Start on port 6161
    python server.py --port 8080        # Custom port
    python server.py --host 0.0.0.0     # Custom host
"""

import os
import sys
import json
import re
import mimetypes
import traceback
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, unquote
from datetime import datetime
from typing import Optional

# ── Paths ──────────────────────────────────────────────────────────────────
SERVER_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SERVER_DIR, ".."))
WEBAPP_DIR = SERVER_DIR
STATIC_DIR = os.path.join(WEBAPP_DIR, "static")
CONFIG_FILE = os.path.join(WEBAPP_DIR, "config", "config.json")

REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports", "base-reports")
INSIGHTS_DIR = os.path.join(PROJECT_ROOT, "reports", "insights")
BASE_GENS_DIR = os.path.join(PROJECT_ROOT, "Agent1", "base-gens")
INSIGHT_GENS_DIR = os.path.join(PROJECT_ROOT, "Agent1", "insight-gens")
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "data", "uploaded-data")

# Agent subagent log paths
AGENT_LOG_PATHS = {
    "Agent 1": {
        "subAgent 1": os.path.join(PROJECT_ROOT, "Agent1", "subAgent1", "log.txt"),
        "subAgent 2": os.path.join(PROJECT_ROOT, "Agent1", "subAgent2", "log.txt"),
        "subAgent 3": os.path.join(PROJECT_ROOT, "Agent1", "subAgent3", "log.txt"),
        "subAgent 4": os.path.join(PROJECT_ROOT, "Agent1", "subAgent4", "log.txt"),
        "subAgent 5": os.path.join(PROJECT_ROOT, "Agent1", "subAgent5", "log.txt"),
    },
    "Agent 2": {
        "subAgent 1": os.path.join(PROJECT_ROOT, "Agent2", "subAgent1", "log.txt"),
        "subAgent 2": os.path.join(PROJECT_ROOT, "Agent2", "subAgent2", "log.txt"),
    }
}

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls'}

# ── Agent imports (lazy, with graceful fallback) ──────────────────────────
_agent1_available = False
_agent2_available = False


def _try_import_agents():
    global _agent1_available, _agent2_available
    try:
        # Ensure project root is on sys.path
        if PROJECT_ROOT not in sys.path:
            sys.path.insert(0, PROJECT_ROOT)

        # Also add the actual project root for 'main' package namespace resolution
        _root = os.path.abspath(os.path.join(SERVER_DIR, "..", ".."))
        if _root not in sys.path:
            sys.path.insert(0, _root)

        try:
            from main.Agent1.main import run_once as agent1_run_once
            globals()['agent1_run_once'] = agent1_run_once
            _agent1_available = True
            print("[server] Agent 1 loaded successfully")
        except ImportError as e:
            print(f"[server] Agent 1 not available: {e}")
            _agent1_available = False

        try:
            from main.Agent2.main import run as agent2_run, reset_memory as agent2_reset
            globals()['agent2_run'] = agent2_run
            globals()['agent2_reset'] = agent2_reset
            _agent2_available = True
            print("[server] Agent 2 loaded successfully")
        except ImportError as e:
            print(f"[server] Agent 2 not available: {e}")
            _agent2_available = False

    except Exception as e:
        print(f"[server] Agent import error: {e}")


# ── LLM Provider Base URLs ───────────────────────────────────────────────

PROVIDER_BASE_URLS = {
    "openai":     "https://api.openai.com/v1",
    "anthropic":  "https://api.anthropic.com/v1",
    "gemini":     "https://generativelanguage.googleapis.com/v1beta",
    "openrouter": "https://openrouter.ai/api/v1",
    "xai":        "https://api.x.ai/v1",
    "deepseek":   "https://api.deepseek.com/v1",
    "groq":       "https://api.groq.com/openai/v1",
    "together":   "https://api.together.xyz/v1",
    "mistral":    "https://api.mistral.ai/v1",
}


# ── Configuration Helpers ─────────────────────────────────────────────────

def _load_config() -> dict:
    """Load configuration from config.json. Returns defaults if not found."""
    defaults = {
        "provider": "",
        "llm_key": "",
        "llm_model": "",
        "tavily_key": "",
    }
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                defaults.update(data)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[server] Config load error: {e}")
    return defaults


def _save_config(config: dict) -> bool:
    """Merge and save configuration to config.json."""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        existing = _load_config()
        existing.update(config)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(existing, f, indent=4)
        return True
    except OSError as e:
        print(f"[server] Config save error: {e}")
        return False


def _apply_config_to_env(config: dict):
    """Set environment variables from config for subagent consumption."""
    provider = config.get("provider", "").strip().lower()
    llm_key = config.get("llm_key", "")
    llm_model = config.get("llm_model", "").strip()
    tavily_key = config.get("tavily_key", "")

    # Set LLM provider and key
    if provider and llm_key:
        os.environ["LLM_PROVIDER"] = provider
        os.environ["LLM_API_KEY"] = llm_key
        os.environ["OPENAI_API_KEY"] = llm_key  # Also set legacy var for backwards compat

        # Auto-set base URL from provider
        base_url = PROVIDER_BASE_URLS.get(provider, "")
        if base_url:
            os.environ["LLM_BASE_URL"] = base_url
            os.environ["OPENAI_BASE_URL"] = base_url
    else:
        # Clear env vars if no provider configured
        os.environ.pop("LLM_PROVIDER", None)
        os.environ.pop("LLM_API_KEY", None)
        os.environ.pop("LLM_BASE_URL", None)

    # Set model (use default if none provided)
    if llm_model:
        os.environ["LLM_MODEL"] = llm_model
    else:
        os.environ.setdefault("LLM_MODEL", "openai/gpt-oss-120b:free")

    # Set Tavily key
    if tavily_key:
        os.environ["TAVILY_API_KEY"] = tavily_key
    else:
        os.environ.pop("TAVILY_API_KEY", None)


def _mask_key(key: str) -> str:
    """Mask an API key showing only the prefix and last 4 characters."""
    if not key or len(key) < 8:
        return ""
    return key[:5] + "..." + key[-4:]


# ── File Listing Helpers ─────────────────────────────────────────────────

def _list_pdf_files(directory: str, json_source_dir: str) -> list:
    """List PDF files in a directory with descriptions from matching JSONs."""
    results = []
    if not os.path.isdir(directory):
        return results

    for fname in sorted(os.listdir(directory)):
        if not fname.lower().endswith('.pdf'):
            continue
        fpath = os.path.join(directory, fname)
        try:
            stat = os.stat(fpath)
            size_bytes = stat.st_size
            modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
        except OSError:
            size_bytes = 0
            modified = ""

        # Try to find matching JSON for description
        stem = os.path.splitext(fname)[0]
        description = ""
        if os.path.isdir(json_source_dir):
            for jfname in os.listdir(json_source_dir):
                if os.path.splitext(jfname)[0] == stem and jfname.endswith('.json'):
                    try:
                        with open(os.path.join(json_source_dir, jfname), 'r') as jf:
                            jdata = json.load(jf)
                        # Extract first line of description from JSON content
                        description = _extract_description(jdata)
                    except (OSError, json.JSONDecodeError):
                        pass
                    break

        results.append({
            "name": fname,
            "description": description,
            "size_bytes": size_bytes,
            "modified": modified
        })
    return results


def _extract_description(jdata: dict) -> str:
    """Extract a one-sentence description from a report JSON."""
    if not isinstance(jdata, dict):
        return ""

    # Try common description fields
    for key in ['description', 'summary', 'introduction', 'overview']:
        val = jdata.get(key, '')
        if isinstance(val, str) and val.strip():
            return val.strip()[:200]

    # Try first value that looks like a description
    for key, val in jdata.items():
        if isinstance(val, str) and len(val) > 20 and len(val) < 300:
            return val.strip()[:200]

    # Try nested: first section content
    for key, val in jdata.items():
        if isinstance(val, dict):
            for k2, v2 in val.items():
                if isinstance(v2, str) and len(v2) > 20:
                    return v2.strip()[:200]

    return ""


def _read_activity_log(log_path: str) -> str:
    """Read the last activity from a subagent's log.txt."""
    try:
        if os.path.exists(log_path):
            with open(log_path, 'r') as f:
                content = f.read().strip()
            if not content:
                return "idle"
            # Extract status after timestamp if present
            if "] " in content:
                status = content.split("] ", 1)[-1].strip()
            else:
                status = content.strip()
            return status if status else "idle"
    except OSError:
        pass
    return "unknown"


def _sanitize_filename(filename: str) -> Optional[str]:
    """Validate and sanitize a filename to prevent path traversal."""
    # Remove any path components
    name = os.path.basename(unquote(filename))
    # Prevent path traversal
    if '..' in name or '/' in name or '\\' in name:
        return None
    if not name:
        return None
    return name


# ── HTTP Request Handler ──────────────────────────────────────────────────

class OpenFinHandler(SimpleHTTPRequestHandler):
    """Extended HTTP handler that serves the SPA and REST API."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEBAPP_DIR, **kwargs)

    def log_message(self, format, *args):
        """Override to add timestamp to log messages."""
        ts = datetime.now().isoformat(timespec="seconds")
        sys.stderr.write(f"[{ts}] {args[0]} {args[1]} {args[2]}\n")

    # ── Routing ──────────────────────────────────────────────────────────

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/') or '/'

        # API Routes
        if path.startswith('/api/'):
            self._handle_api_get(path)
            return

        # Serve static files
        if path.startswith('/static/'):
            self._serve_static(path)
            return

        # Serve index.html for SPA root
        if path == '/':
            self._serve_file(os.path.join(WEBAPP_DIR, 'index.html'), 'text/html')
            return

        # Try to serve file directly (for other static assets)
        self._serve_static(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')

        if path.startswith('/api/'):
            self._handle_api_post(path)
            return

        self._send_json_error(404, "Not found")

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')

        if path.startswith('/api/'):
            self._handle_api_delete(path)
            return

        self._send_json_error(404, "Not found")

    # ── API GET Handler ──────────────────────────────────────────────────

    def _handle_api_get(self, path: str):
        """Route GET API requests to appropriate handlers."""

        if path == '/api/reports':
            self._list_files('reports')
        elif path == '/api/insights':
            self._list_files('insights')
        elif path.startswith('/api/reports/'):
            filename = _sanitize_filename(path[len('/api/reports/'):])
            self._serve_pdf(filename, REPORTS_DIR)
        elif path.startswith('/api/insights/'):
            filename = _sanitize_filename(path[len('/api/insights/'):])
            self._serve_pdf(filename, INSIGHTS_DIR)
        elif path == '/api/agents/status':
            self._get_agents_status()
        elif path == '/api/config':
            self._get_config()
        elif path == '/api/health':
            self._health_check()
        else:
            self._send_json_error(404, "Endpoint not found")

    # ── API POST Handler ─────────────────────────────────────────────────

    def _handle_api_post(self, path: str):
        if path == '/api/upload':
            self._handle_upload()
        elif path == '/api/chat':
            self._handle_chat()
        elif path == '/api/chat/reset':
            self._handle_chat_reset()
        elif path == '/api/config':
            self._handle_config_save()
        else:
            self._send_json_error(404, "Endpoint not found")

    # ── API DELETE Handler ───────────────────────────────────────────────

    def _handle_api_delete(self, path: str):
        if path.startswith('/api/reports/'):
            filename = _sanitize_filename(path[len('/api/reports/'):])
            self._delete_file(filename, REPORTS_DIR, BASE_GENS_DIR, 'report')
        elif path.startswith('/api/insights/'):
            filename = _sanitize_filename(path[len('/api/insights/'):])
            self._delete_file(filename, INSIGHTS_DIR, INSIGHT_GENS_DIR, 'insight')
        else:
            self._send_json_error(404, "Endpoint not found")

    # ── API Endpoint Implementations ─────────────────────────────────────

    def _list_files(self, file_type: str):
        """List PDF files for reports or insights."""
        try:
            if file_type == 'reports':
                files = _list_pdf_files(REPORTS_DIR, BASE_GENS_DIR)
            else:
                files = _list_pdf_files(INSIGHTS_DIR, INSIGHT_GENS_DIR)
            self._send_json(files)
        except Exception as e:
            self._send_json_error(500, f"Failed to list {file_type}: {str(e)}")

    def _serve_pdf(self, filename: Optional[str], directory: str):
        """Serve a PDF file for preview or download.
        Supports Range headers for large file streaming.
        """
        if not filename:
            self._send_json_error(400, "Filename is required")
            return

        fpath = os.path.join(directory, filename)
        if not os.path.isfile(fpath):
            self._send_json_error(404, f"File not found: {filename}")
            return

        try:
            file_size = os.path.getsize(fpath)
            range_header = self.headers.get('Range', '')

            if range_header and range_header.startswith('bytes='):
                # Parse Range header
                try:
                    ranges = range_header[6:].strip()
                    start_str, end_str = ranges.split('-', 1)
                    start = int(start_str) if start_str else 0
                    end = int(end_str) if end_str else file_size - 1

                    if start < 0:
                        start = 0
                    if end >= file_size:
                        end = file_size - 1
                    if start > end:
                        self._send_json_error(416, "Range not satisfiable")
                        return

                    content_length = end - start + 1
                    with open(fpath, 'rb') as f:
                        f.seek(start)
                        content = f.read(content_length)

                    self.send_response(206)
                    self.send_header('Content-Type', 'application/pdf')
                    self.send_header('Content-Length', str(content_length))
                    self.send_header('Content-Range',
                        f'bytes {start}-{end}/{file_size}')
                    self.send_header('Accept-Ranges', 'bytes')
                    self.send_header('Content-Disposition',
                        f'inline; filename="{filename}"')
                    self.end_headers()
                    self.wfile.write(content)
                    return
                except (ValueError, IndexError):
                    # Fall through to full file send on parse error
                    pass

            # Full file (no Range header)
            with open(fpath, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'application/pdf')
            self.send_header('Content-Length', str(file_size))
            self.send_header('Content-Disposition',
                f'inline; filename="{filename}"')
            self.send_header('Accept-Ranges', 'bytes')
            self.end_headers()
            self.wfile.write(content)
        except OSError as e:
            self._send_json_error(500, f"Error reading file: {str(e)}")

    def _delete_file(self, filename: Optional[str], pdf_dir: str,
                     json_dir: str, file_type: str):
        """Delete a PDF and its source JSON."""
        if not filename:
            self._send_json_error(400, "Filename is required")
            return

        pdf_path = os.path.join(pdf_dir, filename)
        stem = os.path.splitext(filename)[0]

        deleted_pdf = False
        deleted_json = False

        # Delete PDF
        if os.path.isfile(pdf_path):
            try:
                os.remove(pdf_path)
                deleted_pdf = True
            except OSError as e:
                self._send_json_error(500, f"Failed to delete PDF: {str(e)}")
                return
        else:
            self._send_json_error(404, f"{file_type.capitalize()} not found: {filename}")
            return

        # Delete matching JSON
        if os.path.isdir(json_dir):
            for jfname in os.listdir(json_dir):
                if os.path.splitext(jfname)[0] == stem and jfname.endswith('.json'):
                    try:
                        os.remove(os.path.join(json_dir, jfname))
                        deleted_json = True
                    except OSError:
                        pass
                    break

        self._send_json({
            "success": True,
            "deleted_pdf": deleted_pdf,
            "deleted_json": deleted_json
        })

    def _handle_upload(self):
        """Handle file upload — saves to upload directory and triggers Agent 1.
        Uses a safe multipart parser that reads raw bytes and extracts the file
        field by splitting on the boundary.
        """
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > MAX_UPLOAD_SIZE:
            self._send_json_error(413, "File exceeds maximum upload size (50MB)")
            return

        content_type = self.headers.get('Content-Type', '')
        if 'multipart/form-data' not in content_type:
            self._send_json_error(400, "Expected multipart/form-data")
            return

        try:
            # Extract boundary string from Content-Type header
            boundary = None
            for part in content_type.split(';'):
                part = part.strip()
                if part.startswith('boundary='):
                    boundary = part[len('boundary='):].strip()
                    # Remove surrounding quotes if present
                    if boundary.startswith('"') and boundary.endswith('"'):
                        boundary = boundary[1:-1]
                    break

            if not boundary:
                self._send_json_error(400, "No boundary found in Content-Type")
                return

            # Read raw request body
            boundary_bytes = boundary.encode('latin-1')
            raw_data = self.rfile.read(content_length)

            # Split by boundary markers
            separator = b'--' + boundary_bytes
            parts = raw_data.split(separator)

            for part in parts:
                # Skip empty parts, closing boundary, and preamble/postamble
                part = part.strip(b'\r\n')
                if not part or part == b'--':
                    continue

                # Find header/body split (double CRLF)
                header_end = part.find(b'\r\n\r\n')
                if header_end == -1:
                    continue

                headers_raw = part[:header_end].decode('utf-8', errors='replace')
                body_data = part[header_end + 4:]

                # Check if this part has a file
                if 'name="file"' not in headers_raw and 'name=\'file\'' not in headers_raw:
                    continue

                # Extract filename
                fn_match = re.search(r'filename="([^"]*)"', headers_raw)
                if not fn_match:
                    continue
                filename = os.path.basename(fn_match.group(1))
                if not filename:
                    continue

                # Validate extension
                ext = os.path.splitext(filename)[1].lower()
                if ext not in ALLOWED_EXTENSIONS:
                    self._send_json_error(400,
                        f"Invalid file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")
                    return

                # Remove trailing CRLF before the closing boundary
                file_bytes = body_data.rstrip(b'\r\n').rstrip(b'--').rstrip(b'\r\n')

                # Save file
                os.makedirs(UPLOAD_DIR, exist_ok=True)
                dest_path = os.path.join(UPLOAD_DIR, filename)

                # Avoid overwriting
                counter = 1
                while os.path.exists(dest_path):
                    name, ext = os.path.splitext(filename)
                    dest_path = os.path.join(UPLOAD_DIR, f"{name}_{counter}{ext}")
                    counter += 1

                with open(dest_path, 'wb') as f:
                    f.write(file_bytes)

                # Trigger Agent 1 pipeline asynchronously
                pipeline_started = False
                if _agent1_available:
                    try:
                        import threading
                        threading.Thread(
                            target=_run_agent1_pipeline,
                            args=(filename,),
                            daemon=True
                        ).start()
                        pipeline_started = True
                    except Exception as e:
                        print(f"[server] Failed to start Agent 1: {e}")

                self._send_json({
                    "success": True,
                    "filename": os.path.basename(dest_path),
                    "pipeline_started": pipeline_started
                })
                return

            self._send_json_error(400, "No file found in upload")

        except Exception as e:
            self._send_json_error(500, f"Upload failed: {str(e)}")

    def _handle_chat(self):
        """Handle chat prompt to Agent 2."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(content_length)
            data = json.loads(raw.decode('utf-8'))

            prompt = data.get('prompt', '').strip()
            if not prompt:
                self._send_json_error(400, "Prompt is required")
                return

            history = data.get('history', [])

            # If frontend sends an empty history (new conversation), reset Agent 2 memory
            if not history:
                if _agent2_available:
                    try:
                        agent2_reset()
                    except Exception:
                        pass

            if _agent2_available:
                try:
                    answer = agent2_run(prompt)
                    # Split answer into main answer and caveats if present
                    caveats = ""
                    if "\n\n---\n" in answer:
                        parts = answer.split("\n\n---\n", 1)
                        answer = parts[0]
                        caveats = parts[1]

                    self._send_json({
                        "answer": answer,
                        "caveats": caveats
                    })
                except Exception as e:
                    self._send_json_error(500, f"Agent 2 error: {str(e)}")
            else:
                # Fallback response when Agent 2 is not available
                self._send_json({
                    "answer": (
                        "Agent 2 (Financial Advisor) is not currently available. "
                        "The module could not be loaded. Please ensure the Agent 2 "
                        "dependencies are properly installed."
                    ),
                    "caveats": "Agent 2 module not loaded"
                })
        except json.JSONDecodeError:
            self._send_json_error(400, "Invalid JSON body")
        except Exception as e:
            self._send_json_error(500, f"Chat error: {str(e)}")

    def _handle_chat_reset(self):
        """Reset Agent 2's conversation memory."""
        if _agent2_available:
            try:
                agent2_reset()
            except Exception as e:
                print(f"[server] Agent 2 reset error: {e}")
        self._send_json({"success": True})

    def _get_agents_status(self):
        """Get current activity status of all agents and subagents."""
        status = {}
        for agent_name, subagents in AGENT_LOG_PATHS.items():
            status[agent_name] = {}
            for sub_name, log_path in subagents.items():
                status[agent_name][sub_name] = _read_activity_log(log_path)
        self._send_json(status)

    def _get_config(self):
        """Get current configuration with masked keys."""
        config = _load_config()
        masked = {
            "provider": config.get("provider", ""),
            "llm_key": _mask_key(config.get("llm_key", "")),
            "llm_model": config.get("llm_model", ""),
            "tavily_key": _mask_key(config.get("tavily_key", "")),
        }
        self._send_json(masked)

    def _handle_config_save(self):
        """Save configuration values and update environment variables."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(content_length)
            data = json.loads(raw.decode('utf-8'))

            success = _save_config(data)
            if success:
                reloaded = _load_config()
                _apply_config_to_env(reloaded)
                self._send_json({"success": True})
            else:
                self._send_json_error(500, "Failed to save configuration")
        except json.JSONDecodeError:
            self._send_json_error(400, "Invalid JSON body")
        except Exception as e:
            self._send_json_error(500, f"Config save error: {str(e)}")

    def _health_check(self):
        """Health check endpoint."""
        self._send_json({
            "status": "ok",
            "agent1_available": _agent1_available,
            "agent2_available": _agent2_available,
            "timestamp": datetime.now().isoformat()
        })

    # ── Static File Serving ──────────────────────────────────────────────

    def _serve_static(self, path: str):
        """Serve a static file from the filesystem."""
        # Security: prevent path traversal
        safe_path = os.path.normpath(path).lstrip('/')
        if '..' in safe_path:
            self._send_json_error(403, "Forbidden")
            return

        file_path = os.path.join(WEBAPP_DIR, safe_path)

        if not os.path.isfile(file_path):
            self._send_json_error(404, "File not found")
            return

        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            mime_type = 'application/octet-stream'

        self._serve_file(file_path, mime_type)

    def _serve_file(self, file_path: str, mime_type: str):
        """Read and serve a file with the given MIME type."""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', mime_type)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(content)
        except OSError as e:
            self._send_json_error(500, f"Error reading file: {str(e)}")

    # ── JSON Response Helpers ────────────────────────────────────────────

    def _send_json(self, data: dict):
        """Send a JSON response with 200 status."""
        content = json.dumps(data).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json_error(self, status_code: int, message: str, detail: str = ""):
        """Send a JSON error response."""
        error_data = {"error": message}
        if detail:
            error_data["detail"] = detail
        content = json.dumps(error_data).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)


# ── Agent 1 Pipeline Runner (Background) ─────────────────────────────────

def _run_agent1_pipeline(filename: str):
    """Run Agent 1 pipeline in background thread."""
    try:
        print(f"[server] Starting Agent 1 pipeline for: {filename}")
        result = agent1_run_once()
        print(f"[server] Agent 1 pipeline complete: {result.get('status', 'unknown')}")
    except Exception as e:
        print(f"[server] Agent 1 pipeline error: {e}")
        traceback.print_exc()


# ── Server Entry Point ───────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="OpenFin Webapp Server")
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=6161, help='Port to listen on')
    parser.add_argument('--no-agents', action='store_true',
                        help='Skip importing agent modules')
    args = parser.parse_args()

    # Create necessary directories
    for d in [UPLOAD_DIR, REPORTS_DIR, INSIGHTS_DIR, BASE_GENS_DIR,
              INSIGHT_GENS_DIR, os.path.dirname(CONFIG_FILE)]:
        os.makedirs(d, exist_ok=True)

    # Set API keys from config file as environment variables for subagents
    _cfg = _load_config()
    _apply_config_to_env(_cfg)
    provider_name = _cfg.get("provider", "") or "not configured"
    print(f"[server] LLM Provider: {provider_name}, "
          f"TAVILY_API_KEY: {'set' if os.environ.get('TAVILY_API_KEY') else 'MISSING'}")

    # Try to import agent modules
    if not args.no_agents:
        _try_import_agents()
    else:
        print("[server] Agent imports skipped (--no-agents)")

    # Start server (threaded to allow concurrent requests like sidebar polling during chat)
    server = ThreadingHTTPServer((args.host, args.port), OpenFinHandler)
    print(f"\n{'=' * 60}")
    print(f"  OpenFin Webapp Server")
    print(f"  Host: {args.host}")
    print(f"  Port: {args.port}")
    print(f"  URL:  http://{args.host}:{args.port}")
    print(f"  Agent 1: {'Available' if _agent1_available else 'Not loaded'}")
    print(f"  Agent 2: {'Available' if _agent2_available else 'Not loaded'}")
    print(f"{'=' * 60}\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.server_close()
        print("Server stopped.")


if __name__ == '__main__':
    main()
