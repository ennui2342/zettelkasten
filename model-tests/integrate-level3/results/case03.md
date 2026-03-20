# Case 3: Failure case: focused evaluation note + different-topic (architectures) draft → EDIT

**Draft:** Hierarchical Multi-Agent Systems

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

## Current _STEP2_EDIT (5,692 chars, 66% of original)

## Evaluation Frameworks for Real-World Agent Deployment

As agents move from sandboxes to production, evaluation must extend beyond task accuracy. The **CLASSic framework** addresses five dimensions: **Cost**, **Latency**, **Accuracy**, **Security**, and **Stability**.

### Cost

High reasoning depth—especially in hierarchical multi-agent architectures where manager agents decompose tasks across specialized experts—incurs exponential token consumption compared to linear chains or zero-shot prompting. Production evaluation must report token budgets and dollar costs alongside accuracy.

### Latency

Agents frequently fail under variable temporal delays; asynchronous settings cause dramatic performance drops, exposing poor temporal awareness in current planners. Safety-critical domains (e.g., autonomous driving with sub-100ms requirements) use knowledge distillation to compress large planners into edge-deployable models. Latency budgets are hard constraints, not secondary metrics.

### Accuracy in Agentic Contexts

Static QA metrics miss failures in tool use, state tracking, and long-horizon recovery. Key benchmarks targeting this gap:

- **GAIA**: multi-step decomposition across difficulty tiers (file reading, web browsing, coding)
- **OSWorld Verified** / **SWE-bench Verified/Pro**: desktop control and software engineering tasks
- **τ-bench**: multi-turn tool interaction under domain policies (retail, airlines)
- **FrontierMath**: hard-ceiling mathematical reasoning with low contamination risk
- **AgentBench**: diverse environment evaluation
- **MultiAgentBench (MARBLE)**: emergent multi-agent behaviors (negotiation, consensus)
- **OfficeBench**: office automation at single-, cross-, and multi-application complexity
- **BrowseComp+**: web browsing capabilities

Modern evaluation increasingly reports compute budgets, run-to-run variance, and failure severity distributions.

### Goal-Directed Benchmarks

A distinct benchmark class requires agents to produce verifiable artifacts—spreadsheets, documents, figures, PDFs—across extended multi-step work episodes. **GDPVal** exemplifies this with ~200 economically valuable tasks requiring diverse tool use for file operations, data manipulation, and content generation.

Evaluation combines **deterministic code checks** (schema validation, bounds tests, consistency) with **model-based judges** (vision-language models scoring rendered artifacts). This hybrid balances objectivity and coverage.

**Test-time scaling** via best-of-N sampling yields monotonic improvement, with each doubling of candidates producing consistent gains. Scaling behavior is similar whether scored by learned evaluation functions or oracle evaluators, suggesting well-designed proxy evaluators can substitute for expensive oracle feedback at runtime.

### Stability

In stochastic LLM agents, mean success rates mask reliability issues. Rigorous evaluation requires failure severity distributions—distinguishing benign timeouts from catastrophic data leaks. Pass^k metrics peaking around 6% on complex workflows show that single-trial success rates dramatically overestimate deployment consistency. Regulated domains (e.g., healthcare) demand compliance stability across prompt variations and sampling temperatures. Benchmarks must report standard deviation and worst-case scenarios.

### Security

Agents with tool access, file system permissions, or network capabilities introduce attack surfaces absent in text generation. Evaluation must assess PII protection, constraint adherence, rule compliance, and adversarial prompt injection resistance. Multi-dimensional criteria spanning correctness, reasoning quality, and safety compliance are essential—a correct but unsafe plan may be unacceptable.

### Hierarchical Architectures and Evaluation Implications

Hierarchical multi-agent systems (HMAS) amplify evaluation challenges across all CLASSic dimensions. Manager-expert paradigms with feedback-driven replanning, centralized controllers (MetaGPT, AutoAct), and DAG-based "agent-as-a-tool" architectures enable sophisticated task decomposition and parallel execution—but multiply cost, latency, and failure propagation risks. Workflow orchestration modeled as directed conditional graphs, where nodes are agents and edges are control flow transitions, demands evaluation that captures emergent coordination behaviors alongside individual agent performance.

### Toward Production-Grade Evaluation

Enterprise benchmarks lack multimodal coverage, likely underestimating context inflation and tool interaction challenges—a gap goal-directed benchmarks like GDPVal begin to address. Most academic evaluations neglect latency and cost. Closing this gap requires benchmarks that jointly optimize across all CLASSic dimensions, employ hybrid deterministic/model-based evaluation, report distributional rather than point estimates, and ground assessment in realistic operational conditions.

## See Also

- [[z20260318-027|Benchmarking and Evaluation of LLM-Based Agent Systems]] — foundational benchmarking methodology that production evaluation extends
- [[z20260318-024|Multi-Agent Systems with Large Language Models]] — multi-agent architectures whose cost-latency-accuracy trade-offs production evaluation must capture
- [[z20260318-001|Multi-Agent Architectures for Workflow Automation]] — enterprise workflow complexity motivating stability and security dimensions
- [[z20260318-053|Non-Determinism, Failure Modes, and Reliability Challenges in Agentic AI]] — non-determinism and failure propagation that stability evaluation must detect
- [[z20260318-054|Multi-Pillar Behavioral Testing of Agentic AI Systems]] — fine-grained behavioral testing complementing deployment-level evaluation

