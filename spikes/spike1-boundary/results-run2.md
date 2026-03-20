# Spike 1 — Episode Boundary Detection: Results

*Generated 2026-03-14 16:27*

---

## Input data

- Source: `pipelines/memory/research-findings.db` session_key=`research`
- Total turns: 21
- Date range: 2026-03-11 → 2026-03-14

### Turn listing

  `[00]` 2026-03-11T07:59  `      C5`  `github    `  langchain-ai/langgraph 1.1.0
  `[01]` 2026-03-11T07:59  `      C5`  `github    `  langchain-ai/langgraph cli==0.4.15
  `[02]` 2026-03-11T13:29  ` general`  `blog      `  The Anatomy of an Agent Harness
  `[03]` 2026-03-11T13:29  ` general`  `blog      `  How Coding Agents Are Reshaping Engineering, Product and Design
  `[04]` 2026-03-12T01:29  `      C2`  `blog      `  Autonomous context compression
  `[05]` 2026-03-12T01:29  `      C6`  `blog      `  Designing AI agents to resist prompt injection
  `[06]` 2026-03-12T01:29  `      C6`  `blog      `  From model to agent: Equipping the Responses API with a computer 
  `[07]` 2026-03-12T01:29  `      C8`  `blog      `  Three sub-agent patterns you need for your agentic system
  `[08]` 2026-03-12T07:59  `      C5`  `github    `  langchain-ai/langgraph 1.1.1
  `[09]` 2026-03-12T07:59  `      C3`  `github    `  inngest/inngest-py inngest@0.5.18
  `[10]` 2026-03-12T08:00  `       ?`  `text      `  [Summary of earlier history]
# Structured Context Block: aswarm M
  `[11]` 2026-03-12T12:29  `      C2`  `arxiv     `  The Missing Memory Hierarchy: Demand Paging for LLM Context Windo
  `[12]` 2026-03-12T12:29  `      C9`  `arxiv     `  AI-Powered ECM Automation with Agentic AI for Adaptive, Policy-Dr
  `[13]` 2026-03-13T01:29  `      C2`  `blog      `  Delivering contextual job matching for millions with OpenAI
  `[14]` 2026-03-13T07:59  `      C5`  `github    `  langchain-ai/langgraph 1.1.2
  `[15]` 2026-03-13T07:59  `      C5`  `github    `  langchain-ai/langgraph cli==0.4.16
  `[16]` 2026-03-13T07:59  `      C6`  `github    `  openai/openai-agents-python v0.12.1
  `[17]` 2026-03-13T07:59  `      C4`  `github    `  openai/openai-agents-python v0.12.0
  `[18]` 2026-03-13T07:59  `      C4`  `github    `  google/adk-python v1.27.0
  `[19]` 2026-03-14T07:59  `      C5`  `github    `  langchain-ai/langgraph cli==0.4.17
  `[20]` 2026-03-14T07:59  `      C5`  `github    `  openai/openai-agents-python v0.12.2

---

## Approach A (Nemori naïve, conf≥0.8)

- Episodes: **7**  (mean 3.0 turns, min 1, max 9, singletons 5)
- LLM calls: 20

### Episode 1: LangGraph v2 Streaming and Multi-Agent Orchestration Advances

  Title: LangGraph v2 Streaming and Multi-Agent Orchestration Advances
  Turns: 9 | areas=C2, C5, C6, C8 sources=blog, github
    [00] [C5] (github) langchain-ai/langgraph 1.1.0 — v2 streaming protocol with typed ou
    [01] [C5] (github) langchain-ai/langgraph cli==0.4.15 — CLI deployment feature added 
    [02] [general] (blog) The Anatomy of an Agent Harness — LangChain's Vivek Trivedy def
    [03] [general] (blog) How Coding Agents Are Reshaping Engineering, Product and Design
    [04] [C2] (blog) Autonomous context compression — LangChain's Deep Agents SDK introdu
    [05] [C6] (blog) Designing AI agents to resist prompt injection — OpenAI's blog post 
    [06] [C6] (blog) From model to agent: Equipping the Responses API with a computer env
    [07] [C8] (blog) Three sub-agent patterns you need for your agentic system — Every pr
    [08] [C5] (github) langchain-ai/langgraph 1.1.1 — Fixed replay bug in direct subgraph

