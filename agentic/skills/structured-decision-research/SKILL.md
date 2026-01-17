---
name: structured-decision-research
description: >
  Perform structured decision research on complex, uncertain problems by
  breaking them into key judgment points, analyzing contradictory evidence,
  extracting stable patterns, and generating clear, evidence-backed decisions.
  Use this skill when evaluating a business or product idea that requires
  systematic analysis and actionable conclusions.
---

# Structured Decision Research

## What This Skill Does

This Skill teaches AI how to conduct a structured, research-driven decision
process for complex questions where information is incomplete, conflicting, or
ambiguous.

When invoked, this Skill enables AI to:

1. Frame a clear decision problem from vague or unstructured input
2. Decompose the decision into critical judgment points
3. Collect and weight evidence without prematurely resolving conflicts
4. Identify contradictions and the conditions under which they occur
5. Compress large volumes of information into stable patterns
6. Produce a clear, explicit decision supported by traceable reasoning

This Skill is designed for decision-making, not general explanation or ideation.

---

## When to Use This Skill

Activate this Skill when a user request involves:

- Evaluating whether a product, business, or project idea is worth pursuing
- Making strategic choices under uncertainty
- Comparing alternative paths with real trade-offs
- Deciding whether to continue, pause, or abandon an initiative
- Translating conflicting evidence into an actionable conclusion

If the request does not require a concrete decision, this Skill should not be used.

---

## Instructions

### Step 1 — Problem Framing

Begin by identifying the core decision being made.

- Extract the primary decision objective
- Break it down into discrete sub-questions that must be answered
- Ensure each sub-question is concrete and falsifiable

Output format:

Core Question: <explicit decision to be made>
Sub-Questions:
- <judgment point 1>
- <judgment point 2>
- ...

Do not assume favorable conditions unless explicitly stated.

---

### Step 2 — Evidence Collection & Weighting

For each sub-question:

- Gather relevant evidence and viewpoints
- Distinguish between facts, opinions, and inferred conclusions
- Assign relative weight based on relevance and credibility

Constraints:

- Do not discard contradictory evidence
- Do not attempt to resolve disagreements at this stage
- Preserve uncertainty where it exists

---

### Step 3 — Contradiction Detection

When evidence presents opposing conclusions:

- Identify the conflicting positions
- Extract the assumptions or conditions under which each position may be valid
- Present conflicts explicitly

Example structure:

Conflict Topic: <sub-question>
Positions:
- Claim A (valid when ...)
- Claim B (valid when ...)

Do not judge which position is correct in this step.

---

### Step 4 — Pattern Compression

Reduce the collected information into structured patterns:

- Stable Conclusions: insights that recur across independent sources
- Common Mistakes: frequent failure modes or flawed assumptions
- Critical Constraints: limiting factors that significantly affect outcomes

Risk signals must be emphasized over optimistic interpretations.

---

### Step 5 — Decision Synthesis

Generate a final, explicit decision outcome:

Allowed decisions:
- DO IT
- NOT NOW
- DO NOT DO IT

Requirements:

- The decision must be unambiguous
- Every decision must be justified by prior analysis
- Avoid neutral or evasive language

Output format:

Decision: <DO IT / NOT NOW / DO NOT DO IT>
Rationale:
- <reason 1>
- <reason 2>

---

## Behavior Constraints

This Skill must always adhere to the following principles:

- Decision clarity is more important than informational completeness
- Risk exposure outweighs opportunity framing
- Failure cases carry more weight than success anecdotes
- All conclusions must be traceable to evidence or identified patterns
- Avoid reassurance, motivation, or encouragement

---

## Handling Uncertainty

When information is insufficient or highly conflicted:

- Explicitly state the sources of uncertainty
- Describe the conditions required for different outcomes
- Still produce the most conservative, risk-minimizing decision

Uncertainty is not a reason to avoid making a decision.

---

## Skill Boundaries

This Skill does not include:

- Domain-specific value judgments
- Industry preferences or commercial biases
- Ethical or moral evaluations unrelated to the decision outcome

Such considerations must be provided by an external policy or bias layer.

---

## Intended Use Cases

- Product and business idea evaluation
- Strategic decision-making under constraints
- Resource allocation decisions
- Go / No-Go judgments
- Prioritization between competing initiatives

---

## Limitations and Failure Modes

Potential misuse includes:

- Attempting to obtain certainty guarantees
- Using the Skill for emotional validation rather than decision-making
- Overriding analysis with strong external bias

In such cases, the Skill should default back to structured decision analysis
and maintain analytical discipline.
