"""Command-line personal AI assistant scaffold.

This script shows how to connect a local language model to a lightweight
memory system that remembers tasks and personal preferences. It expects a
local LLM server such as Ollama, LM Studio, or llama.cpp running in server
mode. Adjust the environment variables documented in `main()` to suit your
setup.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
from urllib import request, error

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
PROFILE_PATH = DATA_DIR / "profile.json"
TASKS_PATH = DATA_DIR / "tasks.json"


def load_json(path: Path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def load_profile() -> Dict:
    return load_json(PROFILE_PATH, {})


def load_tasks() -> Dict[str, List[Dict]]:
    default = {"active": [], "completed": [], "recurring": []}
    tasks = load_json(TASKS_PATH, default)
    for key in default:
        tasks.setdefault(key, [])
    return tasks


def save_tasks(tasks: Dict[str, List[Dict]]) -> None:
    save_json(TASKS_PATH, tasks)


class LocalLLMClient:
    """Minimal HTTP client for a local LLM server."""

    def __init__(self, base_url: str, model: str, temperature: float = 0.2, max_tokens: int = 512):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def generate(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url=f"{self.base_url}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=60) as response:
                raw = response.read()
        except error.URLError as exc:  # pragma: no cover - requires network
            raise RuntimeError(
                "Failed to reach the local LLM server. Make sure it is running "
                f"at {self.base_url} and the model '{self.model}' is available."
            ) from exc

        body = json.loads(raw.decode("utf-8"))
        if "response" in body:
            return body["response"].strip()
        raise RuntimeError(f"Unexpected response payload: {body}")


def build_system_prompt(profile: Dict, tasks: Dict[str, List[Dict]]) -> str:
    profile_section = json.dumps(profile, indent=2) if profile else "{}"
    active_tasks = tasks.get("active", [])
    recurring_tasks = tasks.get("recurring", [])

    task_lines = ["Active tasks:"]
    if active_tasks:
        for item in active_tasks:
            due = item.get("due") or "unscheduled"
            task_lines.append(f"- {item.get('title', 'Untitled')} (due: {due})")
    else:
        task_lines.append("- None logged")

    if recurring_tasks:
        task_lines.append("Recurring reminders:")
        for item in recurring_tasks:
            task_lines.append(
                f"- {item.get('title', 'Untitled')} (frequency: {item.get('frequency', 'n/a')})"
            )

    task_section = "\n".join(task_lines)

    return (
        "You are Conner's personal coding assistant."
        " Provide concise, actionable help with programming tasks and personal productivity."
        " Always check whether there are new tasks that should be added to the backlog."
        " When new information about Conner appears, reflect it back so it can be stored."
        f"\n\nKnown profile:\n{profile_section}\n\n{task_section}\n"
    )


def build_prompt(system_prompt: str, history: List[Dict[str, str]], user_message: str) -> str:
    transcript_lines = [system_prompt, "\nConversation so far:"]
    for turn in history:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        transcript_lines.append(f"{role.capitalize()}: {content}")
    transcript_lines.append(f"User: {user_message}")
    transcript_lines.append("Assistant:")
    return "\n".join(transcript_lines)


def prompt_for_task() -> Optional[Dict]:
    title = input("Task title (leave blank to cancel): ").strip()
    if not title:
        return None
    due_input = input("Due date (YYYY-MM-DD or blank): ").strip()
    if due_input:
        try:
            due = dt.datetime.strptime(due_input, "%Y-%m-%d").date().isoformat()
        except ValueError:
            print("Invalid date format; storing as free text.")
            due = due_input
    else:
        due = None
    notes = input("Notes (optional): ").strip() or None
    return {
        "id": f"task-{dt.datetime.utcnow().isoformat()}",
        "title": title,
        "due": due,
        "notes": notes,
        "created_at": dt.datetime.utcnow().isoformat(),
    }


def add_task_interactively(tasks: Dict[str, List[Dict]]) -> None:
    task = prompt_for_task()
    if task:
        tasks.setdefault("active", []).append(task)
        save_tasks(tasks)
        print(f"Added task: {task['title']}")


def print_task_summary(tasks: Dict[str, List[Dict]]) -> None:
    active = tasks.get("active", [])
    if not active:
        print("No active tasks yet.")
        return
    print("Active tasks:")
    for item in active:
        due = item.get("due") or "unscheduled"
        print(f"- {item.get('title')} (due: {due})")


def run_chat(client: LocalLLMClient) -> None:
    profile = load_profile()
    tasks = load_tasks()
    history: List[Dict[str, str]] = []
    system_prompt = build_system_prompt(profile, tasks)
    print("Type 'exit' to quit.\n")
    print_task_summary(tasks)

    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break
        history.append({"role": "user", "content": user_input})
        prompt = build_prompt(system_prompt, history[:-1], user_input)
        try:
            response = client.generate(prompt)
        except RuntimeError as exc:
            print(exc)
            break
        print(f"Assistant: {response}\n")
        history.append({"role": "assistant", "content": response})

        should_add = input("Add a task based on this discussion? [y/N]: ").strip().lower()
        if should_add == "y":
            tasks = load_tasks()
            add_task_interactively(tasks)
            system_prompt = build_system_prompt(profile, tasks)

        remind = input("Any other tasks to log before we continue? [y/N]: ").strip().lower()
        if remind == "y":
            tasks = load_tasks()
            add_task_interactively(tasks)
            system_prompt = build_system_prompt(profile, tasks)


def handle_add_task(args) -> None:
    tasks = load_tasks()
    add_task_interactively(tasks)


def handle_check(args) -> None:
    tasks = load_tasks()
    print_task_summary(tasks)


def create_client_from_env() -> LocalLLMClient:
    base_url = os.environ.get("LOCAL_LLM_URL", "http://localhost:11434")
    model = os.environ.get("LOCAL_LLM_MODEL", "llama3")
    temperature = float(os.environ.get("LOCAL_LLM_TEMPERATURE", "0.2"))
    max_tokens = int(os.environ.get("LOCAL_LLM_MAX_TOKENS", "512"))
    return LocalLLMClient(
        base_url=base_url,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Personal AI assistant CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("chat", help="Start an interactive chat session")
    subparsers.add_parser("add-task", help="Add a new task to the backlog")
    subparsers.add_parser("check", help="Print the current task summary")

    args = parser.parse_args(argv)
    client = create_client_from_env()

    if args.command == "chat":
        run_chat(client)
    elif args.command == "add-task":
        handle_add_task(args)
    elif args.command == "check":
        handle_check(args)
    else:  # pragma: no cover - argparse prevents this path
        parser.error(f"Unknown command: {args.command}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
