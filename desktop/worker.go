package main

import (
	"bufio"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

type workerRuntime struct {
	python    string
	root      string
	resources string
}

type workerEvent struct {
	Type    string `json:"type"`
	Percent *int   `json:"percent"`
	Stage   string `json:"stage"`
	Message string `json:"message"`
}

func findWorker() (workerRuntime, error) {
	if override := os.Getenv("LOCAL_SRT_PYTHON"); override != "" {
		if !filepath.IsAbs(override) || !isFile(override) {
			return workerRuntime{}, errors.New("LOCAL_SRT_PYTHON must point to an existing Python executable using an absolute path.")
		}
		return workerRuntime{python: override}, nil
	}
	exe, err := os.Executable()
	if err != nil {
		return workerRuntime{}, err
	}
	return platformWorker(filepath.Dir(exe))
}

func isFile(path string) bool {
	info, err := os.Stat(path)
	return err == nil && info.Mode().IsRegular()
}

func (r workerRuntime) transcribe(input, device string, progress func(workerEvent)) (string, error) {
	if err := r.prepare(progress); err != nil {
		return "", err
	}
	tempDir, err := os.MkdirTemp(filepath.Dir(input), ".localsrt-")
	if err != nil {
		return "", fmt.Errorf("could not create a subtitle in the media folder: %w", err)
	}
	defer os.Remove(tempDir)
	tempSRT := filepath.Join(tempDir, "caption.srt")
	defer os.Remove(tempSRT)

	cmd := exec.Command(r.python, "-m", "local_srt.worker", "transcribe",
		"--input", input, "--output", tempSRT, "--device", device,
		"--language", "auto", "--model", speechModel, "--script", "traditional", "--caption-style", "natural")
	cmd.Dir = filepath.Dir(r.python)
	cmd.Env = append(os.Environ(), "PYTHONIOENCODING=utf-8")
	r.configureCommand(cmd)
	return finishWorker(cmd, tempSRT, input, progress)
}

func finishWorker(cmd *exec.Cmd, tempSRT, input string, progress func(workerEvent)) (string, error) {
	lines, err := cmd.StdoutPipe()
	if err != nil {
		return "", err
	}
	defer lines.Close()
	var stderr lastOutput
	cmd.Stderr = &stderr
	if err := cmd.Start(); err != nil {
		return "", fmt.Errorf("could not start the Local SRT worker: %w", err)
	}
	scanner := bufio.NewScanner(lines)
	scanner.Buffer(make([]byte, 4096), 1024*1024)
	var result bool
	var failure string
	for scanner.Scan() {
		var event workerEvent
		if json.Unmarshal(scanner.Bytes(), &event) != nil {
			continue
		}
		switch event.Type {
		case "progress":
			progress(event)
		case "result":
			result = true
		case "error":
			failure = strings.TrimSpace(event.Message)
		}
	}
	if scanner.Err() != nil {
		_, _ = io.Copy(io.Discard, lines)
	}
	err = cmd.Wait()
	if failure != "" {
		return "", errors.New(failure)
	}
	if scanErr := scanner.Err(); scanErr != nil {
		return "", fmt.Errorf("could not read transcription status: %w", scanErr)
	}
	if err != nil || !result || !isFile(tempSRT) {
		if detail := stderr.lastLine(); detail != "" {
			return "", fmt.Errorf("the Local SRT worker did not finish: %s", detail)
		}
		return "", errors.New("The Local SRT worker did not produce a subtitle.")
	}
	return saveSubtitle(tempSRT, input)
}

type lastOutput []byte

func (b *lastOutput) Write(p []byte) (int, error) {
	const limit = 4096
	*b = append(*b, p...)
	if len(*b) > limit {
		*b = append((*b)[:0], (*b)[len(*b)-limit:]...)
	}
	return len(p), nil
}

func (b lastOutput) lastLine() string {
	line := strings.TrimSpace(string(b))
	return line[strings.LastIndexAny(line, "\r\n")+1:]
}

func saveSubtitle(tempSRT, input string) (string, error) {
	stem := strings.TrimSuffix(input, filepath.Ext(input))
	for index := 1; ; index++ {
		output := stem + ".srt"
		if index > 1 {
			output = fmt.Sprintf("%s (%d).srt", stem, index)
		}
		if err := moveSubtitle(tempSRT, output); err == nil {
			return output, nil
		} else if !errors.Is(err, os.ErrExist) {
			return "", fmt.Errorf("could not save subtitle: %w", err)
		}
	}
}
