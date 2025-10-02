# Building a Local Personal AI Assistant

This guide walks you through designing, running, and continually improving a personal AI assistant on your own computer. The focus is on three capabilities:

1. Getting to know you over time by persisting key details.
2. Helping you remember and execute tasks.
3. Proactively checking whether you have new tasks to add.

---

## 1. Choose Your Local Language Model

Pick a model that you can run locally with the hardware you have available. Popular options that work well on consumer hardware include:

| Platform | Why use it? | Example models |
| --- | --- | --- |
| [Ollama](https://ollama.ai/) | Easiest installation on macOS/Linux, simple CLI, streams responses. | `llama3`, `codellama`, `mistral` |
| [LM Studio](https://lmstudio.ai/) | Desktop UI for Windows/macOS, integrates with local notebooks via an HTTP server. | Any GGUF quantized model |
| [llama.cpp](https://github.com/ggerganov/llama.cpp) | Highly optimized for CPU/GPU, great for custom setups. | Download a `gguf` build of `Llama 3`, `Phi-3`, etc. |
| [GPT4All](https://www.nomic.ai/gpt4all) | Bundles models and UI, works offline. | GPT4All family |

> 💡 **Tip:** Start with a 7B parameter model (e.g., `Llama-3-8B-Instruct` quantized to 4-bit) and scale up if your GPU/CPU can handle it. For coding tasks, consider `CodeLlama` or `DeepSeek-Coder` variants.

Once the platform is installed, run the model in server mode (Ollama serve, LM Studio local server, llama.cpp `--server`) so you can call it from scripts.

---

## 2. Persistent Memory Design

A personal assistant needs structured storage so it can "remember" your details and tasks across sessions. A minimal setup includes three stores:

1. **User profile** – high-level facts about you (name, preferences, working hours, favorite tools).
2. **Task list** – active, completed, and recurring tasks with metadata (priority, due date, tags).
3. **Interaction log** – important conversation snippets that should inform future responses.

Use simple, transparent formats at first:

- JSON files are easy to inspect and edit by hand.
- SQLite works well once the data grows.
- For long-term memory, periodically summarize the interaction log and store the summaries rather than every message.

The provided `src/personal_assistant.py` script (see below) demonstrates a JSON-based store that can be upgraded later.

---

## 3. Prompting Strategy

Fine-tuned instruct models respond best to explicit, structured prompts. Combine three elements in every request you send to the model:

1. **System instructions** – the permanent rules the assistant must follow (e.g., "You are Conner's personal coding assistant. Always ask if there are new tasks to log.").
2. **Memory context** – relevant profile facts, outstanding tasks, and any conversation summary.
3. **Latest user input** – your current question or update.

When the assistant responds, parse the output for actionable items and update your stores.

---

## 4. Conversation Loop Overview

1. Load memory (profile, tasks, summaries).
2. Build a prompt that includes the system instructions and the latest context.
3. Send the prompt to your local LLM.
4. Display the response, capture any new tasks or facts, and append them to the memory store.
5. Before ending the session (or every N interactions), ask whether you have more tasks to add.

---

## 5. Scheduling Reminders

Two complementary approaches keep you on track:

- **Pull-based** – start a chat session and ask "What should I work on today?". The assistant filters tasks due or overdue.
- **Push-based** – run a lightweight cron job or scheduled task that checks for upcoming deadlines and notifies you (desktop notification, email, or CLI printout).

The provided script includes a `--check` command that you can schedule with cron/Task Scheduler.

---

## 6. Security and Privacy Considerations

- Store sensitive data locally and encrypt files if your machine is shared.
- Keep model downloads and Python dependencies up to date.
- If you sync data across devices, encrypt backups (e.g., with `age`, `gpg`, or Bitwarden Secure Notes).

---

## 7. Roadmap for Enhancements

1. **Better task understanding** – add natural-language parsing to convert freeform text into structured tasks (LangChain's `TaskExtractionChain` or custom regex).
2. **Voice interface** – integrate `whisper.cpp` for offline speech-to-text and `piper`/`kokoro` for text-to-speech.
3. **Calendar integration** – sync with Google Calendar or local CalDAV for deadlines.
4. **Codebase awareness** – point the assistant to your repositories and let it summarize or search them using embeddings (e.g., `chromadb`).
5. **Automatic daily summaries** – auto-generate a short recap of tasks completed and upcoming priorities.

---

## 8. Getting Started Quickly

1. Install Python 3.10+ and `pipx`.
2. Set up a virtual environment: `python -m venv .venv && source .venv/bin/activate`.
3. Install dependencies from `requirements.txt` (to be created based on the model client you choose).
4. Configure the environment variables expected by the script (e.g., `LOCAL_LLM_URL`).
5. Run `python src/personal_assistant.py chat` to start a conversation.

Review the script below and adapt it to match the local model provider you prefer.

---

## 9. Next Steps

- Populate `data/profile.json` with your details.
- Add a recurring reminder to log new tasks each morning.
- Iterate: log issues, refine prompts, and tune the assistant to your workflow.

Happy building!