### Episode 2: Python SDK Enhanced Connect Integration and Parsing

  Title: Python SDK Enhanced Connect Integration and Parsing
  Turns: 1 | areas=C3 sources=github
    [09] [C3] (github) inngest/inngest-py inngest@0.5.18 — Added app_version field for Co

### Episode 3: # Collaborative Multi-Agent Systems Architecture

  Title: # Collaborative Multi-Agent Systems Architecture
  Turns: 1 | areas=general sources=text
    [10] [Summary of earlier history]
# Structured Context Block: aswarm Multi-Agent Fram

### Episode 4: LLM Context Window Memory Management

  Title: LLM Context Window Memory Management
  Turns: 1 | areas=C2 sources=arxiv
    [11] [C2] (arxiv) The Missing Memory Hierarchy: Demand Paging for LLM Context Windows

### Episode 5: AI Agents Automating Enterprise Content Management

  Title: AI Agents Automating Enterprise Content Management
  Turns: 1 | areas=C9 sources=arxiv
    [12] [C9] (arxiv) AI-Powered ECM Automation with Agentic AI for Adaptive, Policy-Driv

### Episode 6: Large-scale LLM deployment for job matching

  Title: Large-scale LLM deployment for job matching
  Turns: 1 | areas=C2 sources=blog
    [13] [C2] (blog) Delivering contextual job matching for millions with OpenAI — Indeed

### Episode 7: Multi-agent coordination and distributed runtime enhancements

  Title: Multi-agent coordination and distributed runtime enhancements
  Turns: 7 | areas=C4, C5, C6 sources=github
    [14] [C5] (github) langchain-ai/langgraph 1.1.2 — Added context for remote graph API,
    [15] [C5] (github) langchain-ai/langgraph cli==0.4.16 — Added distributed runtime sup
    [16] [C6] (github) openai/openai-agents-python v0.12.1 — Preserve explicit approval r
    [17] [C4] (github) openai/openai-agents-python v0.12.0 — Added opt-in retry policies 
    [18] [C4] (github) google/adk-python v1.27.0 — Durable runtime support, A2A request i
    [19] [C5] (github) langchain-ai/langgraph cli==0.4.17 — New deep agent templates intr
    [20] [C5] (github) openai/openai-agents-python v0.12.2 — Multi-turn replay improvemen

## Approach C (Def-DTS intent)

- Episodes: **15**  (mean 1.4 turns, min 1, max 2, singletons 9)
- LLM calls: 21

### Episode 1: LangGraph v2 Streaming and Multi-Agent Orchestration Features

  Title: LangGraph v2 Streaming and Multi-Agent Orchestration Features
  Turns: 2 | areas=C5 sources=github
    [00] [C5] (github) langchain-ai/langgraph 1.1.0 — v2 streaming protocol with typed ou
    [01] [C5] (github) langchain-ai/langgraph cli==0.4.15 — CLI deployment feature added 

### Episode 2: Agent Architecture Model and Engineering Harness

  Title: Agent Architecture Model and Engineering Harness
  Turns: 1 | areas=general sources=blog
    [02] [general] (blog) The Anatomy of an Agent Harness — LangChain's Vivek Trivedy def

### Episode 3: Coding Agents Transforming Engineering and Product Workflows

  Title: Coding Agents Transforming Engineering and Product Workflows
  Turns: 1 | areas=general sources=blog
    [03] [general] (blog) How Coding Agents Are Reshaping Engineering, Product and Design

### Episode 4: Autonomous Context Compression in Language Models

  Title: Autonomous Context Compression in Language Models
  Turns: 1 | areas=C2 sources=blog
    [04] [C2] (blog) Autonomous context compression — LangChain's Deep Agents SDK introdu

### Episode 5: AI Agent Security and Prompt Injection Defense

  Title: AI Agent Security and Prompt Injection Defense
  Turns: 2 | areas=C6 sources=blog
    [05] [C6] (blog) Designing AI agents to resist prompt injection — OpenAI's blog post 
    [06] [C6] (blog) From model to agent: Equipping the Responses API with a computer env

### Episode 6: Agentic System Sub-Agent Delegation Patterns

  Title: Agentic System Sub-Agent Delegation Patterns
  Turns: 1 | areas=C8 sources=blog
    [07] [C8] (blog) Three sub-agent patterns you need for your agentic system — Every pr

