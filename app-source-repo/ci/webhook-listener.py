#!/usr/bin/env python3
"""
Enterprise Webhook Listener Daemon
Triggers automated CI pipeline upon receiving Git push events.
Simulates GitHub / GitLab / Gitea Enterprise Webhook.
Author: consultant.sachinbhardwaj@gmail.com
"""
import json
import logging
import os
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [WEBHOOK] %(message)s"
)

PORT = int(os.getenv("WEBHOOK_PORT", "9000"))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_SCRIPT = os.path.join(BASE_DIR, "build-and-deploy.sh")

class WebhookHandler(BaseHTTPRequestHandler):
    def _send_response(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))

    def do_GET(self):
        if self.path == "/healthz":
            self._send_response(200, {
                "status": "active",
                "service": "enterprise-webhook-listener",
                "listening_port": PORT
            })
        else:
            self._send_response(404, {"error": "Not Found"})

    def do_POST(self):
        if self.path in ["/webhook", "/"]:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length) if content_length > 0 else b"{}"
            
            try:
                payload = json.loads(post_data.decode("utf-8")) if post_data else {}
            except Exception as e:
                payload = {}

            service = payload.get("service", "core-api")
            target_env = payload.get("env", "dev")
            author = payload.get("author", "consultant.sachinbhardwaj@gmail.com")
            
            logging.info(f"Incoming Webhook: service={service}, env={target_env}, author={author}")

            try:
                # Trigger automated CI build and deploy script
                cmd = [BUILD_SCRIPT, service, target_env]
                process = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=300
                )
                
                success = (process.returncode == 0)
                logging.info(f"CI execution completed with exit code: {process.returncode}")
                
                self._send_response(200 if success else 500, {
                    "status": "success" if success else "failed",
                    "returncode": process.returncode,
                    "service": service,
                    "target_env": target_env,
                    "author": author,
                    "output_tail": process.stdout.splitlines()[-10:] if process.stdout else []
                })
            except Exception as ex:
                logging.error(f"Error executing build script: {str(ex)}")
                self._send_response(500, {"status": "error", "message": str(ex)})
        else:
            self._send_response(404, {"error": "Endpoint not found"})

def run_server():
    server = HTTPServer(("0.0.0.0", PORT), WebhookHandler)
    logging.info(f"Enterprise Webhook Server listening on 0.0.0.0:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
        logging.info("Webhook server stopped.")

if __name__ == "__main__":
    run_server()
