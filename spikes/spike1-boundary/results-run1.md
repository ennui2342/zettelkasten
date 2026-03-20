# Spike 1 — Episode Boundary Detection: Results

*Generated 2026-03-14 16:00*

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

## Approach A (Nemori naïve)

- Episodes: **11**  (mean 1.9 turns, min 1, max 5, singletons 6)
- LLM calls: 20

### Episode 1: LangGraph Agents: Streaming, Orchestration, Architecture

  Title: LangGraph Agents: Streaming, Orchestration, Architecture
  Turns: 5 | areas=C2, C5 sources=blog, github
    [00] [C5] (github) langchain-ai/langgraph 1.1.0 — v2 streaming protocol with typed ou
    [01] [C5] (github) langchain-ai/langgraph cli==0.4.15 — CLI deployment feature added 
    [02] [general] (blog) The Anatomy of an Agent Harness — LangChain's Vivek Trivedy def
    [03] [general] (blog) How Coding Agents Are Reshaping Engineering, Product and Design
    [04] [C2] (blog) Autonomous context compression — LangChain's Deep Agents SDK introdu

### Episode 2: AI Agent Security and Architecture Patterns

  Title: AI Agent Security and Architecture Patterns
  Turns: 4 | areas=C5, C6, C8 sources=blog, github
    [05] [C6] (blog) Designing AI agents to resist prompt injection — OpenAI's blog post 
    [06] [C6] (blog) From model to agent: Equipping the Responses API with a computer env
    [07] [C8] (blog) Three sub-agent patterns you need for your agentic system — Every pr
    [08] [C5] (github) langchain-ai/langgraph 1.1.1 — Fixed replay bug in direct subgraph

### Episode 3: Python SDK Version Control and Duration Parsing Improvements

  Title: Python SDK Version Control and Duration Parsing Improvements
  Turns: 1 | areas=C3 sources=github
    [09] [C3] (github) inngest/inngest-py inngest@0.5.18 — Added app_version field for Co

### Episode 4: Multi-agent collaborative framework architecture design

  Title: Multi-agent collaborative framework architecture design
  Turns: 1 | areas=general sources=text
    [10] [Summary of earlier history]
# Structured Context Block: aswarm Multi-Agent Fram

### Episode 5: LLM Context Window Demand Paging System

  Title: LLM Context Window Demand Paging System
  Turns: 1 | areas=C2 sources=arxiv
    [11] [C2] (arxiv) The Missing Memory Hierarchy: Demand Paging for LLM Context Windows

### Episode 6: AI-Driven Enterprise Content Management Automation

  Title: AI-Driven Enterprise Content Management Automation
  Turns: 1 | areas=C9 sources=arxiv
    [12] [C9] (arxiv) AI-Powered ECM Automation with Agentic AI for Adaptive, Policy-Driv

### Episode 7: Large-Scale LLM Job Matching at Enterprise Scale

  Title: Large-Scale LLM Job Matching at Enterprise Scale
  Turns: 1 | areas=C2 sources=blog
    [13] [C2] (blog) Delivering contextual job matching for millions with OpenAI — Indeed

### Episode 8: Multi-agent coordination and distributed runtime improvements

  Title: Multi-agent coordination and distributed runtime improvements
  Turns: 2 | areas=C5 sources=github
    [14] [C5] (github) langchain-ai/langgraph 1.1.2 — Added context for remote graph API,
    [15] [C5] (github) langchain-ai/langgraph cli==0.4.16 — Added distributed runtime sup

### Episode 9: Agent Tool Approval and Retry Policy Management

  Title: Agent Tool Approval and Retry Policy Management
  Turns: 2 | areas=C4, C6 sources=github
    [16] [C6] (github) openai/openai-agents-python v0.12.1 — Preserve explicit approval r
    [17] [C4] (github) openai/openai-agents-python v0.12.0 — Added opt-in retry policies 

### Episode 10: Dynamic Multi-Agent Architecture with Interceptor Support

  Title: Dynamic Multi-Agent Architecture with Interceptor Support
  Turns: 1 | areas=C4 sources=github
    [18] [C4] (github) google/adk-python v1.27.0 — Durable runtime support, A2A request i

