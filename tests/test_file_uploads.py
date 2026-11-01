import urllib.request
import urllib.error
import json
import uuid

BASE_URL = "http://127.0.0.1:8080"

def upload_file(tool_name: str, filename: str, content: bytes):
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    
    parts = []
    # Add tool field
    parts.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="tool"\r\n\r\n'
        f"{tool_name}\r\n"
    )
    # Add file field
    parts.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    )
    
    body = parts[0].encode("utf-8") + parts[1].encode("utf-8") + content + f"\r\n--{boundary}--\r\n".encode("utf-8")
    
    req = urllib.request.Request(
        f"{BASE_URL}/api/upload",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return resp.status, data
    except urllib.error.HTTPError as e:
        data = json.loads(e.read().decode("utf-8"))
        return e.code, data

print("[*] Testing Athena File Upload Restrictions...")

# Test 1: Upload .png to pcap -> EXPECT 400 REJECT
status, data = upload_file("pcap", "bad_capture.png", b"fake image png data")
print(f"Test 1 (.png -> pcap): status={status}, error='{data.get('error')}'")
assert status == 400, f"Expected 400, got {status}"
assert "Invalid file type" in data.get("error", ""), "Expected file type error message"

# Test 2: Upload .pcap to pcap -> EXPECT 200 SUCCESS
status, data = upload_file("pcap", "network.pcap", b"\xd4\xc3\xb2\xa1\x02\x00\x04\x00" + b"\x00" * 32)
print(f"Test 2 (.pcap -> pcap): status={status}, success={data.get('status')}")
assert status == 200, f"Expected 200, got {status}"
assert data.get("status") == "success"

# Test 3: Upload .png to phishing -> EXPECT 400 REJECT
status, data = upload_file("phishing", "fake_email.png", b"fake png data")
print(f"Test 3 (.png -> phishing): status={status}, error='{data.get('error')}'")
assert status == 400, f"Expected 400, got {status}"
assert "Invalid file type" in data.get("error", "")

# Test 4: Upload .eml to phishing -> EXPECT 200 SUCCESS
status, data = upload_file("phishing", "alert.eml", b"From: attacker@evil.com\r\nSubject: Urgent\r\n\r\nClick here")
print(f"Test 4 (.eml -> phishing): status={status}, success={data.get('status')}")
assert status == 200, f"Expected 200, got {status}"
assert data.get("status") == "success"

# Test 5: Upload .png to cve -> EXPECT 400 REJECT
status, data = upload_file("cve", "dependencies.png", b"fake png data")
print(f"Test 5 (.png -> cve): status={status}, error='{data.get('error')}'")
assert status == 400, f"Expected 400, got {status}"
assert "Invalid file type" in data.get("error", "")

# Test 6: Upload .txt to cve -> EXPECT 200 SUCCESS
status, data = upload_file("cve", "requirements.txt", b"flask==2.0.1\r\nrequests==2.25.1\r\n")
print(f"Test 6 (.txt -> cve): status={status}, success={data.get('status')}")
assert status == 200, f"Expected 200, got {status}"
assert data.get("status") == "success"

# Test 7: Verify dropzone is gone from /blue HTML
with urllib.request.urlopen(f"{BASE_URL}/blue") as resp:
    blue_html = resp.read().decode("utf-8")
    assert 'class="dropzone-box"' not in blue_html, "Found dropzone-box still present in blue.html!"
    assert 'id="dropzone"' not in blue_html, "Found id='dropzone' still present in blue.html!"
    assert 'Drop forensic artifacts here' not in blue_html, "Found dropzone text in blue.html!"
    print("Test 7 (Dropzone removed from /blue): PASSED - dropzone is completely gone.")

print("\n[SUCCESS] ALL 7 FILE UPLOAD & RESTRICTION TESTS PASSED!")
