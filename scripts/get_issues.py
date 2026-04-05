import requests
import json

url = "http://localhost:9000/api/issues/search?componentKeys=api-endpoint-scanner&types=BUG,VULNERABILITY&ps=10"
auth = ("admin", "AdminPassword1!")

try:
    response = requests.get(url, auth=auth)
    data = response.json()
    print("ISSUES:")
    for issue in data.get("issues", []):
        print(f" - [{issue['severity']}] {issue['type']} in {issue.get('component')}: {issue['message']} (Line {issue.get('line')})")
except Exception as e:
    print("Error:", e)