### Episode 11: Multi-Agent Coordination and Workflow Management Advances

  Title: Multi-Agent Coordination and Workflow Management Advances
  Turns: 2 | areas=C5 sources=github
    [19] [C5] (github) langchain-ai/langgraph cli==0.4.17 — New deep agent templates intr
    [20] [C5] (github) openai/openai-agents-python v0.12.2 — Multi-turn replay improvemen

## Approach B (ES-Mem two-stage)

- Episodes: **2**  (mean 10.5 turns, min 9, max 12, singletons 0)
- LLM calls: see output above

### Episode 1: LangGraph Streaming, Agents, and Multi-Agent Orchestration

  Title: LangGraph Streaming, Agents, and Multi-Agent Orchestration
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

### Episode 2: Multi-Agent Framework Orchestration and Context Management

  Title: Multi-Agent Framework Orchestration and Context Management
  Turns: 12 | areas=C2, C3, C4, C5, C6, C9 sources=arxiv, blog, github, text
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

## Approach C (Def-DTS intent)

- Episodes: **14**  (mean 1.5 turns, min 1, max 2, singletons 7)
- LLM calls: 21

### Episode 1: LangGraph v2 Streaming and Multi-Agent Deployment Updates

  Title: LangGraph v2 Streaming and Multi-Agent Deployment Updates
  Turns: 2 | areas=C5 sources=github
    [00] [C5] (github) langchain-ai/langgraph 1.1.0 — v2 streaming protocol with typed ou
    [01] [C5] (github) langchain-ai/langgraph cli==0.4.15 — CLI deployment feature added 

### Episode 2: Agents as Engineering Harnesses Transforming Workflows

  Title: Agents as Engineering Harnesses Transforming Workflows
  Turns: 2 | areas=general sources=blog
    [02] [general] (blog) The Anatomy of an Agent Harness — LangChain's Vivek Trivedy def
    [03] [general] (blog) How Coding Agents Are Reshaping Engineering, Product and Design

### Episode 3: Autonomous Context Compression for Language Models

  Title: Autonomous Context Compression for Language Models
  Turns: 1 | areas=C2 sources=blog
    [04] [C2] (blog) Autonomous context compression — LangChain's Deep Agents SDK introdu

### Episode 4: AI Agent Security and Sandbox Execution

  Title: AI Agent Security and Sandbox Execution
  Turns: 2 | areas=C6 sources=blog
    [05] [C6] (blog) Designing AI agents to resist prompt injection — OpenAI's blog post 
    [06] [C6] (blog) From model to agent: Equipping the Responses API with a computer env

### Episode 5: Agentic System Sub-Agent Delegation Patterns

  Title: Agentic System Sub-Agent Delegation Patterns
  Turns: 1 | areas=C8 sources=blog
    [07] [C8] (blog) Three sub-agent patterns you need for your agentic system — Every pr

### Episode 6: Graph-Based Agent Coordination and Workflow Configuration

  Title: Graph-Based Agent Coordination and Workflow Configuration
  Turns: 2 | areas=C3, C5 sources=github
    [08] [C5] (github) langchain-ai/langgraph 1.1.1 — Fixed replay bug in direct subgraph
    [09] [C3] (github) inngest/inngest-py inngest@0.5.18 — Added app_version field for Co

### Episode 7: aswarm Multi-Agent Framework Development and Synthesis

  Title: aswarm Multi-Agent Framework Development and Synthesis
  Turns: 1 | areas=general sources=text
    [10] [Summary of earlier history]
# Structured Context Block: aswarm Multi-Agent Fram

### Episode 8: LLM Context Memory Hierarchy and Demand Paging

  Title: LLM Context Memory Hierarchy and Demand Paging
  Turns: 1 | areas=C2 sources=arxiv
    [11] [C2] (arxiv) The Missing Memory Hierarchy: Demand Paging for LLM Context Windows

### Episode 9: AI-Powered Enterprise Content Management Automation

  Title: AI-Powered Enterprise Content Management Automation
  Turns: 1 | areas=C9 sources=arxiv
    [12] [C9] (arxiv) AI-Powered ECM Automation with Agentic AI for Adaptive, Policy-Driv

