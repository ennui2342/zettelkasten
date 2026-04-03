# Case 4: Same-topic EDIT: evaluation note + evaluation benchmarking draft

**Draft:** Evaluation and Benchmarking of AI Agents

---

## Original (8,597 chars)

## Evaluation Frameworks for Real-World Agent Deployment

As agents transition from closed sandboxes to real-world deployment, evaluation methodologies must evolve beyond task accuracy alone. A comprehensive assessment framework addresses five critical dimensions: **Cost**, **Latency**, **Accuracy**, **Security**, and **Stability** (the CLASSic framework). Each dimension captures failure modes that standard benchmarks routinely miss.

### Cost

Cost reflects the efficiency–intelligence trade-off inherent in agent design. High reasoning depth often comes at significant computational overhead: hierarchical architectures maximize task proficiency but incur exponential increases in token consumption compared to linear chains or zero-shot prompting. This remains a critical bottleneck for deploying agents in cost-sensitive, real-time applications. Production evaluation must report token budgets and dollar costs alongside accuracy to enable meaningful system comparison.

### Latency

Latency evaluation reveals that agents frequently fail when tasks involve variable temporal delays. Asynchronous benchmarks demonstrate that while synchronous agents achieve moderate success rates, asynchronous settings cause performance to plummet dramatically, highlighting a critical lack of temporal awareness in current planners. For safety-critical domains like autonomous driving where sub-100ms response times are mandatory, knowledge distillation approaches compress large multimodal planners into compact edge-deployable models. Latency budgets must be treated as hard constraints rather than secondary metrics.

### Accuracy in Agentic Contexts

Accuracy for agents is not captured by static question-answering alone—success can collapse when tasks require tool use, state tracking, and long-horizon recovery. Several benchmarks target this gap:

- **GAIA** highlights failures on human-easy tasks requiring multi-step decomposition and verification across three difficulty tiers involving file reading, web browsing, and coding.
- **OSWorld Verified** reduces evaluation noise for desktop control tasks.
- **SWE-bench Verified** and **SWE-bench Pro** address software engineering evaluation at increasing scales.
- **τ-bench** evaluates multi-turn tool interaction under policies in domains like retail and airlines.
- **FrontierMath** targets hard-ceiling mathematical reasoning with reduced contamination risk.
- **AgentBench** evaluates agents across diverse environments.
- **MultiAgentBench (MARBLE)** measures emergent multi-agent behaviors such as negotiation efficiency and consensus formation.
- **OfficeBench** evaluates office automation at single-, cross-, and multi-application complexity with programmatic state comparison.
- **BrowseComp+** targets web browsing capabilities specifically.

Modern agent evaluation increasingly reports compute budgets, run-to-run variance, and failure severity distributions alongside mean success rates.

### Goal-Directed Agent Benchmarks

A distinct class of benchmarks evaluates whether agents can perform complex, multi-step work episodes that go beyond single-turn generation. These benchmarks require agents to manipulate, analyze, and synthesize structured artifacts—spreadsheets, documents, figures, and PDFs—across extended task horizons in practical domains such as data analysis, document authoring, and visual reporting. Correctness is demonstrated through verifiable outputs rather than language-only responses: agents must emit concrete artifacts (e.g., Markdown files, spreadsheets, or images) that downstream evaluators can deterministically check.

**GDPVal** exemplifies this approach as a large-scale benchmark for goal-directed agents on economically valuable tasks. Tasks require multi-step reasoning and tool use, with agents accessing diverse tool categories for file operations, data manipulation, and content generation. After filtering for supported file types, a typical experimental setup retains on the order of 200 tasks split into training and evaluation partitions.

Evaluation in such benchmarks combines deterministic code-based checks with model-based judgments. Code rules execute as Python functions with access to all intermediate and final task resources, enabling schema validation, bounds tests, and consistency verification. Model-based judges use vision-language models capable of reading rendered artifacts and applying structured scoring prompts. This hybrid methodology balances objectivity and coverage: code handles verifiable, deterministic properties while model judges assess higher-level reasoning and qualitative attributes.

