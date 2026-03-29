//go:build linux

package bridge

import (
	"os/exec"
	"syscall"
)

// configureChromeProcess sets parent death signal on Linux so Chrome dies
// when the Go process exits unexpectedly.
// Does NOT set Setpgid — Chrome stays in the parent's process group so the
// orchestrator can kill the entire bridge group at once.
func configureChromeProcess(cmd *exec.Cmd) {
	cmd.SysProcAttr = &syscall.SysProcAttr{
		Pdeathsig: syscall.SIGKILL,
	}
}
