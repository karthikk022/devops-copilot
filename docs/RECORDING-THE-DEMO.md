# Recording the demo GIF

A 2-3 minute GIF showing the copilot in action is the **#1 thing** that makes recruiters click. Here's the exact script.

## What you need
- Screen recorder: [ScreenToGif](https://www.screentogif.com/) (Windows, free) or Kap (Mac)
- Both `uvicorn` (backend) and `npm run dev` (frontend) running
- A few curl calls pre-staged to generate data

## Pre-recording checklist (run once)

```powershell
# Terminal 1: backend
cd copilot-backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000

# Terminal 2: frontend
cd apps\frontend
npm run dev

# Terminal 3: generate "interesting" data
# (this is the demo of the buggy app being monitored)
1..30 | ForEach-Object -Parallel { curl -s http://localhost:8080/api/users/1 > $null } -ThrottleLimit 5
1..5  | ForEach-Object { curl -s http://localhost:8080/api/leak > $null }
curl http://localhost:8080/api/slow
curl http://localhost:8080/api/error
```

## Recording script (the actual demo)

| Time | Action | Show in frame |
|------|--------|---------------|
| 0:00 | **Open the chat UI** | http://localhost:3000 — empty state with suggestions |
| 0:10 | **Click "What is this project..."** | Shows LLM + markdown streaming |
| 0:30 | **Type: "List all pods in the devops-copilot namespace"** | Tool call card appears (k8s_list_pods) |
| 0:50 | **Type: "Why is sample-api returning 500s? Investigate."** | Multi-tool sequence: pods → logs → Loki → diagnosis |
| 1:30 | **Zoom in on the tool call cards** | Highlight the result preview |
| 1:45 | **Show the final answer** | `## Diagnosis` + `## Recommended action` + RAG citation chip |
| 2:00 | **Switch to Grafana tab** | Live dashboard: error rate climbing, memory growing |
| 2:15 | **End card** | GitHub URL: github.com/YOU/devops-copilot |

## GIF optimization
- Resize to 1280x720 (or smaller for Twitter)
- Keep file size under 10 MB (recruiters won't wait for 50 MB)
- Use ScreenToGif → Editor → Resize → Save as `.gif`
- Or convert to MP4: `ffmpeg -i demo.gif demo.mp4` (smaller, LinkedIn accepts)

## What to put in the README

```markdown
## Demo

![Demo GIF](docs/screenshots/demo.gif)
```

## Where to host
- **GitHub README**: works directly
- **LinkedIn post**: upload the MP4 directly to the post
- **Personal site**: <img> tag