### Episode 10: AI-Powered Job Matching at Enterprise Scale

  Title: AI-Powered Job Matching at Enterprise Scale
  Turns: 1 | areas=C2 sources=blog
    [13] [C2] (blog) Delivering contextual job matching for millions with OpenAI — Indeed

### Episode 11: Multi-agent coordination and distributed deployment improvements

  Title: Multi-agent coordination and distributed deployment improvements
  Turns: 2 | areas=C5 sources=github
    [14] [C5] (github) langchain-ai/langgraph 1.1.2 — Added context for remote graph API,
    [15] [C5] (github) langchain-ai/langgraph cli==0.4.16 — Added distributed runtime sup

### Episode 12: Tool Approval Workflow Message Preservation

  Title: Tool Approval Workflow Message Preservation
  Turns: 1 | areas=C6 sources=github
    [16] [C6] (github) openai/openai-agents-python v0.12.1 — Preserve explicit approval r

### Episode 13: Configurable agent retry policies and runtime enhancements

  Title: Configurable agent retry policies and runtime enhancements
  Turns: 2 | areas=C4 sources=github
    [17] [C4] (github) openai/openai-agents-python v0.12.0 — Added opt-in retry policies 
    [18] [C4] (github) google/adk-python v1.27.0 — Durable runtime support, A2A request i

### Episode 14: Multi-Agent Coordination and Replay Improvements

  Title: Multi-Agent Coordination and Replay Improvements
  Turns: 2 | areas=C5 sources=github
    [19] [C5] (github) langchain-ai/langgraph cli==0.4.17 — New deep agent templates intr
    [20] [C5] (github) openai/openai-agents-python v0.12.2 — Multi-turn replay improvemen

---

## Qualitative scoring

| Dimension | Approach A | Approach B | Approach C |
|-----------|-----------|-----------|-----------|
| Episode atomicity (one idea each?) | 3 | 1 | 4 |
| Boundary placement (at natural shifts?) | 4 | 2 | 4 |
| Granularity (not too fine, not too coarse?) | 3 | 1 | 2 |
| Signal quality (reasons make sense?) | 4 | 2 | 4 |
| **Overall** | **3.5** | **1.5** | **3.5** |

## Go / No-Go

> **Go criteria:** at least 2 approaches score ≥ 3.5/5 overall.

Decision: [x] Iterate (A and C both hit 3.5 but both have fixable granularity issues)

## Analysis

**Approach B — eliminated.** Only 1 candidate boundary detected across 21 turns. The
word-overlap cosine pre-filter is blind to topic shifts in domain-coherent data: all
research findings share vocabulary ("agent", "pipeline", "coordination") regardless of
topic. ES-Mem is designed for conversational dialogue where vocabulary shifts are
reliable. For specialised research streams, the pre-filter would need semantic embeddings
— at which point it's no longer a cheap stage-1. Drop from further evaluation.

**Approach C — right signal, too granular.** Intent classifications are accurate and
consistent: every turn correctly typed. The failure is in the boundary rule: any intent
change triggers a split, producing 14 episodes with 7 singletons. `blog_memory_compaction`
and `arxiv_memory` (both C2) should group; consecutive github releases across related
tools shouldn't split on tool name alone. Fix: coarsen the taxonomy OR use the intent
label as *context for Approach A* rather than as the direct boundary trigger.

**Approach A — best overall, over-triggers.** Episode groupings are semantically sound
(ep1 fuses LangGraph releases + architecture blogs correctly; ep2 groups security/agent
patterns). Singletons [10]-[13] reflect genuinely anomalous items (compaction artefact,
disparate arXiv papers, isolated case study) — these may actually be correct. Primary
issue: `CONFIDENCE_THRESHOLD=0.65` is too permissive. Raising to 0.80 would likely
eliminate 2–4 spurious boundaries.

**Iteration plan (Run 2):**
- Approach A: raise `CONFIDENCE_THRESHOLD` to 0.80
- Approach D (hybrid): pre-label each turn with Def-DTS intent taxonomy, inject label
  as structured context into the Nemori boundary judgment. The LLM gets a typed signal
  to reason with rather than relying on raw text similarity alone.
- Drop Approach B; keep C as-is for comparison baseline.
