import requests

url = "http://localhost:9000/api/measures/component?component=api-endpoint-scanner&metricKeys=bugs,vulnerabilities,code_smells,coverage"
auth = ("admin", "AdminPassword1!")

try:
    response = requests.get(url, auth=auth)
    data = response.json()
    metrics = data.get("component", {}).get("measures", [])
    print("SONARQUBE METRICS:")
    for measure in metrics:
        print(f" - {measure['metric']}: {measure['value']}")
except Exception as e:
    print("Error:", e)
