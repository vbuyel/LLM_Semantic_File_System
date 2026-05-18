# LLM Service Test Suite Walkthrough

We have analyzed the codebase of the LLM microservice and implemented a comprehensive suite of **35 tests** covering both **Unit Tests** and **System/Integration Tests**. These tests have been placed under the `tests/` directory and are designed to target critical, high-risk areas where bugs, edge cases, or race conditions could arise.

---

## 📂 Test Suite Structure

The tests are organized into isolated `unit/` and `system/` folders:

```
src/llm/tests/
├── conftest.py                      # Global test setup (sys.path config & mock env vars)
├── unit/                            # Unit Tests (100% Mocked External Calls)
│   ├── test_domain.py               # Pydantic schema validation tests
│   ├── test_agent_researcher.py     # LLM forcing rules, agent loops, & error paths
│   ├── test_rag_search.py           # RAG response parsing & owner validation
│   ├── test_web_search.py           # Web search formatting & fallback triggers
│   └── test_kafka.py                # Singleton lifecycle & single-command timeout
└── system/                          # System & Integration Tests
    ├── test_api.py                  # FastAPI endpoints, status codes, & CORS compliance
    └── test_kafka_concurrency.py    # Multi-task Kafka message-stealing race condition test
```

---

## 🎯 Targeted Bug-Prone Areas

Our test cases specifically target highly critical architectural and code-level bottlenecks to prevent bugs:

### 1. The Singleton Shared-Consumer Concurrency Bug (Race Condition)
> [!IMPORTANT]
> **Found in:** `adapters.kafka.Kafka.send_command`
> 
> **The Issue:** The `Kafka` class is a singleton. When multiple requests call `send_command` concurrently (e.g. parallel chat questions), they share a single `AIOKafkaConsumer` instance. If one request calls `getmany()` and receives a batch containing reply messages for *both* Task A and Task B, it processes its own, returns, and *discards the rest of the batch*. The second task's message is permanently lost from the consumer, causing the second task to hit a `TimeoutError`.
> 
> **How we test it:** In [test_kafka_concurrency.py](file:///Users/vladbuyel/Documents/Projects/LLM_Semantic_File_System/src/llm/tests/system/test_kafka_concurrency.py), we simulate two concurrent calls using `asyncio.gather` and mock the consumer to yield both responses in a single batch. We verify that this race condition indeed causes one of the commands to timeout, proving the architectural vulnerability.

### 2. Null/Missing Owner Type Crash
> [!WARNING]
> **Found in:** `adapters.rag_search.RAGSearch.do_search`
> 
> **The Issue:** The RAG adapter contains the following logic:
> ```python
> owner = owner if "@gmail.com" in owner else "guest"
> ```
> If `owner` is passed as `None` (for instance, if the field is bypassed, omitted in database records, or passed as null by outer services), this line will crash with a `TypeError: argument of type 'NoneType' is not iterable`.
> 
> **How we test it:** In [test_rag_search.py](file:///Users/vladbuyel/Documents/Projects/LLM_Semantic_File_System/src/llm/tests/unit/test_rag_search.py#L115-L123), we pass `None` as the owner to ensure it is caught gracefully by the inner exception handler and converted into a user-friendly error response rather than crashing the execution thread.

### 3. LLM Tool Call Parsing & Loop Edge Cases
> [!NOTE]
> **Found in:** `adapters.agent.AgentResearcher.get_response`
> 
> **The Issue:** Since local LLMs (like Ollama) are prone to returning invalid JSON in tool arguments or leaving out required arguments (like `"text"`), the tool calling logic has multiple points of failure.
> 
> **How we test it:** In [test_agent_researcher.py](file:///Users/vladbuyel/Documents/Projects/LLM_Semantic_File_System/src/llm/tests/unit/test_agent_researcher.py), we test:
> - `test_get_response_invalid_tool_json` (handles invalid JSON string args).
> - `test_get_response_missing_tool_text_arg` (handles cases where the LLM forgets the required `"text"` tool parameter).
> - `test_get_response_unknown_tool_function` (handles cases where the LLM calls a function name that doesn't exist).

### 4. CORS Middleware Policies & Portability
> [!TIP]
> **Found in:** `v1.main.app`
> 
> **The Issue:** With CORS configured to allow credentials (`allow_credentials=True`), browser security requires the server to echo back the exact client origin (e.g. `http://localhost:3000`) instead of returning a wildcard `"*"`.
> 
> **How we test it:** In [test_api.py](file:///Users/vladbuyel/Documents/Projects/LLM_Semantic_File_System/src/llm/tests/system/test_api.py#L25-L38), we trigger an `OPTIONS` preflight request mimicking a frontend origin and assert that Starlette CORS middleware correctly handles preflight headers and echoes the exact origin back.

---

## ⚡ How to Run the Tests

To run the test suite locally, execute the following command from the `llm` root folder:

```bash
.venv/bin/pytest tests -v
```

All 35 tests run completely in memory without requiring actual running instances of Ollama, Exa, or Kafka. The suite finishes in **under 1 second**:

```
============================== 35 passed in 0.60s ==============================
```