**Test-time scaling** through best-of-N sampling—generating multiple candidate outputs and selecting the highest-scoring one—yields monotonic improvement with increasing N, with each doubling of candidates producing consistent absolute gains. Notably, the scaling behavior is similar whether outputs are scored by learned evaluation functions or oracle evaluators, suggesting that well-designed evaluation proxies can approximate oracle scoring even without direct access to ground-truth utility functions. This finding has practical implications for deployment: reliable proxy evaluators can serve as runtime selectors without requiring expensive human or oracle feedback loops.

### Stability and Failure Mode Analysis

Stability refers to system variance over repeated runs and resilience to minor perturbations. In stochastic systems like LLM agents, simple success rate metrics often mask critical reliability issues. Rigorous evaluation must include failure mode analysis, quantifying not just how often an agent succeeds but the severity distribution of its failures—distinguishing benign timeouts from catastrophic data leaks. Low reliability scores on complex workflows (pass^k metrics peaking around 6%) suggest that single-trial success rates dramatically overestimate the consistency real deployments demand.

In regulated domains such as healthcare, agents must demonstrate high compliance stability, ensuring clinical decisions consistently align with medical guidelines regardless of prompt phrasing or sampling temperature. Future benchmarks must report standard deviation and worst-case failure scenarios alongside mean performance.

### Security

Security evaluation remains underdeveloped relative to its importance. Agents with tool access, file system permissions, or network capabilities introduce attack surfaces absent in pure text generation. Evaluation must assess PII protection, constraint adherence, rule compliance, and resistance to adversarial prompt injection. A correct but unsafe plan, or an accurate but unjustified diagnosis, may be unacceptable in enterprise contexts. Multi-dimensional criteria spanning plan correctness, reasoning quality, and safety compliance are essential for deployment readiness assessment.

### Toward Production-Grade Evaluation

The gap between research benchmarks and production requirements remains substantial. Enterprise benchmarks lack multimodal coverage (documents, images, PDFs), likely underestimating context inflation and tool interaction challenges—a gap that goal-directed benchmarks like GDPVal begin to address by requiring agents to produce and be evaluated on diverse artifact types. Most academic evaluations neglect latency and cost despite their centrality to deployment decisions. Bridging this gap requires benchmarks that jointly optimize across all CLASSic dimensions, employ hybrid evaluation combining deterministic code checks with model-based judgment, report distributional rather than point estimates of performance, and ground evaluation in realistic operational conditions rather than sanitized test sets.

## See Also

- [[z20260318-027|Benchmarking and Evaluation of LLM-Based Agent Systems]] — provides the foundational benchmarking methodology and metrics that production evaluation extends
- [[z20260318-024|Multi-Agent Systems with Large Language Models]] — describes the multi-agent architectures whose cost-latency-accuracy trade-offs production evaluation must capture
- [[z20260318-001|Multi-Agent Architectures for Workflow Automation]] — grounds enterprise workflow complexity levels that motivate stability and security evaluation dimensions
- [[z20260318-053|Non-Determinism, Failure Modes, and Reliability Challenges in Agentic AI]] — analyzes the non-determinism and failure propagation dynamics that stability evaluation must detect
- [[z20260318-054|Multi-Pillar Behavioral Testing of Agentic AI Systems]] — complements deployment-level evaluation with fine-grained behavioral testing across agent subsystems

---

## Current _STEP2_EDIT (5,268 chars, 61% of original)

## Evaluation Frameworks for Real-World Agent Deployment

As agents move from sandboxes to production, evaluation must extend beyond task accuracy. The **CLASSic framework** addresses five dimensions: **Cost, Latency, Accuracy, Security, and Stability**.

### Cost

High reasoning depth incurs significant computational overhead—hierarchical architectures maximize proficiency but exponentially increase token consumption versus linear chains or zero-shot prompting. Production evaluation must report token budgets and dollar costs alongside accuracy.

### Latency

Agents frequently fail under variable temporal delays. Asynchronous benchmarks like Robotouille show dramatic drops (47% synchronous → 11% asynchronous), exposing poor temporal awareness in current planners. In safety-critical domains requiring sub-100ms responses, knowledge distillation compresses large planners into edge-deployable models. Latency budgets must be hard constraints, not secondary metrics.

### Accuracy

Agent accuracy collapses when tasks require tool use, state tracking, and long-horizon recovery—beyond what static QA captures. Key benchmarks targeting this gap:

