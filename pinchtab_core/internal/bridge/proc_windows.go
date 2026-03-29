//go:build windows

package bridge

import "os/exec"

// configureChromeProcess is a no-op on Windows.
func configureChromeProcess(_ *exec.Cmd) {}
