package main

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"sync"
)

var mediaExtensions = strings.Fields(
	"mp4 mkv avi mov wmv flv webm ts m2ts mpg mpeg m4v vob 3gp f4v mxf wav mp3 m4a aac flac ogg opus wma",
)

type Job struct {
	Input   string `json:"input"`
	Name    string `json:"name"`
	Output  string `json:"output,omitempty"`
	Status  string `json:"status"`
	Stage   string `json:"stage,omitempty"`
	Percent int    `json:"percent"`
	Error   string `json:"error,omitempty"`
}

type Snapshot struct {
	Jobs     []Job  `json:"jobs"`
	Running  bool   `json:"running"`
	Active   int    `json:"active"`
	Device   string `json:"device"`
	CUDA     bool   `json:"cuda"`
	Notice   string `json:"notice"`
	Revision int    `json:"revision"`
}

type queue struct {
	mu       sync.Mutex
	jobs     []Job
	running  bool
	active   int
	device   string
	notice   string
	revision int
}

func newQueue() *queue {
	device := "cpu"
	if supportsCUDA && !strings.EqualFold(os.Getenv("LOCAL_SRT_DEFAULT_DEVICE"), "cpu") {
		device = "cuda"
	}
	return &queue{device: device, active: -1}
}

func (q *queue) snapshot() Snapshot {
	q.mu.Lock()
	defer q.mu.Unlock()
	return Snapshot{
		Jobs: slices.Clone(q.jobs), Running: q.running, Active: q.active,
		Device: q.device, CUDA: supportsCUDA, Notice: q.notice, Revision: q.revision,
	}
}

// Caller holds q.mu.
func (q *queue) setNotice(message string) {
	q.notice = message
	q.revision++
}

func (q *queue) add(paths []string) {
	if len(paths) == 0 {
		return
	}
	q.mu.Lock()
	defer q.mu.Unlock()
	if q.running {
		q.setNotice("Wait for the queue to finish before adding more files.")
		return
	}
	skipped := 0
	for _, path := range paths {
		path, err := filepath.Abs(path)
		if err != nil || !slices.Contains(mediaExtensions, strings.TrimPrefix(strings.ToLower(filepath.Ext(path)), ".")) {
			skipped++
			continue
		}
		info, err := os.Stat(path)
		if err != nil || !info.Mode().IsRegular() {
			skipped++
			continue
		}
		if slices.ContainsFunc(q.jobs, func(job Job) bool { return strings.EqualFold(job.Input, path) }) {
			continue
		}
		q.jobs = append(q.jobs, Job{Input: path, Name: filepath.Base(path), Status: "queued"})
	}
	if skipped > 0 {
		q.setNotice(fmt.Sprintf("Skipped %d unsupported or unavailable file(s).", skipped))
	} else {
		q.setNotice("")
	}
}

func (q *queue) clear() error {
	q.mu.Lock()
	defer q.mu.Unlock()
	if q.running {
		return errors.New("Wait for the queue to finish before clearing it.")
	}
	q.jobs = nil
	q.active = -1
	q.setNotice("")
	return nil
}

func (q *queue) start(device string) error {
	q.mu.Lock()
	defer q.mu.Unlock()
	if q.running {
		return errors.New("The queue is already running.")
	}
	if device != "cpu" && !(supportsCUDA && device == "cuda") {
		return errors.New("Select an available transcription device.")
	}
	if !slices.ContainsFunc(q.jobs, func(job Job) bool { return job.Status == "queued" || job.Status == "failed" }) {
		return errors.New("Add a file to transcribe.")
	}
	runtime, err := findWorker()
	if err != nil {
		return err
	}
	q.running = true
	q.device = device
	for i := range q.jobs {
		if q.jobs[i].Status != "saved" {
			q.jobs[i].Status = "queued"
			q.jobs[i].Percent = 0
			q.jobs[i].Error = ""
		}
	}
	q.setNotice("")
	go q.run(runtime, device)
	return nil
}

func (q *queue) run(runtime workerRuntime, device string) {
	q.mu.Lock()
	for i, job := range q.jobs {
		if job.Status == "saved" {
			continue
		}
		q.active = i
		q.jobs[i].Status, q.jobs[i].Stage = "working", "Starting worker"
		q.revision++
		q.mu.Unlock()

		output, err := runtime.transcribe(job.Input, device, func(event workerEvent) {
			q.mu.Lock()
			defer q.mu.Unlock()
			active := &q.jobs[i]
			if event.Stage != "" {
				active.Stage = event.Stage
			}
			if event.Percent != nil && *event.Percent < 100 {
				active.Percent = max(active.Percent, *event.Percent)
			}
			q.revision++
		})

		q.mu.Lock()
		q.jobs[i].Stage = ""
		if err != nil {
			q.jobs[i].Status, q.jobs[i].Error = "failed", err.Error()
		} else {
			q.jobs[i].Status, q.jobs[i].Output, q.jobs[i].Percent = "saved", output, 100
		}
		q.revision++
	}
	q.running = false
	q.setNotice("")
	q.mu.Unlock()
}