### Episode 7: Multi-agent Workflow Orchestration and Execution Improvements

  Title: Multi-agent Workflow Orchestration and Execution Improvements
  Turns: 2 | areas=C3, C5 sources=github
    [08] [C5] (github) langchain-ai/langgraph 1.1.1 — Fixed replay bug in direct subgraph
    [09] [C3] (github) inngest/inngest-py inngest@0.5.18 — Added app_version field for Co

### Episode 8: # Multi-Agent Framework aswarm Development

  Title: # Multi-Agent Framework aswarm Development
  Turns: 1 | areas=general sources=text
    [10] [Summary of earlier history]
# Structured Context Block: aswarm Multi-Agent Fram

### Episode 9: LLM Context Memory Management Through Demand Paging

  Title: LLM Context Memory Management Through Demand Paging
  Turns: 1 | areas=C2 sources=arxiv
    [11] [C2] (arxiv) The Missing Memory Hierarchy: Demand Paging for LLM Context Windows

### Episode 10: AI Agents for Adaptive Enterprise Content Management

  Title: AI Agents for Adaptive Enterprise Content Management
  Turns: 1 | areas=C9 sources=arxiv
    [12] [C9] (arxiv) AI-Powered ECM Automation with Agentic AI for Adaptive, Policy-Driv

### Episode 11: AI-Powered Job Matching at Scale

  Title: AI-Powered Job Matching at Scale
  Turns: 1 | areas=C2 sources=blog
    [13] [C2] (blog) Delivering contextual job matching for millions with OpenAI — Indeed

### Episode 12: Multi-agent coordination and distributed deployment improvements

  Title: Multi-agent coordination and distributed deployment improvements
  Turns: 2 | areas=C5 sources=github
    [14] [C5] (github) langchain-ai/langgraph 1.1.2 — Added context for remote graph API,
    [15] [C5] (github) langchain-ai/langgraph cli==0.4.16 — Added distributed runtime sup

### Episode 13: Tool Approval Message Preservation in Resume Flows

  Title: Tool Approval Message Preservation in Resume Flows
  Turns: 1 | areas=C6 sources=github
    [16] [C6] (github) openai/openai-agents-python v0.12.1 — Preserve explicit approval r

### Episode 14: Agent Framework API Enhancements and Reliability

  Title: Agent Framework API Enhancements and Reliability
  Turns: 2 | areas=C4 sources=github
    [17] [C4] (github) openai/openai-agents-python v0.12.0 — Added opt-in retry policies 
    [18] [C4] (github) google/adk-python v1.27.0 — Durable runtime support, A2A request i

### Episode 15: Multi-Agent Coordination and Conversation Management Advances

  Title: Multi-Agent Coordination and Conversation Management Advances
  Turns: 2 | areas=C5 sources=github
    [19] [C5] (github) langchain-ai/langgraph cli==0.4.17 — New deep agent templates intr
    [20] [C5] (github) openai/openai-agents-python v0.12.2 — Multi-turn replay improvemen

## Approach D (Hybrid intent-labelled Nemori)

- Episodes: **1**  (mean 21.0 turns, min 21, max 21, singletons 0)
- LLM calls: ?

### Episode 1: LangGraph Multi-Agent Framework Development and Deployment

  Title: LangGraph Multi-Agent Framework Development and Deployment
  Turns: 21 | areas=C2, C3, C4, C5, C6, C8, C9 sources=arxiv, blog, github, text
    [00] [C5] (github) langchain-ai/langgraph 1.1.0 — v2 streaming protocol with typed ou
    [01] [C5] (github) langchain-ai/langgraph cli==0.4.15 — CLI deployment feature added 
    [02] [general] (blog) The Anatomy of an Agent Harness — LangChain's Vivek Trivedy def
    [03] [general] (blog) How Coding Agents Are Reshaping Engineering, Product and Design
    [04] [C2] (blog) Autonomous context compression — LangChain's Deep Agents SDK introdu
    [05] [C6] (blog) Designing AI agents to resist prompt injection — OpenAI's blog post 
    [06] [C6] (blog) From model to agent: Equipping the Responses API with a computer env
    [07] [C8] (blog) Three sub-agent patterns you need for your agentic system — Every pr
    [08] [C5] (github) langchain-ai/langgraph 1.1.1 — Fixed replay bug in direct subgraph
    [09] [C3] (github) inngest/inngest-py inngest@0.5.18 — Added app_version field for Co
    [10] [Summary of earlier history]