- **GAIA**: multi-step decomposition across three difficulty tiers (file reading, web browsing, coding)
- **OSWorld Verified / SWE-bench Verified / SWE-bench Pro**: desktop control and software engineering at increasing scale
- **τ-bench**: multi-turn tool interaction under domain policies (retail, airlines)
- **FrontierMath**: hard-ceiling mathematical reasoning with reduced contamination risk
- **AgentBench / MultiAgentBench (MARBLE)**: diverse environments and emergent multi-agent behaviors (negotiation, consensus)
- **OfficeBench**: office automation across single-, cross-, and multi-application complexity
- **BrowseComp+**: web browsing capabilities

Modern evaluation increasingly reports compute budgets, run-to-run variance, and failure severity distributions alongside mean success rates.

### Goal-Directed Benchmarks

A distinct benchmark class evaluates complex, multi-step work episodes requiring agents to produce verifiable artifacts—spreadsheets, documents, figures, PDFs—rather than language-only responses.

**GDPVal** exemplifies this as a large-scale benchmark for goal-directed agents on economically valuable tasks, with ~200 tasks requiring multi-step reasoning and diverse tool use. Evaluation combines **deterministic code checks** (schema validation, bounds tests, consistency) with **model-based judges** (vision-language models scoring rendered artifacts), balancing objectivity and coverage.

**Test-time scaling** via best-of-N sampling yields monotonic improvement, with each doubling of candidates producing consistent gains. Scaling behavior is similar whether scored by learned evaluators or oracles, suggesting well-designed proxy evaluators can approximate oracle scoring—enabling runtime selection without expensive human feedback.

### Stability

In stochastic LLM agents, simple success rates mask reliability issues. Rigorous evaluation must quantify failure severity distributions—distinguishing benign timeouts from catastrophic data leaks. Pass^k metrics peaking around 6% on complex workflows suggest single-trial rates dramatically overestimate deployment consistency. In regulated domains like healthcare, agents must demonstrate compliance stability regardless of prompt phrasing or sampling temperature. Benchmarks must report standard deviation and worst-case scenarios alongside means.

### Security

Security evaluation remains underdeveloped. Agents with tool access, file system permissions, or network capabilities introduce attack surfaces absent in text generation. Evaluation must assess PII protection, constraint adherence, rule compliance, and adversarial prompt injection resistance. A correct but unsafe plan may be unacceptable—multi-dimensional criteria spanning correctness, reasoning quality, and safety compliance are essential.

### Toward Production-Grade Evaluation

Enterprise benchmarks lack multimodal coverage, likely underestimating context inflation and tool interaction challenges—a gap goal-directed benchmarks like GDPVal begin to address. Most academic evaluations neglect latency and cost despite their deployment centrality. Bridging this requires benchmarks that jointly optimize across all CLASSic dimensions, employ hybrid deterministic-plus-model-based evaluation, report distributional rather than point estimates, and ground assessment in realistic operational conditions.

## See Also

- [[z20260318-027|Benchmarking and Evaluation of LLM-Based Agent Systems]] — foundational benchmarking methodology that production evaluation extends
- [[z20260318-024|Multi-Agent Systems with Large Language Models]] — multi-agent architectures whose cost-latency-accuracy trade-offs production evaluation must capture
- [[z20260318-001|Multi-Agent Architectures for Workflow Automation]] — enterprise workflow complexity motivating stability and security dimensions
- [[z20260318-053|Non-Determinism, Failure Modes, and Reliability Challenges in Agentic AI]] — non-determinism and failure propagation that stability evaluation must detect
- [[z20260318-054|Multi-Pillar Behavioral Testing of Agentic AI Systems]] — fine-grained behavioral testing complementing deployment-level evaluation

---

## Candidate step2_edit.txt (5,187 chars, 60% of original)

## Evaluation Frameworks for Real-World Agent Deployment

As agents move from sandboxes to production, evaluation must go beyond task accuracy. The **CLASSic framework** assesses five dimensions: **Cost, Latency, Accuracy, Security, and Stability**.

### Cost

High reasoning depth incurs significant computational overhead—hierarchical architectures maximize proficiency but exponentially increase token consumption versus linear chains or zero-shot prompting. Production evaluation must report token budgets and dollar costs alongside accuracy.

