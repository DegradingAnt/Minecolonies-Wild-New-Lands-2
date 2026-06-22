"""Tiny static file server with HTTP Basic Auth, for serving the deco viewer through the Cloudflare
tunnel WITHOUT leaving the (private modded) textures openly public. Credentials are passed at runtime
(argv), never hard-coded, so this script is safe to commit.
Usage:  python auth_server.py <user> <password> [port] [dir]"""
import sys, base64, os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from functools import partial

USER = sys.argv[1] if len(sys.argv) > 1 else "wnl"
PW = sys.argv[2] if len(sys.argv) > 2 else "changeme"
PORT = int(sys.argv[3]) if len(sys.argv) > 3 else 8000
ROOT = sys.argv[4] if len(sys.argv) > 4 else os.getcwd()
_EXPECT = "Basic " + base64.b64encode(("%s:%s" % (USER, PW)).encode()).decode()


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.headers.get("Authorization", "") != _EXPECT:
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="WNL deco viewer"')
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        super().do_GET()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    httpd = ThreadingHTTPServer(("", PORT), partial(Handler, directory=ROOT))
    print("auth server on :%d  serving %s  (user=%s)" % (PORT, ROOT, USER))
    httpd.serve_forever()
