"""One-command Windows real-RAG startup and loopback access to Kubernetes Ingress."""
import argparse
import http.client
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]
HOP_HEADERS = {'connection', 'transfer-encoding', 'keep-alive', 'upgrade',
               'proxy-authenticate', 'proxy-authorization', 'te', 'trailer'}
HIDDEN = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}


class LocalServer(ThreadingHTTPServer):
    allow_reuse_address = False

    def server_bind(self):
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def command(args, capture=False):
    if capture:
        return subprocess.run(args, cwd=ROOT, check=True, text=True, encoding='utf-8',
                              capture_output=True, **HIDDEN).stdout
    # Explicit pipes keep progress visible even for hidden Windows child processes.
    with subprocess.Popen(args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding='utf-8', errors='replace', **HIDDEN) as process:
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end='', flush=True)
        if process.wait():
            raise subprocess.CalledProcessError(process.returncode, args)
    return None


def ready(url, timeout=180):
    deadline = time.monotonic() + timeout
    with httpx.Client(timeout=5, trust_env=False) as client:
        while time.monotonic() < deadline:
            try:
                response = client.get(url)
                if response.status_code == 200:
                    return response
            except httpx.HTTPError:
                pass
            time.sleep(1)
    raise RuntimeError(f'Timed out waiting for {url}')


def detached(args):
    # These shared desktop services intentionally outlive the browser launcher.
    subprocess.Popen(args, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **HIDDEN)


def services():
    try:
        command(['docker', 'info'], capture=True)
    except subprocess.CalledProcessError:
        candidates = [Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs/DockerDesktop/Docker Desktop.exe',
                      Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Docker/Docker/Docker Desktop.exe']
        desktop = next((p for p in candidates if p.is_file()), None)
        if desktop is None:
            raise RuntimeError('Docker Desktop is unavailable. Install it with Linux containers enabled.') from None
        print('Starting Docker Desktop...', flush=True)
        detached([str(desktop)])
        deadline = time.monotonic() + 180
        while True:
            try:
                command(['docker', 'info'], capture=True)
                break
            except subprocess.CalledProcessError:
                if time.monotonic() >= deadline:
                    raise RuntimeError('Docker did not start; check Docker Desktop.') from None
                time.sleep(2)
    try:
        tags = ready('http://127.0.0.1:11434/api/tags', timeout=2).json()
    except RuntimeError:
        print('Starting Ollama...', flush=True)
        detached([shutil.which('ollama') or 'ollama', 'serve'])
        tags = ready('http://127.0.0.1:11434/api/tags', timeout=60).json()
    names = {model['name'] for model in tags['models']}
    config=yaml.safe_load((ROOT/'k8s/base/configmap.yaml').read_text(encoding='utf-8'))['data']
    pull_models = [config['EMBED_MODEL']]
    if config.get('LLM_PROVIDER', 'ollama-host') == 'ollama-host':
        pull_models.append(config['LLM_MODEL'])
    for model in pull_models:
        if model not in names and model + ':latest' not in names:
            print(f'Downloading required model {model} (first run only)...', flush=True)
            command(['ollama', 'pull', model])


def prepare(rebuild):
    def task(name, *args):
        command(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                 '-File', str(ROOT / 'scripts/dev.ps1'), name, *args])
    minikube = next(p for p in [ROOT / '.venv/tools/bin/minikube.exe',
                               ROOT / '.venv/tools/minikube.exe'] if p.exists())
    print('Starting/checking the Rahbar Kubernetes profile...', flush=True)
    try:
        status = json.loads(command([str(minikube), 'status', '-p', 'rahbar', '--output=json'], capture=True))
        running = all(status.get(k) == 'Running' for k in ['Host', 'Kubelet', 'APIServer'])
    except (subprocess.CalledProcessError, ValueError):
        running = False
    if not running:
        task('cluster')
    exists = command(['kubectl', '--context', 'rahbar', '-n', 'rahbar', 'get', 'deployment/api',
                      '--ignore-not-found', '-o', 'name'], capture=True).strip()
    if rebuild or not exists:
        print('Building images and preparing the real corpus; first startup can take several minutes.', flush=True)
        task('images')
        host = command([str(minikube), 'ssh', '-p', 'rahbar', '--', 'getent', 'hosts',
                        'host.minikube.internal'], capture=True).split()[0]
        task('apply', '-HostCidr', host + '/32')
    for workload in ['statefulset/chroma', 'deployment/redis', 'deployment/api', 'deployment/ui']:
        command(['kubectl', '--context', 'rahbar', '-n', 'rahbar', 'rollout', 'status', workload,
                 '--timeout=600s'])


