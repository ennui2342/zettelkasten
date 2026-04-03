---
id: z20260314-001
type: topic
confidence: 0.78
salience: 0.7
stable: false
context: >
  Core principle in memory science and learning system design. Directly
  relevant to any system that schedules reviews or surfaces past material.
tags: [memory, learning, spaced-repetition, retention]
sources:
  - ebbinghaus-1885
  - cepeda-et-al-2006
created: 2026-03-14T09:00:00Z
updated: 2026-03-14T09:00:00Z
---

Spaced repetition is the practice of distributing study or review sessions over time rather than concentrating them in a single session. Ebbinghaus's forgetting curve shows that memory strength decays exponentially after encoding; each successful retrieval resets the curve with a shallower slope. The practical implication is that reviews timed to arrive just before the memory would be lost require fewer total review sessions to achieve a given retention target than reviews at fixed short intervals.

The phenomenon is sometimes called the spacing effect or distributed practice effect. The contrast is with massed practice — studying the same material repeatedly in a single session — which produces strong short-term performance but weak long-term retention, because the material remains accessible in working memory throughout and genuine retrieval is rarely required.

Implementations such as Anki and SuperMemo formalise the scheduling by estimating the decay rate for each item and computing the optimal next review date. The SM-2 algorithm (SuperMemo 2) uses performance on each review to adjust the inter-repetition interval.

**Open question:** whether spacing interval alone explains the retention benefit, or whether the qualitative difficulty of retrieval after a longer gap is itself a contributing factor.
