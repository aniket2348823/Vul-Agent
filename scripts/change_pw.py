import requests

url = "http://localhost:9000/api/users/change_password"
data = {
    "login": "admin",
    "previousPassword": "admin",
    "password": "AdminPassword1!"
}
auth = ("admin", "admin")

try:
    response = requests.post(url, data=data, auth=auth)
    print("Status:", response.status_code)
    print("Response:", response.text)
except Exception as e:
    print("Error:", e)
