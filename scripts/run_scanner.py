import subprocess

def run():
    try:
        with open("token.txt") as f:
            token = f.read().strip()
    except Exception as e:
        print("Failed to read token:", e)
        return

    cmd = [
        "docker", "run", "--rm", 
        "-v", "d:\\Antigravity 2\\API Endpoint Scanner:/usr/src", 
        "--network=host", 
        "-e", "SONAR_HOST_URL=http://localhost:9000", 
        "-e", f"SONAR_TOKEN={token}", 
        "sonarsource/sonar-scanner-cli"
    ]
    print("Running:", " ".join(cmd).replace(token, "***"))
    subprocess.run(cmd)

if __name__ == "__main__":
    run()
