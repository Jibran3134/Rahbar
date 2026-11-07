"""Exercise the localhost gateway against an actual HTTP backend, without Kubernetes."""
import importlib.util
import json
from pathlib import Path
import threading
import subprocess
import sys
from types import SimpleNamespace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest

spec = importlib.util.spec_from_file_location('run_app', Path(__file__).parents[1] / 'run_app.py')
assert spec and spec.loader
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


@pytest.fixture
def gateway():
    seen = []

    class Backend(BaseHTTPRequestHandler):
        def do_POST(self):
            seen.append((self.path, self.headers['Host'], self.rfile.read(int(self.headers['Content-Length']))))
            self.send_response(503)
            self.send_header('Content-Type', 'application/json')
            self.send_header('X-Cache', 'BYPASS')
            self.send_header('X-Request-ID', 'request-123')
            self.end_headers()
            self.wfile.write(b'{"answer":"not ready"}')

        def log_message(self, *_):
            pass

    backend = ThreadingHTTPServer(('127.0.0.1', 0), Backend)
    proxy = ThreadingHTTPServer(('127.0.0.1', 0), launcher.proxy_handler(backend.server_port))
    threads = []
    for server in [backend, proxy]:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        threads.append(thread)
    try:
        yield f'http://127.0.0.1:{proxy.server_port}', seen
    finally:
        for server, thread in zip([backend, proxy], threads):
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


def test_real_ingress_host_body_and_error_headers_are_preserved(gateway):
    url, seen = gateway
    body = json.dumps({'question': 'What is the fee?', 'session_id': 'abc'}).encode()
    response = httpx.post(url + '/api/ask?test=1', content=body, headers={'Content-Type': 'application/json'}, trust_env=False)
    assert seen == [('/api/ask?test=1', 'rahbar.local', body)]
    assert response.status_code == 503
    assert response.json() == {'answer': 'not ready'}
    assert response.headers['X-Cache'] == 'BYPASS'
    assert response.headers['X-Request-ID'] == 'request-123'


def test_oversized_requests_do_not_reach_ingress(gateway):
    url, seen = gateway
    response = httpx.post(url + '/api/ask', content=b'x' * 65537, trust_env=False)
    assert response.status_code == 413
    assert seen == []


def test_occupied_browser_port_does_not_modify_services(monkeypatch):
    server = ThreadingHTTPServer(('127.0.0.1', 0), BaseHTTPRequestHandler)
    monkeypatch.setattr(launcher, 'services', lambda: pytest.fail('Do not touch services on port conflict'))
    try:
        with pytest.raises(OSError):
            launcher.launch(port=server.server_port, check_only=True)
    finally:
        server.server_close()


def test_failed_child_command_shows_diagnostics_and_stops(capsys):
    with pytest.raises(subprocess.CalledProcessError) as error:
        launcher.command([sys.executable, '-c', "import sys; print('child failed'); sys.exit(7)"])
    assert error.value.returncode == 7
    assert 'child failed' in capsys.readouterr().out


@pytest.mark.parametrize('result', [
    {'done':True,'model':'llama3.2:3b'},
    {'done':False,'model':'llama3.2:3b'},
    {'done':True,'model':'wrong-model'},
])
def test_preload_uses_empty_request_and_checks_completion(monkeypatch,result):
    seen=[]
    def post(url,**kwargs):
        seen.append((url,kwargs))
        if url.endswith('/api/show'):
            return httpx.Response(200,json={'thinking':{'values':[False]}},request=httpx.Request('POST',url))
        return httpx.Response(200,json=result,request=httpx.Request('POST',url))
    monkeypatch.setattr(launcher.httpx,'post',post)
    if result['done'] and result['model']=='llama3.2:3b':
        launcher.warm_generation('llama3.2:3b')
    else:
        with pytest.raises(RuntimeError,match='could not preload'):
            launcher.warm_generation('llama3.2:3b')
    assert seen[0][0].endswith('/api/show')
    body=seen[-1][1]['json']
    assert 'prompt' not in body and 'messages' not in body
    assert body['model']=='llama3.2:3b' and body['stream'] is False
    assert body['options']['num_ctx']==4096 and seen[-1][1]['timeout']==180


@pytest.mark.parametrize('values', [[True],['low','medium','high']])
def test_thinking_only_model_fails_before_loading_or_generating(monkeypatch,values):
    def post(url,**kwargs):
        assert url.endswith('/api/show'), 'Reject an incompatible model before spending time loading it'
        return httpx.Response(200,json={'thinking':{'values':values}},request=httpx.Request('POST',url))
    monkeypatch.setattr(launcher.httpx,'post',post)
    with pytest.raises(RuntimeError,match='Instruct'):
        launcher.warm_generation('thinking-only-model')


def test_startup_pulls_the_models_in_the_actual_configmap(monkeypatch,tmp_path):
    config=tmp_path/'k8s/base/configmap.yaml'
    config.parent.mkdir(parents=True)
    config.write_text('data:\n  EMBED_MODEL: example-embed\n  LLM_MODEL: example-instruct:7b\n')
    monkeypatch.setattr(launcher,'ROOT',tmp_path)
    calls=[]
    monkeypatch.setattr(launcher,'command',lambda args,**kwargs:calls.append(args) or '')
    monkeypatch.setattr(launcher,'ready',lambda *args,**kwargs:SimpleNamespace(json=lambda:{
        'models':[{'name':'example-embed:latest'}]}))
    launcher.services()
    assert ['ollama','pull','example-instruct:7b'] in calls
    assert not any('llama3.2:3b' in args for args in calls)
