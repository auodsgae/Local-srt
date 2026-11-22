package main

import (
	"context"
	"embed"
	"io/fs"
	"log"
	"os"
	"strings"

	"github.com/egoist/mygo"
)

//go:embed frontend/*
var assets embed.FS

var appVersion = "dev"

type Desktop struct {
	queue *queue
}

func (d *Desktop) PickFiles(ctx context.Context) error {
	paths, err := mygo.Dialog.Open(mygo.OpenDialogOptions{
		Parent: mygo.CallerWindow(ctx), Title: "Add audio or video files", Multiple: true,
		Filters: []mygo.FileFilter{{Name: "Audio and video", Extensions: mediaExtensions}},
	})
	if err != nil {
		return err
	}
	d.queue.add(paths)
	return nil
}

func (d *Desktop) Snapshot() Snapshot        { return d.queue.snapshot() }
func (d *Desktop) Start(device string) error { return d.queue.start(device) }
func (d *Desktop) Clear() error              { return d.queue.clear() }

func main() {
	frontend, err := fs.Sub(assets, "frontend")
	if err != nil {
		log.Fatal(err)
	}
	mygo.SetFrontend(frontend)
	q := newQueue()
	q.add(os.Args[1:])
	mygo.Bind(&Desktop{queue: q})
	mygo.App.SetName("Local SRT")
	mygo.Theme.SetSource(mygo.ThemeDark)
	mygo.App.WhenReady(func() {
		win := mygo.NewWindow(mygo.WindowOptions{
			Title: "Local SRT", URL: "/", Width: 920, Height: 690,
			MinWidth: 590, MinHeight: 510, BackgroundColor: "#141414",
		})
		win.OnFileDrop(func(e *mygo.FileDropEvent) { q.add(e.Paths) })
		win.OnClose(func(e *mygo.CloseEvent) {
			q.mu.Lock()
			defer q.mu.Unlock()
			if q.running {
				e.PreventDefault()
				q.setNotice("Wait for the queue to finish before closing.")
			}
		})
	})
	if err := mygo.App.Run(); err != nil {
		mygo.Dialog.Error("Could not open Local SRT", strings.TrimSpace(err.Error()))
		log.Fatal(err)
	}
}
