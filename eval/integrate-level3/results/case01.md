# Case 1: Regression: focused single-topic note + same-topic draft → EDIT

**Draft:** Calibrating Rubric Weights Through Contrastive Human Feedback

---

## Original (8,705 chars)

## Rubric-Based Evaluation of AI Systems

Rubrics—structured sets of weighted, verifiable criteria expressed in natural language—have emerged as a paradigm for evaluating and improving the alignment of AI systems with human preferences. Rather than relying on a single opaque reward signal, rubric-based approaches decompose evaluation into interpretable dimensions, enabling transparent assessment of complex outputs.

**Rubric Structure and Design.** A rubric consists of a finite set of criteria, each described in natural language and assigned a relative importance weight. Criteria are designed to be specific (targeting observable properties rather than vague qualities), verifiable (checkable via code or model-based judges), independent (minimizing redundancy), and capable of partial credit where appropriate. A common organizational pattern decomposes rubrics into stages: a gate stage checking basic structure and task compliance, a verification stage validating factual or logical correctness, and a quality stage assessing higher-level attributes such as clarity, completeness, and usefulness.

**Verification Mechanisms.** Each rubric criterion is paired with a verifier that estimates how well an output satisfies the criterion. Verifiers fall into two categories: rule-based (deterministic checks such as file format validation, schema compliance, or arithmetic verification implemented as Python functions) and model-based (lightweight LLM or classifier evaluators for semantic properties such as factuality, coherence, tone, or argument quality). Hybrid evaluation combining both types enables reproducible low-level validation while reserving model-based judges for higher-level reasoning. To minimize verifier error, best practices include using verifier models from different model families than the systems being evaluated (avoiding self-enforcement bias) and designing criteria that exploit the asymmetry of verification—where checking a property is easier than generating a correct output.

**Rubric-Based Reward Functions.** The overall proxy utility induced by a rubric is computed as a weighted linear combination of individual criterion scores. This formulation turns abstract alignment objectives into concrete, interpretable scoring functions. Rubric-based reinforcement fine-tuning—using rubric scores as reward signals during training—has been shown to improve robustness and alignment stability compared to opaque scalar rewards. The composite reward functions used in communication policy optimization—combining task performance, communication cost, and intrinsic shaping rewards—are already rudimentary multi-dimensional rubrics; making them explicit and stakeholder-configurable transforms fixed hyperparameters into adjustable preference dimensions.

**Synthetic Rubric Generation.** Large-scale frameworks demonstrate that rubrics can be synthetically generated, enabling scalable, domain-specific supervision without extensive human labeling. Rubric generation can itself be framed as a learning problem: a model learns to map task descriptions and stakeholder preferences into structured rubrics whose induced scores correlate with true stakeholder evaluations. This approach allows rubrics to be generated on-the-fly from task context rather than being statically defined per domain.

**Evaluation Metrics for Rubric Quality.** Rubric quality can be assessed along multiple dimensions: usefulness (whether rubric-guided outputs achieve higher stakeholder utility than unguided ones), faithfulness (whether rubric-induced rankings agree with oracle rankings, measured by metrics such as NDCG), and interpretability (whether rubrics are compact, legible, and auditable, measured by criteria count, tokens per criterion, and weight distribution balance). Empirical findings indicate that learned rubrics can approach oracle-level ranking performance while remaining concise—typically around 12 criteria per rubric with 17–18 tokens per criterion description.

**Domain Sensitivity.** Rubric-based evaluation shows differential effectiveness across domains. Improvements tend to be strongest for subjective, language-heavy domains such as content creation and legal compliance, where quality is multi-dimensional and hard to specify a priori. Operational and data-analysis tasks, where correctness is more objectively defined, show smaller or flat improvements. This suggests that rubric-based approaches are most valuable when quality is inherently subjective and decomposable into multiple nuanced dimensions.

