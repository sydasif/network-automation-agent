# Simplified Network AI Agent Plan

## Core Principle

Build a working prototype first, then add complexity only when needed.

---

## Phase 1: Basic Foundation (Days 1-2)

### Step 1: Project Setup

```bash
uv add langchain langchain-groq langgraph netmiko python-dotenv pydantic
```

**Create structure:**

```bash
src/
  agent.py    # Everything starts here
config/
  hosts.yaml         # Device inventory
.env.example         # API keys template
```

### Step 2: Device Connectivity

**File: `agent.py`**

1. Load `.env` for secrets
2. Parse `hosts.yaml` (simple YAML load, no fancy resolver)
3. Connect to ONE device using netmiko
4. Execute ONE command: `show version`
5. Print raw output

**Test:** Can you SSH and get output? Good. Move on.

---

## Phase 2: LLM Integration (Days 3-4)

### Step 3: Hook Up Groq

1. Initialize `ChatGroq` with API key from `.env`
2. Create a simple function tool:

   ```python
   @tool
   def run_command(device: str, command: str) -> str:
       """Execute network command and return output"""
       # Call your netmiko code from Step 2
   ```

3. Create basic agent with this tool
4. Test: "Show me the version of router-1"

**Goal:** LLM can call your network function.

---

## Phase 3: Multi-Agent (Days 5-6)

### Step 4: Add LangGraph State Machine

**Keep it minimal:**

1. **State:**

   ```python
   class State(TypedDict):
       messages: list
       results: dict  # That's it
   ```

2. **Three Nodes:**
   - `understand`: Parse user intent (extract device + command)
   - `execute`: Run the command
   - `respond`: Format and return results

3. **Flow:**

   ```
   START → understand → execute → respond → END
   ```

No supervisor needed yet. Linear flow.

---

## Phase 4: Polish (Days 7-8)

### Step 5: Make It User-Friendly

1. Add CLI loop (ask for input, run graph, print output, repeat)
2. Handle errors gracefully (connection failed? Say so clearly)
3. Add 2-3 more useful commands (show interfaces, show ip route)
4. Format output as tables using `tabulate`

### Step 6: Multi-Device Support

1. Change `run_command` to accept `device: list[str]`
2. Use `ThreadPoolExecutor` to run commands in parallel
3. Aggregate results

---

## Implementation Order

```python
# Day 1
1. SSH to one device ✓
2. Print raw output ✓

# Day 2
3. Wrap in LangChain tool ✓
4. LLM calls your tool ✓

# Day 3-4
5. Add LangGraph state flow ✓
6. Parse intent, execute, respond ✓

# Day 5-6
7. CLI loop ✓
8. Multi-device ✓
9. Pretty output ✓
