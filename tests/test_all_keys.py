import urllib.request
import json
import time

tools_to_test = [
    # Red Wing buttons
    'mapper', 'headers', 'breach', 'cve', 'jwt', 'tls', 'php2shell-audit',
    # Blue Wing buttons
    'ssh', 'fim', 'phishing', 'pcap', 'malware', 'ioc', 'php2shell-detect'
]

passed = 0
failed = []

for tool in tools_to_test:
    req = urllib.request.Request(
        'http://127.0.0.1:8080/api/run',
        data=json.dumps({'tool': tool, 'args': ['--demo']}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode('utf-8'))
        if 'error' in res:
            failed.append((tool, res['error']))
            continue
        job_id = res['job_id']
        time.sleep(0.4)
        with urllib.request.urlopen(f'http://127.0.0.1:8080/api/job/{job_id}') as resp:
            job = json.loads(resp.read().decode('utf-8'))
            status = job.get('status')
            canonical = job.get('tool')
            print(f"✓ {tool:18} -> job={job_id[:8]}, status={status}, canonical={canonical}")
            passed += 1
    except Exception as e:
        failed.append((tool, str(e)))

print(f"\nTotal passed: {passed}/{len(tools_to_test)}")
if failed:
    print("FAILED:", failed)
