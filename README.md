
# Personal Productivity Agent

This project implements a multi‑agent productivity system designed to collect tasks, prioritize them, generate a daily schedule, produce reminders, and evaluate the output. The system is built using Python, a modular agent architecture, and a custom Gradio interface.

---

# 1. Architecture Overview

Below is the complete architecture and workflow layout of the system.

```
                         ┌─────────────────────────────────────────┐
                         │     Main Orchestrator (A2A Hub)         │
                         │    Coordinates all agent operations     │
                         └──────────────┬──────────────────────────┘
                                        │
                               ┌────────┴────────┐
                               │                 │
                       ┌───────▼──────┐   ┌─────▼─────────┐
                       │ Collector    │   │   Priority     │
                       │   Agent      │   │     Agent      │
                       └──────────────┘   └───────┬────────┘
                                                  │
                                        ┌─────────▼─────────┐
                                        │     Planner       │
                                        │      Agent        │
                                        └─────────┬─────────┘
                                                  │
                    ┌─────────────────────────────┴──────────────────────────┐
                    │                                                        │
           ┌────────▼────────┐                                      ┌────────▼─────────┐
           │   Reminder      │                                      │   Reflection      │
           │     Agent       │                                      │      Agent        │
           └─────────────────┘                                      └───────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                   User Interface (Gradio)                    │
│           Modern dashboard for interacting with agents       │
└──────────────────────────────────────────────────────────────┘
```

---

# 2. Detailed Flow

```
User Input (Text or JSON)
        │
        ▼
Collector Agent
 - Parses text
 - Extracts durations & priorities
 - Normalizes fields
        │
        ▼
Priority Agent
 - Scores tasks (urgency, importance, effort, deadline)
 - Assigns high/medium/low priority
 - Ranks tasks
        │
        ▼
Planner Agent
 - Generates timeline starting at 09:00 (local timezone)
 - Inserts break intervals
 - Ensures time consistency
        │
        ▼
Reminder Agent
 - Generates reminder timestamps
 - Stores reminder JSON files
        │
        ▼
Reflection Agent
 - Analyzes quality, workload, balance
 - Produces improvement tips
        │
        ▼
Orchestrator
 - Collects outputs from all agents
 - Merges schedule, reminders, evaluation
 - Returns unified response to UI
        │
        ▼
Gradio UI
 - Renders schedule
 - Displays scores and reminders
 - Shows task history
```

---

# 3. Folder Structure

```
src/
 ├── agents/
 │    ├── collector_agent.py
 │    ├── priority_agent.py
 │    ├── planner_agent.py
 │    ├── reminder_agent.py
 │    ├── reflection_agent.py
 │    └── orchestrator.py
 │
 ├── evaluation/
 │    └── plan_evaluator.py
 │
 ├── memory/
 │    ├── session_manager.py
 │    ├── memory_bank.py
 │    └── context_engineer.py
 │
 ├── observability/
 │    ├── logger.py
 │    ├── metrics.py
 │    └── tracer.py
 │
 ├── tools/
 │    ├── time_estimator.py
 │    ├── habit_analyzer.py
 │    ├── search_tool.py
 │    └── mcp_tools.py
 │
 └── utils/
      └── helpers.py

ui/
 └── gradio_app.py

README.md
```

---

# 4. Key Components

### CollectorAgent

Parses raw text and JSON inputs. Extracts priority, category, duration, tags, and deadlines.
Normalizes all tasks into a standard structure.

### PriorityAgent

Scores tasks based on:

- urgency
- importance (category importance map)
- expected effort
- deadline proximity

Outputs a numerical score + adjusted final priority.

### PlannerAgent

Builds a chronological schedule:

- Default start time: 09:00 local time
- Adds break intervals
- Computes start/end times
- Ensures sequential consistency

### ReminderAgent

Generates reminder timestamps and writes them to the `reminders/` directory.

### ReflectionAgent

Runs simple pattern analysis, workload balance checks, and improvement suggestions.

### Orchestrator

Coordinates the end‑to‑end pipeline:

- Calls each agent sequentially
- Aggregates all outputs
- Handles history logging
- Returns final structured output to UI

### Gradio UI

Provides:

- Task input box
- History view
- Reminder view
- Responsive layout with mobile‑friendly navbar
- Rich schedule visualizer with cards/sections

---

# 5. Running the Project

Install dependencies:

```
pip install -r requirements.txt
```

Start the Gradio UI:

```
python -m ui.gradio_app
```

The interface opens at:

```
http://localhost:7860/
```

---

# 6. Configuration

Create a `.env` file:

```
GOOGLE_API_KEY=your_api_key_here
```

Your system will use this key for LLM-powered agents.

---

# 7. Scheduling Logic

- Day start time: **09:00 local timezone**
- Each task is scheduled sequentially
- Breaks added after each task
  - < 60 min → 5 min break
  - 60–120 min → 15 min break
  -  > 120 min → 20 min break
    >

This ensures a realistic plan with proper work‑break cycles.

---

# 8. Notes

- Timezone handling uses `tzlocal` to avoid UTC shift issues.
- Category importance mapping is customizable in `priority_agent.py`.
- UI supports both JSON and plain-English input formats.
