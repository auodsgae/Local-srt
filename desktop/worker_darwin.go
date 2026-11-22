package main

import (
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"syscall"

	"golang.org/x/sys/unix"
)

const supportsCUDA = false
const speechModel = "0.6b"

func platformWorker(dir string) (workerRuntime, error) {
	data, err := os.UserConfigDir()
	if err != nil {
		return workerRuntime{}, err
	}
	resources := filepath.Join(filepath.Dir(dir), "Resources")
	if !isFile(filepath.Join(resources, "prepare-worker.sh")) {
		return workerRuntime{}, errors.New("Open the Local SRT app from the macOS disk image, or set LOCAL_SRT_PYTHON for development.")
	}
	root := filepath.Join(data, "LocalSRT")
	python := filepath.Join(root, "runtime", appVersion, "bin", "python3")
	return workerRuntime{python: python, root: root, resources: resources}, nil
}

func (r workerRuntime) prepare(progress func(workerEvent)) error {
	if r.resources == "" {
		return nil
	}
	venv := filepath.Dir(filepath.Dir(r.python))
	if err := os.MkdirAll(venv, 0700); err != nil {
		return err
	}
	lock, err := os.OpenFile(filepath.Join(venv, ".setup-lock"), os.O_CREATE|os.O_RDWR, 0600)
	if err != nil {
		return err
	}
	defer lock.Close()
	if err := syscall.Flock(int(lock.Fd()), syscall.LOCK_EX); err != nil {
		return err
	}
	if isFile(r.python) && isFile(filepath.Join(venv, ".worker-ready")) {
		return nil
	}
	progress(workerEvent{Stage: "Downloading the speech runtime for first use"})
	cmd := exec.Command("/bin/sh", filepath.Join(r.resources, "prepare-worker.sh"), r.root, appVersion)
	var output lastOutput
	cmd.Stdout, cmd.Stderr = &output, &output
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("could not set up the speech runtime: %w. %s", err, output.lastLine())
	}
	return nil
}

func (r workerRuntime) configureCommand(cmd *exec.Cmd) {
	if r.root != "" && os.Getenv("LOCAL_SRT_APP_DATA") == "" {
		cmd.Env = append(cmd.Env, "LOCAL_SRT_APP_DATA="+r.root)
	}
}

func moveSubtitle(source, destination string) error {
	return unix.RenamexNp(source, destination, unix.RENAME_EXCL)
}
