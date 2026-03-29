//go:build darwin

package bridge

import "os/exec"

// configureChromeProcess is a no-op on macOS.
// Chrome inherits the parent's process group. The orchestrator kills the
// entire bridge group, and in standalone bridge mode, Cleanup() handles it.
func configureChromeProcess(_ *exec.Cmd) {}
