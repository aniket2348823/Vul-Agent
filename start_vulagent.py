"""
PROBLEM 16 FIX: Cross-platform launcher for Vulagent Scanner.
Works on Windows, Linux, and macOS without modification.
Replaces the Windows-only start_vulagent.bat.
"""

import subprocess
import sys
import os
import platform
import time


def main():
    is_windows = platform.system() == "Windows"
    root = os.path.dirname(os.path.abspath(__file__))

    print("=" * 50)
    print("  VULAGENT SCANNER — Cross-Platform Launcher")
    print(f"  Platform: {platform.system()} {platform.machine()}")
    print(f"  Python: {sys.version.split()[0]}")
    print("=" * 50)

    # Start backend
    backend_cmd = [sys.executable, "-m", "backend.main", "--mode", "serve"]
    creation_flags = subprocess.CREATE_NEW_CONSOLE if is_windows else 0
    
    try:
        backend = subprocess.Popen(
            backend_cmd,
            cwd=root,
            creationflags=creation_flags
        )
        print(f"✅ Backend started (PID {backend.pid})")
    except Exception as e:
        print(f"❌ Backend failed to start: {e}")
        sys.exit(1)

    time.sleep(2)

    # Start frontend
    npm_cmd = "npm.cmd" if is_windows else "npm"
    try:
        frontend = subprocess.Popen(
            [npm_cmd, "run", "dev"],
            cwd=root,
            creationflags=creation_flags
        )
        print(f"✅ Frontend started (PID {frontend.pid})")
    except Exception as e:
        print(f"❌ Frontend failed to start: {e}")
        backend.terminate()
        sys.exit(1)

    print()
    print("🚀 Vulagent Scanner running at http://localhost:5173")
    print("   Backend API at http://localhost:8000")
    print("   Press Ctrl+C to stop all services.")
    print()

    try:
        backend.wait()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Vulagent Scanner...")
        backend.terminate()
        frontend.terminate()
        try:
            backend.wait(timeout=5)
            frontend.wait(timeout=5)
        except subprocess.TimeoutExpired:
            backend.kill()
            frontend.kill()
        print("✅ Vulagent stopped.")


if __name__ == "__main__":
    main()