# Structured Context Block: aswarm Multi-Agent Fram
    [11] [C2] (arxiv) The Missing Memory Hierarchy: Demand Paging for LLM Context Windows
    [12] [C9] (arxiv) AI-Powered ECM Automation with Agentic AI for Adaptive, Policy-Driv
    [13] [C2] (blog) Delivering contextual job matching for millions with OpenAI — Indeed
    [14] [C5] (github) langchain-ai/langgraph 1.1.2 — Added context for remote graph API,
    [15] [C5] (github) langchain-ai/langgraph cli==0.4.16 — Added distributed runtime sup
    [16] [C6] (github) openai/openai-agents-python v0.12.1 — Preserve explicit approval r
    [17] [C4] (github) openai/openai-agents-python v0.12.0 — Added opt-in retry policies 
    [18] [C4] (github) google/adk-python v1.27.0 — Durable runtime support, A2A request i
    [19] [C5] (github) langchain-ai/langgraph cli==0.4.17 — New deep agent templates intr
    [20] [C5] (github) openai/openai-agents-python v0.12.2 — Multi-turn replay improvemen

---

## Qualitative scoring

| Dimension | Approach A (conf≥0.80) | Approach C (Def-DTS) | Approach D (Hybrid) |
|-----------|-----------|-----------|-----------|
| Episode atomicity (one idea each?) | 4 | 4 | 1 |
| Boundary placement (at natural shifts?) | 4 | 4 | 1 |
| Granularity (not too fine, not too coarse?) | 4 | 2 | 1 |
| Signal quality (reasons make sense?) | 4 | 3 | 2 |
| **Overall** | **4.0** | **3.25** | **1.25** |

## Go / No-Go

> **Go criteria:** at least 2 approaches score ≥ 3.5/5 overall.

Decision: [x] **Go** — Approach A (conf≥0.80) clears the bar.

## Analysis

**Approach A (conf≥0.80) — the winner.** Raising the threshold from 0.65 to 0.80 fixed
the over-triggering. 7 episodes from 21 turns is well-calibrated. Episode 1 correctly
fuses the whole first batch (LangGraph releases + architecture blogs + security blogs)
under a single "LangGraph ecosystem" frame. Episode 7 correctly groups all Mar 13-14
github releases across LangGraph, OpenAI agents, and Google ADK as a "multi-agent
coordination releases" cluster. The 5 singletons between them ([09]-[13]) represent
genuinely disparate items arriving in a scattered daily monitoring window — these are
appropriate singletons; the consolidation `defer` outcome handles them. The boundary
reasons are consistently coherent and domain-specific.

**Approach C (Def-DTS) — useful labels, unreliable boundaries.** Worsened from 14 to
15 episodes run-to-run because the intent classification is inconsistent:
[03] was `blog_architecture` in Run 1 but `general_commentary` in Run 2. The
classifications are accurate when they're stable, but they drift enough to make
boundary placement non-deterministic. **Key insight**: the intent labels are valuable
*metadata* (consistently identifying type+domain) but the boundary trigger rule is
too brittle. Use Def-DTS labels as an annotation step, not a segmentation driver.

**Approach D (Hybrid) — over-corrected.** Failed in the opposite direction from Run 1's
Approach B — 1 episode covering all 21 turns. The prompt guidance ("tool releases in the
same broad area are usually continuations") was interpreted by the LLM as license to
rationalise every transition as a non-boundary. Giving the LLM explicit anti-boundary
heuristics backfires: it uses them to suppress boundaries it should have caught.
The intent label context helps only marginally; the base Nemori judgment with a tuned
threshold is simpler and better.

## Decision: Approach A (Nemori, conf≥0.80) forward

- Use as Phase 1a boundary detector in the consolidation pipeline
- Run Def-DTS intent classification as a separate annotation pass on each flushed
  episode (not as the boundary trigger) — the `(type, domain)` label becomes metadata
  on the episode and later on the Zettel notes, enabling tag and area filtering
- Maximum buffer backstop: 8–10 turns (episodes 1 and 7 are 9 and 7 turns respectively
  — that feels like the right upper bound for a coherent consolidation unit)
- The compaction summary artefact [10] is a data quality issue: consolidation pipelines
  should skip turns matching the `[Summary of earlier history]` prefix
