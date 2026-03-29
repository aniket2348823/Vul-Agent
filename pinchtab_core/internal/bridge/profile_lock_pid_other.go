//go:build !windows

package bridge

import (
	"errors"
	"fmt"
	"os/exec"
	"strings"
	"syscall"
	"time"
)

func isChromePIDRunning(pid int) (bool, error) {
	if pid <= 0 {
		return false, nil
	}
	err := syscall.Kill(pid, syscall.Signal(0))
	if err == nil {
		return true, nil
	}
	if errors.Is(err, syscall.ESRCH) {
		return false, nil
	}
	if errors.Is(err, syscall.EPERM) {
		return true, nil
	}
	return false, err
}

func killProcesses(processes []chromeProfileProcess) error {
	for _, proc := range processes {
		var pid int
		if _, err := fmt.Sscanf(proc.PID, "%d", &pid); err != nil {
			continue
		}
		if pid <= 0 {
			continue
		}
		// Try SIGTERM first, then SIGKILL if it doesn't work?
		// Given we are in a "stale recovery" path, being aggressive is often better
		// to ensure the next startup succeeds.
		_ = syscall.Kill(pid, syscall.SIGKILL)
	}
	// Give a small amount of time for processes to actually exit
	time.Sleep(100 * time.Millisecond)
	return nil
}

func isPinchTabProcess(pid int) bool {
	if pid <= 0 {
		return false
	}
	// On Linux/macOS, we can check the process name or args.
	// A simple check is to see if the command contains "pinchtab".
	cmd := exec.Command("ps", "-p", fmt.Sprintf("%d", pid), "-o", "args=") // #nosec G204 -- pid is an int, not user-controlled string
	out, err := cmd.Output()
	if err != nil {
		return false
	}
	line := strings.ToLower(string(out))
	return strings.Contains(line, "pinchtab")
}
