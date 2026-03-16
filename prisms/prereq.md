---
name: prereq
description: "Knowledge prerequisite scanner: given a task, identifies what you need to know BEFORE doing it. Outputs atomic questions that can be batch-queried against a knowledge base."
optimal_model: sonnet
domain: any
type: knowledge
---
Execute every step. Output the complete analysis.

You receive a TASK the user wants to accomplish. Your job: identify every piece of knowledge they need BEFORE starting.

## DOMAINS
What knowledge domains does this task touch? Name each (e.g., "Python asyncio", "PostgreSQL configuration", "HTTP protocol", "React state management"). Be specific — not "databases" but "PostgreSQL replication" or "Redis pub/sub."

## PREREQUISITES
For each domain, list the specific facts, concepts, or procedures the user must understand to do this task well. Group by domain. Be concrete — not "understand async" but "know that asyncio.Lock is reentrant-unsafe."

## ATOMIC QUESTIONS
Convert every prerequisite into a standalone question that could be answered by a knowledge base. Requirements:
- Each question must be self-contained (no "it" or "this" — name the thing)
- Each question should have ONE factual answer
- Include the technology name in every question
- Order from most fundamental to most specific
- Tag each question with its TYPE for knowledge base routing:
  [FACT] = atomic lookup ("What is the default port?")
  [REFERENCE] = API/syntax docs ("What parameters does X accept?")
  [TROUBLESHOOTING] = error diagnosis ("What causes X error?")
  [METHODOLOGY] = step-by-step ("How do you implement X?")
  [EXPLANATION] = how it works ("How does X handle Y?")
  [DECISION] = comparison ("X vs Y for Z?")

Also tag each question by ANSWERABILITY TIER:
  T1 = well-documented fact, verifiable from official docs
  T2 = requires composing multiple sources or version-specific context
  T3 = requires runtime context, configuration, or domain expertise — structurally unanswerable from docs alone

Output as a numbered list. Target: 10-30 questions covering all domains.

## CONFABULATION RISK MAP
T3 questions are where models confabulate most. For each T3 question:
- Name what the model would GUESS
- Name why that guess is likely WRONG
- Name what would actually be needed to answer correctly

## CRITICAL GAPS
Which of these questions, if answered wrong, would cause the task to FAIL? Mark the top 3-5 as CRITICAL.

## CONFIDENCE MAP
For each question, estimate: would a general-purpose LLM answer this correctly?
- HIGH: common knowledge, unlikely to confabulate (e.g., "What port does PostgreSQL use?")
- MEDIUM: needs specific version/context, may confabulate details
- LOW: obscure, version-specific, or commonly confused — MUST verify externally

Focus on LOW confidence items. Those are the gaps that matter.
