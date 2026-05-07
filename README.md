# Nova

Local-first AI infrastructure for user-owned agents.

Nova is a macOS-first experimental repo for building agents with more
capability than a single chat loop. The focus is local execution, richer
computer context, multi-agent task harnesses, and infrastructure that keeps
the user in control of models, memory, tools, and automation.

The direction is simple:

- Local-first AI infra instead of cloud-dependent agent stacks.
- User-owned AI instead of rented intelligence with outsourced context.
- Computer-state context as a first-class input to reasoning.
- Multi-agent harnesses for more power, better decomposition, and task
  management.
- Agents that act on the machine, not just talk about it.

## What Nova Is Building

Nova explores a system where an orchestrator can understand the current state
of the computer, decide what matters, hand work to sub-agents when useful, and
route tool results back into a shared reasoning loop.

Today that computer context is mostly built from desktop signals like:

- frontmost app
- running apps
- installed apps
- date and time
- battery state

The larger idea is a computer-state graph: a structured context layer that
lets agents reason over what the machine is doing, what the user is doing, and
what tasks should happen next.

## Core Ideas

### Local-first

Inference, orchestration, and tools should run on the user's machine whenever
possible. Nova experiments with both `ollama` and `mlx-lm` based local model
flows.

### User-owned AI

The user should own the context. That includes prompts, memory, tool access,
desktop state, and model choice.

### Multi-agent harnesses

Some tasks should not be forced through one monolithic agent. Nova explores an
orchestrator plus sub-agent model so complex work can be split into smaller,
more manageable branches.

### Computer-state context

A useful agent should understand the environment it is acting inside. Nova
treats computer state as part of the context window, not as an afterthought.

## Repo Map

- `from_base/` the main active workspace for MLX model loading, inference,
  prompting, and benchmarking experiments.
- `data/` training and eval datasets plus the dataset-building script moved out
  of `from_base/`.
- `old work/` archived agent infrastructure, sub-agent, and voice experiments.
- `requirements.txt` shared Python dependencies for the local stack.

## Current Capabilities

- Local tool-calling agents backed by `ollama`.
- macOS automation helpers such as opening apps, opening URLs, and sending
  notifications.
- Computer-state summaries built from app focus, running apps, time, battery,
  and installed apps.
- Reasoning loops that separate tool use from final user-facing output.
- Early sub-agent patterns for decomposing multi-step tasks.
- Voice pipeline experiments using wake word detection and transcription.
- MLX-based local model loading experiments in `from_base/`.

## Architecture Direction

```text
User / Voice / UI
        |
        v
  Orchestrator Agent
        |
        +---------------- Shared memory / task state ----------------+
        |                                                           |
        v                                                           v
Computer-state builder                                  Sub-agent harnesses
(desktop context)                                       (task decomposition)
        |                                                           |
        +------------------- local tools and models -----------------+
```

## Getting Started

Nova is still an experimental workspace, not a polished product. The current
active area is `from_base/`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python3 from_base/main.py
```

Useful paths to inspect:

- `from_base/main.py` for MLX load-on-demand experiments.
- `from_base/use_model.py` for local model loading and generation.
- `data/build_dataset.py` for dataset assembly.
- `old work/agent_infra_native/` for archived native agent experiments.
- `old work/bs/voice_agent.py` for archived wake word -> transcription ->
  agent experiments.

## Notes

- This repo is currently macOS-first.
- Some experimental paths assume local model files or extra audio dependencies
  that may need adjustment on your machine.
- The README reflects the actual direction of the repo more than a stable API
  surface.

## Why Nova

Most agent stacks are remote-first, stateless, and weakly connected to the
computer they are supposed to help with. Nova is the opposite direction:
local-first AI infra, better context, stronger agent capability, and ownership
that stays with the user.