def proxy_handler(backend_port):
    class Proxy(BaseHTTPRequestHandler):
        def forward(self):
            if not self.path.startswith('/') or self.path.startswith('//'):
                self.send_error(400)
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
            except ValueError:
                self.send_error(400)
                return
            if self.headers.get('Transfer-Encoding') or not 0 <= length <= 65536:
                self.send_error(413)
                return
            headers = {k: v for k, v in self.headers.items()
                       if k.lower() not in HOP_HEADERS | {'host', 'content-length'}}
            headers['Host'] = 'rahbar.local'
            connection = http.client.HTTPConnection('127.0.0.1', backend_port, timeout=480)
            try:
                connection.request(self.command, self.path, body=self.rfile.read(length), headers=headers)
                response = connection.getresponse()
                data = response.read()
                self.send_response(response.status)
                for key, value in response.getheaders():
                    if key.lower() not in HOP_HEADERS | {'content-length'}:
                        self.send_header(key, value)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except (OSError, http.client.HTTPException):
                self.send_error(502, 'Rahbar Ingress is unavailable')
            finally:
                connection.close()

        do_GET = forward
        do_POST = forward

        def log_message(self, *_):
            pass  # No user questions or model answers in launcher logs.

    return Proxy


def warm_generation(model):
    print(f'Preloading generation model {model} before opening the app...', flush=True)
    try:
        metadata=httpx.post('http://127.0.0.1:11434/api/show',json={'model':model},
                            timeout=10,trust_env=False)
        metadata.raise_for_status()
        thinking=metadata.json().get('thinking',{})
        values=thinking.get('values')
        if isinstance(values,list) and not any(value is False for value in values):
            raise RuntimeError('This model requires thinking. Use the configured Instruct model '
                               'for bounded JSON generation.')
        response = httpx.post('http://127.0.0.1:11434/api/generate',
            json={'model':model,'stream':False,'keep_alive':'5m','options':{'num_ctx':4096}},
            timeout=180,trust_env=False)
        response.raise_for_status()
        result = response.json()
        if result.get('done') is not True or result.get('model') != model:
            raise ValueError('Unexpected preload response')
    except (httpx.HTTPError, ValueError):
        raise RuntimeError('Ollama could not preload the generation model. Check the local Ollama service.') from None


def launch(port=8090, no_browser=False, check_only=False, rebuild=False):
    directory = ROOT / '.venv/launcher'
    directory.mkdir(parents=True, exist_ok=True)
    # Reserve the public port before modifying runtime state; never kill its current owner.
    server = LocalServer(('127.0.0.1', port), proxy_handler(0))
    server.daemon_threads = True
    process = None
    serving = False
    try:
        services()
        prepare(rebuild)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            backend_port = sock.getsockname()[1]
        server.RequestHandlerClass = proxy_handler(backend_port)
        with (directory / 'port-forward.txt').open('w', encoding='utf-8') as log:
            process = subprocess.Popen(['kubectl', '--context', 'rahbar', '-n', 'ingress-nginx',
                'port-forward', 'svc/ingress-nginx-controller', f'{backend_port}:80',
                '--address=127.0.0.1'], stdout=log, stderr=log, cwd=ROOT, **HIDDEN)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            serving = True
            url = f'http://127.0.0.1:{port}'
            info = ready(url + '/api/info').json()
            if info.get('provider') not in {'ollama-host', 'hosted'} or not info.get('active'):
                raise RuntimeError('Expected a configured provider and a published corpus index.')
            if info.get('provider') == 'ollama-host':
                warm_generation(info['llm_model'])
            home = ready(url)
            if 'RAHBAR' not in home.text:
                raise RuntimeError('Ingress did not serve the Rahbar UI.')
            (directory / 'smoke.json').write_text(json.dumps(dict(url=url, info=info,
                ui_status=home.status_code, real_rag=True), indent=2), encoding='utf-8')
            print(f'RAHBAR is ready: http://localhost:{port}\nKeep this terminal open. Ctrl+C closes browser access; indexed data stays.', flush=True)
            if check_only:
                return
            if not no_browser:
                webbrowser.open(f'http://localhost:{port}')
            while process.poll() is None:
                time.sleep(.5)
            raise RuntimeError(f'Ingress port-forward stopped. See {directory / "port-forward.txt"}')
    finally:
        if serving:
            server.shutdown()
        server.server_close()
        if process is not None and process.poll() is None:
            process.terminate()
            process.wait(timeout=10)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8090)
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--rebuild', action='store_true')
    args = parser.parse_args()
    try:
        launch(args.port, args.no_browser, args.check_only, args.rebuild)
    except KeyboardInterrupt:
        print('\nBrowser access stopped. Rahbar services and data are retained.')
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'RAHBAR could not start: {exc}\nIf the browser port is occupied, use run.cmd -Port 8091.\n')