**Rubrics as Topology-Aware Evaluation.** When applied not just to final outputs but to inter-agent communications, rubrics become topology-aware reward functions capable of evaluating whether particular communication edges in a multi-agent graph produce exchanges satisfying stakeholder-specified quality dimensions. A rubric criterion for "reasoning transparency" can penalize edges where agents share conclusions without supporting logic; a criterion for "epistemic humility" can reward interactions where agents appropriately signal uncertainty. This reframing transforms topology optimization from a purely performance-driven search into a preference-aligned design process, where the optimization target becomes whether interaction patterns satisfy a multi-dimensional preference specification rather than merely whether interacting agents produce correct answers.

**Multi-Dimensional Phase Structure.** When rubric dimensions are applied to multi-agent aggregation, each preference dimension induces its own effective scaling parameters, meaning a single topology cannot be characterized by a single organization exponent. A topology may achieve supercritical amplification for factual accuracy while being deeply subcritical for reasoning transparency or safety adherence. This dimension-dependence creates a dangerous regime where scaling out improves task metrics while degrading alignment on dimensions that carry lower weight in aggregate evaluation—a form of alignment debt invisible to outcome-only assessment. Rubrics provide the decomposition needed to detect and prevent such failures by serving as sufficient statistics for the preference structure that determines whether a given topology is alignment-preserving.

**Connection to Behavioral Testing.** The four-pillar decomposition used in behavioral testing of agentic systems—LLM, Memory, Tools, Environment—maps naturally onto rubric dimensions applicable to topology evaluation. Memory recall metrics reveal whether agents consult relevant information during interactions; tool orchestration metrics reveal whether communication edges trigger appropriate verification sequences. The documented finding that agents can achieve perfect task completion while exhibiting only 33% policy adherence illustrates precisely the failure mode that rubric-based evaluation is designed to catch: high scores on outcome dimensions masking severe deficiencies on process dimensions.

## See Also

- [[z20260318-057|Alignment as Topology-Aware Reward: Bridging Preference Optimization and Multi-Agent Communication Structure]] — elaborates the framework for applying rubric-based evaluation to inter-agent communications and topology optimization as a preference-aligned design process
- [[z20260318-058|Alignment-Aware Aggregation: How Preference Structure Constrains the Effective Organization Exponent]] — extends rubric-based evaluation into multi-agent scaling theory by decomposing the organization exponent across preference dimensions and identifying the multi-dimensional phase structure
- [[z20260318-026|Reinforcement Learning Policy Optimization for Language Models and Communication Agents]] — grounds the composite reward functions that rubric-based evaluation formalizes and makes stakeholder-configurable, including task performance, communication cost, and intrinsic shaping components
- [[z20260318-054|Multi-Pillar Behavioral Testing of Agentic AI Systems]] — applies the pillar-specific metrics and layered evaluation methodology that rubric-based assessment generalizes into interpretable, weighted preference dimensions
- [[z20260318-035|Multi-Agent Systems for LLM-Based Reasoning]] — exemplifies the verbal reinforcement learning and debate mechanisms whose fixed evaluation criteria (correctness and coherence) rubric-based approaches replace with structured, multi-dimensional preference specifications
- [[z20260318-056|Uncertainty as the Unifying Substrate of Behavioral Evaluation and Security Assessment in Agentic Systems]] — contrasts the unified uncertainty attribution framework with rubric-based decomposition as complementary approaches to diagnosing failures across behavioral and alignment dimensions

---

## Current _STEP2_EDIT (5,468 chars, 63% of original)

## Rubric-Based Evaluation of AI Systems

Rubrics—structured sets of weighted, verifiable criteria in natural language—decompose AI evaluation into interpretable dimensions rather than relying on a single opaque reward signal.

**Structure and Design.** A rubric comprises criteria that are specific (targeting observable properties), verifiable (checkable via code or model-based judges), independent, and capable of partial credit. A common pattern uses staged organization: a gate stage for structure/compliance, a verification stage for correctness, and a quality stage for clarity, completeness, and usefulness.

**Verification.** Each criterion pairs with a verifier: rule-based (deterministic checks like schema compliance or arithmetic) or model-based (LLM/classifier evaluators for semantic properties like factuality or coherence). Best practices include using verifier models from different families than the evaluated system and designing criteria that exploit the verification–generation asymmetry.