### Latency

Agents frequently fail under variable temporal delays. Asynchronous benchmarks like Robotouille show dramatic drops (47% synchronous → 11% asynchronous), exposing poor temporal awareness in current planners. In safety-critical domains requiring sub-100ms responses, knowledge distillation compresses large planners into edge-deployable models. Latency budgets must be hard constraints, not secondary metrics.

### Accuracy in Agentic Contexts

Agent accuracy collapses when tasks require tool use, state tracking, and long-horizon recovery. Key benchmarks targeting this gap:

- **GAIA**: multi-step decomposition across three difficulty tiers (file reading, web browsing, coding)
- **OSWorld Verified / SWE-bench Verified / SWE-bench Pro**: desktop control and software engineering at increasing scale
- **τ-bench**: multi-turn tool interaction under domain policies (retail, airlines)
- **FrontierMath**: hard-ceiling mathematical reasoning with reduced contamination risk
- **AgentBench / MultiAgentBench (MARBLE)**: diverse environments and emergent multi-agent behaviors (negotiation, consensus)
- **OfficeBench**: office automation at single-, cross-, and multi-application complexity with programmatic state comparison
- **BrowseComp+**: web browsing capabilities

Modern evaluation increasingly reports compute budgets, run-to-run variance, and failure severity distributions alongside mean success rates.

### Goal-Directed Benchmarks

A distinct benchmark class evaluates complex, multi-step work episodes requiring agents to produce verifiable artifacts—spreadsheets, documents, figures, PDFs—rather than language-only responses.

**GDPVal** exemplifies this as a large-scale benchmark for goal-directed agents on economically valuable tasks. Evaluation combines deterministic code checks (schema validation, bounds tests, consistency) with vision-language model judges for higher-level reasoning and qualitative attributes.

**Test-time scaling** via best-of-N sampling yields monotonic improvement, with each doubling of candidates producing consistent gains. Scaling behavior is similar whether scored by learned evaluation functions or oracle evaluators, suggesting well-designed proxy evaluators can approximate oracle scoring—enabling runtime selection without expensive human feedback loops.

### Stability

In stochastic LLM agents, simple success rates mask critical reliability issues. Pass^k metrics peaking around 6% on complex workflows show that single-trial success rates dramatically overestimate deployment consistency. Evaluation must quantify failure severity distributions—distinguishing benign timeouts from catastrophic data leaks—and report standard deviation and worst-case scenarios. In regulated domains like healthcare, agents must demonstrate consistent guideline compliance regardless of prompt phrasing or sampling temperature.

### Security

Security evaluation remains underdeveloped. Agents with tool access, file system permissions, or network capabilities introduce attack surfaces absent in pure text generation. Evaluation must assess PII protection, constraint adherence, rule compliance, and adversarial prompt injection resistance. Multi-dimensional criteria spanning plan correctness, reasoning quality, and safety compliance are essential.

### Toward Production-Grade Evaluation

Enterprise benchmarks lack multimodal coverage (documents, images, PDFs), underestimating context inflation and tool interaction challenges—a gap goal-directed benchmarks like GDPVal begin to address. Most academic evaluations neglect latency and cost despite their deployment centrality. Bridging this gap requires benchmarks that jointly optimize across all CLASSic dimensions, employ hybrid deterministic-plus-model-based evaluation, report distributional rather than point estimates, and ground evaluation in realistic operational conditions.

## See Also

- [[z20260318-027|Benchmarking and Evaluation of LLM-Based Agent Systems]] — foundational benchmarking methodology that production evaluation extends
- [[z20260318-024|Multi-Agent Systems with Large Language Models]] — multi-agent architectures whose cost-latency-accuracy trade-offs production evaluation must capture
- [[z20260318-001|Multi-Agent Architectures for Workflow Automation]] — enterprise workflow complexity motivating stability and security dimensions
- [[z20260318-053|Non-Determinism, Failure Modes, and Reliability Challenges in Agentic AI]] — non-determinism and failure propagation that stability evaluation must detect
- [[z20260318-054|Multi-Pillar Behavioral Testing of Agentic AI Systems]] — fine-grained behavioral testing complementing deployment-level evaluation

