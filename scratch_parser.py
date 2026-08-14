import json
import sys

try:
    with open('results/experiments/registry.json', 'r') as f:
        data = json.load(f)
except Exception as e:
    sys.exit(1)

recent = [exp for exp in data if exp.get('total_tasks') == 2]

print('| Dataset | Provider | Model | Pass Rate | Avg Latency | Result |')
print('|---|---|---|---|---|---|')

recent.sort(key=lambda x: (x.get('dataset', ''), x.get('config', {}).get('provider', '')))

for exp in recent:
    ds = exp.get('dataset', 'N/A')
    model = exp.get('model', 'N/A')
    metrics = exp.get('metrics', {})
    
    pass_ratio = exp.get('pass_at_1', 0)
    pass_pct = f"{pass_ratio * 100:.0f}%"
    latency = f"{metrics.get('average_latency_ms', 0):.0f}ms"
    
    total = metrics.get('total_tasks', 2)
    passed = int(round(pass_ratio * total))
    failed = total - passed
    
    provider = exp.get('config', {}).get('provider', 'unknown')
    
    print(f"| {ds} | {provider} | {model} | {pass_pct} | {latency} | {passed} passed, {failed} failed |")