**Rubric-Based Reward and Training.** Overall scores are computed as weighted linear combinations of criterion scores, turning alignment objectives into interpretable scoring functions. Using these as reward signals during reinforcement fine-tuning improves robustness over opaque scalar rewards. Composite reward functions already used in communication policy optimization—combining task performance, communication cost, and shaping rewards—are rudimentary multi-dimensional rubrics; making them explicit and stakeholder-configurable transforms fixed hyperparameters into adjustable preference dimensions.

**Weight Calibration.** When criteria conflict—maximal conciseness may sacrifice completeness—relative weights determine which trade-off is rewarded. Contrastive human feedback, where evaluators compare output pairs with similar criterion profiles but different weight distributions, provides calibration signals that simple agreement scoring cannot. Bayesian weight inference from pairwise comparisons converges on human preference orderings with significantly fewer annotations than criterion-level rating.

**Synthetic Generation.** Rubrics can be synthetically generated at scale: a model maps task descriptions and stakeholder preferences into structured rubrics whose induced scores correlate with true evaluations, enabling on-the-fly, domain-specific supervision without extensive human labeling.

**Quality Metrics.** Rubric quality is assessed via usefulness (whether guided outputs achieve higher utility), faithfulness (agreement with oracle rankings, e.g., NDCG), and interpretability (compactness, legibility, auditability). Learned rubrics approach oracle-level ranking while remaining concise—typically ~12 criteria at 17–18 tokens each.

**Domain Sensitivity.** Improvements are strongest for subjective, language-heavy domains (content creation, legal compliance) where quality is multi-dimensional. Operational and data-analysis tasks with objectively defined correctness show smaller gains.

**Topology-Aware Evaluation.** Applied to inter-agent communications, rubrics become topology-aware reward functions evaluating whether communication edges satisfy stakeholder-specified quality dimensions. A "reasoning transparency" criterion penalizes sharing conclusions without supporting logic; an "epistemic humility" criterion rewards appropriate uncertainty signaling. This transforms topology optimization from performance-driven search into preference-aligned design.

**Multi-Dimensional Phase Structure.** Each rubric dimension induces its own effective scaling parameters in multi-agent aggregation, so a single topology cannot be characterized by one organization exponent. A topology may achieve supercritical amplification for accuracy while being subcritical for transparency or safety—a form of alignment debt invisible to outcome-only assessment. Rubrics provide the decomposition needed to detect this failure mode.

**Connection to Behavioral Testing.** The four-pillar decomposition (LLM, Memory, Tools, Environment) maps onto rubric dimensions for topology evaluation. The documented finding that agents achieve perfect task completion with only 33% policy adherence illustrates precisely what rubric-based evaluation catches: high outcome scores masking severe process deficiencies.

## See Also

- [[z20260318-057|Alignment as Topology-Aware Reward]] — framework for applying rubric-based evaluation to inter-agent communications and topology optimization as preference-aligned design
- [[z20260318-058|Alignment-Aware Aggregation]] — extends rubric evaluation into multi-agent scaling theory, decomposing the organization exponent across preference dimensions
- [[z20260318-026|Reinforcement Learning Policy Optimization for Language Models and Communication Agents]] — grounds the composite reward functions that rubric-based evaluation formalizes
- [[z20260318-054|Multi-Pillar Behavioral Testing of Agentic AI Systems]] — pillar-specific metrics that rubric-based assessment generalizes into weighted preference dimensions
- [[z20260318-035|Multi-Agent Systems for LLM-Based Reasoning]] — verbal reinforcement learning and debate mechanisms whose fixed criteria rubric approaches replace with multi-dimensional specifications
- [[z20260318-056|Uncertainty as the Unifying Substrate of Behavioral Evaluation and Security Assessment]] — complementary uncertainty attribution framework for diagnosing failures across behavioral and alignment dimensions

---

## Candidate step2_edit.txt (5,312 chars, 61% of original)

## Rubric-Based Evaluation of AI Systems

Rubrics—structured sets of weighted, verifiable criteria in natural language—decompose AI evaluation into interpretable dimensions rather than relying on a single opaque reward signal.

**Structure and Design.** A rubric comprises criteria that are specific (targeting observable properties), verifiable (checkable via code or model-based judges), independent, and capable of partial credit. A common pattern uses stages: a gate stage for structure/compliance, a verification stage for correctness, and a quality stage for clarity, completeness, and usefulness.

