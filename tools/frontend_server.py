"""Local frontend gateway. Django renders templates on the separate backend port.

Development only; production uses nginx. Streams request/response bodies without
buffering MRI uploads in memory. Binds loopback and never spawns another service.
"""
import argparse
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOP_HEADERS = {'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
               'te', 'trailer', 'transfer-encoding', 'upgrade'}


class Gateway(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def proxy(self):
        if self.headers.get('Transfer-Encoding'):
            self.send_error(411, 'Content-Length required')
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            self.send_error(400)
            return
        if length < 0 or length > 260 * 1024 * 1024:
            self.send_error(413, 'Upload exceeds gateway limit')
            return
        if not self.path.startswith('/') or self.path.startswith('//'):
            self.send_error(400)
            return
        backend = http.client.HTTPConnection('127.0.0.1', self.server.backend_port, timeout=180)
        try:
            backend.putrequest(self.command, self.path, skip_host=True, skip_accept_encoding=True)
            for key, value in self.headers.items():
                if key.lower() not in HOP_HEADERS:
                    backend.putheader(key, value)
            backend.endheaders()
            remaining = length
            while remaining:
                chunk = self.rfile.read(min(65536, remaining))
                if not chunk:
                    raise ConnectionError('Incomplete upload')
                backend.send(chunk)
                remaining -= len(chunk)
            response = backend.getresponse()
            self.send_response(response.status)
            for key, value in response.getheaders():
                if key.lower() not in HOP_HEADERS:
                    self.send_header(key, value)
            self.send_header('Connection', 'close')
            self.end_headers()
            if self.command != 'HEAD':
                while chunk := response.read(65536):
                    self.wfile.write(chunk)
            self.close_connection = True
        except (OSError, http.client.HTTPException):
            self.send_error(502, 'Django backend unavailable. Start it on the configured backend port.')
        finally:
            backend.close()

    do_GET = do_POST = do_HEAD = do_OPTIONS = proxy


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=9130)
    parser.add_argument('--backend-port', type=int, default=9131)
    args = parser.parse_args()
    if args.port == args.backend_port:
        parser.error('Frontend and backend ports must differ.')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Gateway)
    server.backend_port = args.backend_port
    print(f'NeuroVision frontend http://127.0.0.1:{args.port} -> Django :{args.backend_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
