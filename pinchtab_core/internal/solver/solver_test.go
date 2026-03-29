package solver

import (
	"context"
	"testing"
)

type fakeSolver struct {
	name      string
	canHandle bool
	result    *Result
	err       error
}

func (f *fakeSolver) Name() string { return f.name }
func (f *fakeSolver) CanHandle(ctx context.Context) (bool, error) {
	return f.canHandle, nil
}
func (f *fakeSolver) Solve(ctx context.Context, opts Options) (*Result, error) {
	return f.result, f.err
}

func TestRegister(t *testing.T) {
	defer cleanup("test-reg")

	err := Register("test-reg", &fakeSolver{name: "test-reg"})
	if err != nil {
		t.Fatalf("Register failed: %v", err)
	}

	err = Register("test-reg", &fakeSolver{name: "test-reg"})
	if err == nil {
		t.Fatal("expected error for duplicate registration")
	}
}

func TestMustRegisterPanicsOnDuplicate(t *testing.T) {
	defer cleanup("test-must")

	MustRegister("test-must", &fakeSolver{name: "test-must"})

	defer func() {
		if r := recover(); r == nil {
			t.Fatal("expected panic for duplicate MustRegister")
		}
	}()
	MustRegister("test-must", &fakeSolver{name: "test-must"})
}

func TestGet(t *testing.T) {
	defer cleanup("test-get")

	if err := Register("test-get", &fakeSolver{name: "test-get"}); err != nil {
		t.Fatalf("Register failed: %v", err)
	}

	s, ok := Get("test-get")
	if !ok || s == nil {
		t.Fatal("expected solver to be found")
	}
	if s.Name() != "test-get" {
		t.Errorf("expected name 'test-get', got %q", s.Name())
	}

	_, ok = Get("nonexistent")
	if ok {
		t.Error("expected false for unknown solver")
	}
}

func TestNames(t *testing.T) {
	defer cleanup("test-names-a")
	defer cleanup("test-names-b")

	if err := Register("test-names-a", &fakeSolver{name: "a"}); err != nil {
		t.Fatalf("Register failed: %v", err)
	}
	if err := Register("test-names-b", &fakeSolver{name: "b"}); err != nil {
		t.Fatalf("Register failed: %v", err)
	}

	names := Names()
	found := map[string]bool{}
	for _, n := range names {
		found[n] = true
	}
	if !found["test-names-a"] {
		t.Error("missing test-names-a")
	}
	if !found["test-names-b"] {
		t.Error("missing test-names-b")
	}
}

func TestSolve_Named(t *testing.T) {
	defer cleanup("test-solve")

	expected := &Result{Solver: "test-solve", Solved: true, Attempts: 1}
	if err := Register("test-solve", &fakeSolver{
		name:      "test-solve",
		canHandle: true,
		result:    expected,
	}); err != nil {
		t.Fatalf("Register failed: %v", err)
	}

	result, err := Solve(context.Background(), "test-solve", Options{MaxAttempts: 3})
	if err != nil {
		t.Fatalf("Solve failed: %v", err)
	}
	if !result.Solved {
		t.Error("expected Solved=true")
	}
	if result.Solver != "test-solve" {
		t.Errorf("expected solver 'test-solve', got %q", result.Solver)
	}
}

func TestSolve_Unknown(t *testing.T) {
	_, err := Solve(context.Background(), "does-not-exist", Options{})
	if err == nil {
		t.Fatal("expected error for unknown solver")
	}
}

func TestSolve_AutoDetect(t *testing.T) {
	defer cleanup("test-auto-no")
	defer cleanup("test-auto-yes")

	if err := Register("test-auto-no", &fakeSolver{
		name:      "test-auto-no",
		canHandle: false,
	}); err != nil {
		t.Fatalf("Register failed: %v", err)
	}
	if err := Register("test-auto-yes", &fakeSolver{
		name:      "test-auto-yes",
		canHandle: true,
		result:    &Result{Solver: "test-auto-yes", Solved: true},
	}); err != nil {
		t.Fatalf("Register failed: %v", err)
	}

	result, err := Solve(context.Background(), "", Options{})
	if err != nil {
		t.Fatalf("auto-detect Solve failed: %v", err)
	}
	if result.Solver != "test-auto-yes" {
		t.Errorf("expected solver 'test-auto-yes', got %q", result.Solver)
	}
}

func TestSolve_NoChallenge(t *testing.T) {
	defer cleanup("test-noop")

	if err := Register("test-noop", &fakeSolver{
		name:      "test-noop",
		canHandle: false,
	}); err != nil {
		t.Fatalf("Register failed: %v", err)
	}

	result, err := Solve(context.Background(), "", Options{})
	if err != nil {
		t.Fatalf("Solve failed: %v", err)
	}
	if !result.Solved {
		t.Error("expected Solved=true when no challenge detected")
	}
}

func TestUnregister(t *testing.T) {
	_ = Register("test-unreg", &fakeSolver{name: "test-unreg"})
	Unregister("test-unreg")

	_, ok := Get("test-unreg")
	if ok {
		t.Error("expected solver to be gone after Unregister")
	}
}

func cleanup(name string) {
	Unregister(name)
}
