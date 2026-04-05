import requests

url = "http://localhost:9000/api/user_tokens/generate"
data = {"name": "my-scanner-token-3"}
auth = ("admin", "AdminPassword1!")

try:
    response = requests.post(url, data=data, auth=auth)
    token = response.json().get("token")
    if token:
        with open("token.txt", "w") as f:
            f.write(token)
        print("Token written to token.txt")
    else:
        print("No token found:", response.text)
except Exception as e:
    print("Error:", e)
