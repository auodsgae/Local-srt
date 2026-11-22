package main

import (
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"syscall"
)

const supportsCUDA = true
const speechModel = "1.7b"

func platformWorker(dir string) (workerRuntime, error) {
	roots := []string{dir, filepath.Dir(dir)}
	if appData := os.Getenv("LOCALAPPDATA"); appData != "" {
		roots = append(roots, filepath.Join(appData, "LocalSRT"))
	}
	for _, root := range roots {
		for _, relative := range []string{".venv/Scripts/python.exe", "python/python.exe"} {
			python := filepath.Join(root, relative)
			if isFile(python) {
				return workerRuntime{python: python, root: root}, nil
			}
		}
	}
	return workerRuntime{}, errors.New("The Local SRT worker was not found. Run the Local SRT Windows installer or set LOCAL_SRT_PYTHON.")
}

func (r workerRuntime) prepare(_ func(workerEvent)) error { return nil }

func (r workerRuntime) configureCommand(cmd *exec.Cmd) {
	cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true, CreationFlags: 0x08000000} // CREATE_NO_WINDOW
	if r.root == "" {
		return
	}
	if ffmpeg := filepath.Join(r.root, "app", "ffmpeg"); isFile(filepath.Join(ffmpeg, "ffmpeg.exe")) {
		cmd.Env = append(cmd.Env, "PATH="+ffmpeg+string(os.PathListSeparator)+os.Getenv("PATH"))
	}
	if os.Getenv("LOCAL_SRT_APP_DATA") == "" && r.python == filepath.Join(r.root, "python", "python.exe") {
		cmd.Env = append(cmd.Env, "LOCAL_SRT_APP_DATA="+filepath.Join(r.root, "data"))
	}
}

func moveSubtitle(source, destination string) error {
	from, err := syscall.UTF16PtrFromString(source)
	if err != nil {
		return err
	}
	to, err := syscall.UTF16PtrFromString(destination)
	if err != nil {
		return err
	}
	return syscall.MoveFile(from, to)
}
