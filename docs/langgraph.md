# LangGraph workflow

> _To be filled out in Phase 3 (state + base graph) and expanded as agents are added._

The research task is a directed graph rather than a linear pipeline. Nodes each
operate on a typed `ResearchState`, and a **research critic** decides whether the
evidence base is sufficient:

```
START
  → analyze_query
  → create_research_plan
  → search_web
  → analyze_sources
  → fact_check
  → evaluate_research   (conditional)
       → insufficient → search_more → evaluate_research
       → sufficient  → write_report → review_report
                                        → problems? → rewrite (bounded)
                                        → ok        → finalize
  → END
```

Key properties:

- **Typed state** — `ResearchState` (TypedDict) carries question, plans, sources,
  claims, fact checks, gaps, report drafts, citations, errors.
- **Conditional edges** — critic result routes to more research or report writing.
- **Iteration bound** — `MAX_RESEARCH_ITERATIONS` prevents infinite loops.
- **Checkpointing** — conversations resume via `thread_id` (Phase 13).
- **Error recovery** — node failures are captured in state and handled gracefully.