**Verification.** Each criterion pairs with a verifier: rule-based (deterministic checks like schema compliance or arithmetic) or model-based (LLM/classifier evaluators for semantic properties like factuality or coherence). Best practices include using verifier models from different families than the evaluated system (avoiding self-enforcement bias) and exploiting the verification-generation asymmetry—checking is easier than producing correct output.

**Rubric-Based Reward and Weight Calibration.** Overall scores are weighted linear combinations of criterion scores, turning abstract alignment objectives into interpretable scoring functions. Rubric-based reinforcement fine-tuning improves robustness over opaque scalar rewards. Critically, when criteria conflict—maximal conciseness may sacrifice completeness—relative weights determine which trade-off is rewarded. Contrastive human feedback, where evaluators compare output pairs with similar criterion profiles but different weight distributions, calibrates these weights more efficiently than criterion-level rating. Bayesian weight inference from pairwise comparisons converges on human preference orderings with significantly fewer annotations. The composite reward functions in communication policy optimization (task performance, communication cost, shaping rewards) are already rudimentary multi-dimensional rubrics; making them explicit and stakeholder-configurable transforms fixed hyperparameters into adjustable preference dimensions.

**Synthetic Generation.** Rubrics can be synthetically generated at scale: a model maps task descriptions and stakeholder preferences into structured rubrics whose induced scores correlate with true evaluations, enabling on-the-fly domain-specific supervision without extensive human labeling.

**Quality Metrics.** Rubric quality is assessed via usefulness (do rubric-guided outputs achieve higher utility?), faithfulness (do induced rankings agree with oracle rankings, e.g., by NDCG?), and interpretability (compactness, legibility, auditability). Learned rubrics approach oracle-level ranking with ~12 criteria at ~17–18 tokens each.

**Domain Sensitivity.** Improvements are strongest for subjective, language-heavy domains (content creation, legal compliance) where quality is multi-dimensional. Operational and data-analysis tasks with objectively defined correctness show smaller gains.

**Topology-Aware Evaluation.** Applied to inter-agent communications, rubrics become topology-aware reward functions evaluating whether communication edges satisfy stakeholder-specified quality dimensions. A "reasoning transparency" criterion penalizes sharing conclusions without supporting logic; an "epistemic humility" criterion rewards appropriate uncertainty signaling. This transforms topology optimization from performance-driven search into preference-aligned design.

**Multi-Dimensional Phase Structure.** Each rubric dimension induces its own effective scaling parameters, so a single topology cannot be characterized by one organization exponent. A topology may achieve supercritical amplification for accuracy while being subcritical for transparency or safety—a form of alignment debt invisible to outcome-only assessment. Rubrics provide the decomposition to detect such failures.

**Connection to Behavioral Testing.** The four-pillar decomposition (LLM, Memory, Tools, Environment) maps onto rubric dimensions for topology evaluation. The documented finding that agents achieve perfect task completion with only 33% policy adherence illustrates precisely the failure mode rubrics catch: high outcome scores masking severe process deficiencies.

## See Also

- [[z20260318-057|Alignment as Topology-Aware Reward]] — framework for rubric-based evaluation of inter-agent communications and topology optimization as preference-aligned design
- [[z20260318-058|Alignment-Aware Aggregation]] — decomposes the organization exponent across preference dimensions, identifying multi-dimensional phase structure
- [[z20260318-026|RL Policy Optimization for Language Models and Communication Agents]] — grounds the composite reward functions that rubric-based evaluation formalizes
- [[z20260318-054|Multi-Pillar Behavioral Testing of Agentic AI Systems]] — pillar-specific metrics that rubric-based assessment generalizes into weighted preference dimensions
- [[z20260318-035|Multi-Agent Systems for LLM-Based Reasoning]] — verbal RL and debate mechanisms whose fixed criteria rubrics replace with multi-dimensional specifications
- [[z20260318-056|Uncertainty as Unifying Substrate of Behavioral and Security Assessment]] — complementary uncertainty attribution framework for diagnosing failures across behavioral and alignment dimensions