---

## Candidate step2_edit.txt (5,308 chars, 62% of original)

## Evaluation Frameworks for Real-World Agent Deployment

As agents move from sandboxes to production, evaluation must extend beyond task accuracy. The **CLASSic framework** addresses five dimensions: **Cost**, **Latency**, **Accuracy**, **Security**, and **Stability**.

### Cost

High reasoning depth—especially in hierarchical multi-agent architectures where manager agents decompose tasks across specialist sub-agents—incurs exponential token consumption compared to linear chains or zero-shot prompting. Production evaluation must report token budgets and dollar costs alongside accuracy.

### Latency

Agents frequently fail under variable temporal delays; asynchronous settings cause dramatic performance drops, exposing poor temporal awareness in current planners. Safety-critical domains (e.g., autonomous driving with sub-100ms requirements) use knowledge distillation to compress large planners into edge-deployable models. Latency budgets must be hard constraints, not secondary metrics.

### Accuracy in Agentic Contexts

Agent accuracy collapses when tasks require tool use, state tracking, and long-horizon recovery. Key benchmarks targeting this gap:

- **GAIA**: multi-step decomposition across difficulty tiers (file reading, web browsing, coding)
- **OSWorld Verified** / **SWE-bench Verified/Pro**: desktop control and software engineering tasks
- **τ-bench**: multi-turn tool interaction under domain policies (retail, airlines)
- **FrontierMath**: hard-ceiling mathematical reasoning with low contamination risk
- **AgentBench**: diverse environment evaluation
- **MultiAgentBench (MARBLE)**: emergent multi-agent behaviors (negotiation, consensus)
- **OfficeBench**: office automation at single-, cross-, and multi-application complexity
- **BrowseComp+**: web browsing capabilities

Modern evaluation increasingly reports compute budgets, run-to-run variance, and failure severity distributions.

### Goal-Directed Agent Benchmarks

A distinct benchmark class evaluates complex, multi-step work episodes requiring agents to produce verifiable artifacts (spreadsheets, documents, figures, PDFs). **GDPVal** exemplifies this as a large-scale benchmark for economically valuable tasks requiring multi-step reasoning and diverse tool use.

Evaluation combines **deterministic code checks** (schema validation, bounds tests, consistency) with **model-based judges** (vision-language models scoring rendered artifacts). This hybrid balances objectivity and coverage.

**Test-time scaling** via best-of-N sampling yields monotonic improvement, with consistent gains per doubling of candidates. Scaling behavior is similar whether scored by learned evaluators or oracles, suggesting well-designed proxy evaluators can substitute for expensive oracle feedback at runtime.

### Stability

In stochastic LLM agents, simple success rates mask reliability issues. Rigorous evaluation requires failure severity distributions—distinguishing benign timeouts from catastrophic data leaks. Pass^k metrics peaking around 6% on complex workflows show that single-trial success rates dramatically overestimate deployment consistency. Hierarchical multi-agent systems amplify this concern: failures can propagate through agent hierarchies, and feedback-driven replanning loops between manager and expert agents introduce additional variance. Benchmarks must report standard deviation and worst-case scenarios.

### Security

Agents with tool access, file system permissions, or network capabilities introduce attack surfaces absent in text generation. Evaluation must assess PII protection, constraint adherence, rule compliance, and adversarial prompt injection resistance. Multi-dimensional criteria spanning correctness, reasoning quality, and safety compliance are essential.

### Toward Production-Grade Evaluation

Enterprise benchmarks lack multimodal coverage, likely underestimating context inflation and tool interaction challenges—a gap goal-directed benchmarks like GDPVal begin to address. Most academic evaluations neglect latency and cost. Bridging this gap requires benchmarks that jointly optimize across all CLASSic dimensions, employ hybrid deterministic/model-based evaluation, report distributional rather than point estimates, and ground evaluation in realistic operational conditions. Advanced hierarchical architectures—including DAG-based "agent-as-a-tool" designs and workflow orchestration via directed conditional graphs—demand evaluation methods that capture emergent coordination costs and failure propagation across agent layers.

## See Also

- [[z20260318-027|Benchmarking and Evaluation of LLM-Based Agent Systems]] — foundational benchmarking methodology that production evaluation extends
- [[z20260318-024|Multi-Agent Systems with Large Language Models]] — multi-agent architectures whose cost-latency-accuracy trade-offs production evaluation must capture
- [[z20260318-001|Multi-Agent Architectures for Workflow Automation]] — enterprise workflow complexity motivating stability and security dimensions
- [[z20260318-053|Non-Determinism, Failure Modes, and Reliability Challenges in Agentic AI]] — non-determinism and failure propagation that stability evaluation must detect
- [[z20260318-054|Multi-Pillar Behavioral Testing of Agentic AI Systems]] — fine-grained behavioral testing complementing deployment-level evaluation

