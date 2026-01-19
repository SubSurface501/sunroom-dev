
import sys
import json

log_output = sys.stdin.read()
# The output from gcloud --format=json is already a valid JSON array string
log_entries = json.loads(log_output)

found_404 = False
# Now log_entries is a list of dicts, so entry will be a dict
for entry in log_entries:
    log_name = entry.get("logName", "")

    if "cloudaudit.googleapis.com" in log_name:
        continue # Skip audit logs

    # Check for 404 in httpRequest.status for request logs
    if "run.googleapis.com/requests" in log_name and "httpRequest" in entry and entry["httpRequest"].get("status") == 404:
        request_url = entry["httpRequest"].get("requestUrl", "N/A")
        print(f"Found 404 in request log for URL: {request_url}")
        found_404 = True
        break

    # Check in textPayload (for application logs)
    if "textPayload" in entry and "404 Not Found" in entry["textPayload"]:
        print(f"Found 404 in textPayload: {entry['textPayload']}")
        found_404 = True
        break
    
    # Check in jsonPayload (if it exists and contains a message field)
    if "jsonPayload" in entry and "message" in entry["jsonPayload"] and "404 Not Found" in entry["jsonPayload"]["message"]:
        print(f"Found 404 in jsonPayload: {entry['jsonPayload']['message']}")
        found_404 = True
        break

if not found_404:
    print("No '404 Not Found' entries found in application logs.")
