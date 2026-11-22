package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestSaveSubtitleKeepsExistingFile(t *testing.T) {
	dir := t.TempDir()
	input := filepath.Join(dir, "speech.wav")
	existing := filepath.Join(dir, "speech.srt")
	newSubtitle := filepath.Join(dir, "new.srt")
	for path, content := range map[string]string{existing: "original", newSubtitle: "new subtitle"} {
		if err := os.WriteFile(path, []byte(content), 0600); err != nil {
			t.Fatal(err)
		}
	}

	saved, err := saveSubtitle(newSubtitle, input)
	if err != nil {
		t.Fatal(err)
	}
	if want := filepath.Join(dir, "speech (2).srt"); saved != want {
		t.Fatalf("saved as %q, want %q", saved, want)
	}
	for path, want := range map[string]string{existing: "original", saved: "new subtitle"} {
		data, err := os.ReadFile(path)
		if err != nil || string(data) != want {
			t.Fatalf("read %q from %s, want %q (error: %v)", data, path, want, err)
		}
	}
}
