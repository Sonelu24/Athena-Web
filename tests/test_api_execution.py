import urllib.request
import json
import time

def test_tool(tool_key, args):
    req = urllib.request.Request(
        'http://127.0.0.1:8080/api/run',
        data=json.dumps({'tool': tool_key, 'args': args}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode('utf-8'))
    job_id = res['job_id']
    print(f"Launched {tool_key} -> job_id {job_id}")

    for _ in range(25):
        time.sleep(0.3)
        with urllib.request.urlopen(f'http://127.0.0.1:8080/api/job/{job_id}') as resp:
            job = json.loads(resp.read().decode('utf-8'))
            if job['status'] in ('completed', 'failed'):
                status = job['status']
                exit_code = job['exit_code']
                out_len = len(job['output'])
                print(f"  {tool_key} done: status={status}, exit={exit_code}, out_len={out_len}")
                first_line = [l.strip() for l in job['output'].splitlines() if l.strip()][:2]
                print(f"  Preview: {first_line}")
                return exit_code == 0
    print(f"  {tool_key} timed out!")
    return False

tests = [
    ('jwt', ['--demo']),
    ('pcap', ['--demo']),
    ('headers', ['--demo']),
    ('ssh', ['--demo']),
    ('breach', ['--demo']),
    ('fim', ['--demo']),
]

passed = 0
for tool, args in tests:
    if test_tool(tool, args):
        passed += 1

print(f"\nAll API tests completed: {passed}/{len(tests)} passed.")
