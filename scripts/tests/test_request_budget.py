"""Keep CPU model budgets inside browser, Ingress, evaluator and drain budgets."""
import ast
from pathlib import Path

import yaml

ROOT=Path(__file__).resolve().parents[2]


def test_default_generation_budget_fits_all_outer_request_layers():
    config=yaml.safe_load((ROOT/'k8s/base/configmap.yaml').read_text())['data']
    api=yaml.safe_load((ROOT/'k8s/base/api.yaml').read_text())
    ingress=yaml.safe_load((ROOT/'k8s/base/ingress.yaml').read_text())
    model=float(config['LLM_TIMEOUT_SECONDS'])
    assert model==180
    # Two validation attempts + the bounded query embedding call + preStop drain.
    budget=2*model+60+10
    assert api['spec']['template']['spec']['terminationGracePeriodSeconds']>budget
    assert float(ingress['metadata']['annotations']['nginx.ingress.kubernetes.io/proxy-read-timeout'])>budget
    for filename,call_name in [('scripts/run_app.py','HTTPConnection'),('eval/run_eval.py','Client')]:
        tree=ast.parse((ROOT/filename).read_text())
        timeouts=[kw.value.value for node in ast.walk(tree)
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr==call_name
            for kw in node.keywords if kw.arg=='timeout' and isinstance(kw.value,ast.Constant)
            and isinstance(kw.value.value,(int,float))]
        assert any(t>budget for t in timeouts),filename
