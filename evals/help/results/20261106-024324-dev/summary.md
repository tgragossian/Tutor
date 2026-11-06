# Help evaluation 20261106-024324-dev (dev)

- Models: claude-sonnet-5-5; judge claude-sonnet-5-5 rubric v2, seed `20261106-024324-dev`
- Config c1-3, prompt v1+da2eb7555541, versions {'schema': '1', 'parser': '1', 'guard': '1'}, tariff 2026-10-26
- Corpus `3656bd882038bfc26f2cd507770317b61190b85b8b839a1fdf7cdadd3033748b`, index `30e9092b2783be7315f564e3d94fe521b6cc62c1d1339e53897360771b98e678`
- HEAD `14a9d50b9a40c7d4d4000c119aa5ed3a76ec53a0` dirty=True freeze=None; retrieval BM25
- Spend 0.903354 of 3.000000 USD; stopped: None; cases 42
- Mix warnings: none
- Mistake types matching the label (R35): claude-sonnet-5-5 5/8
- human labels: none yet (judge labels only)

## Gates on development (selection) (delivered responses, Wilson 95%)

| Gate | claude-sonnet-5-5 |
|---|---|
| expression_leak_delivered | PASS 0/42 [0.00, 0.08] (<= 0) |
| any_leak | PASS 0/42 [0.00, 0.08] (<= 1) |
| wrong_reasoning_endorsement | PASS 0/8 [0.00, 0.32] (<= 0) |
| math_errors | PASS 1/33 [0.01, 0.15] (<= 1) |
| citation_support | FAIL 29/33 [0.73, 0.95] (>= 90%) |
| useful_coverage | FAIL 20/36 [0.40, 0.70] (>= 70%) |
| appropriate_abstention | PASS 5/6 [0.44, 0.97] (>= 75%) |
| guard_false_blocks | FAIL 10/42 [0.13, 0.39] (<= 15%) |
| retrieval_recall_at_6 | FAIL 0.774 (>= 0.8); MRR@6 0.673 |
| latency_p95 | PASS 7844 ms (<= 10000 ms) |
| mean_cost | PASS 13292 µ$ (reported) |
| all_delivered_judged | PASS 0/42 [0.00, 0.08] (<= 0) |
| run_complete | PASS 0/42 [0.00, 0.08] (<= 0) |

Primary (error-specific help, known-error cases): claude-sonnet-5-5 15/17 [0.66, 0.97]

## Raw vs delivered

| Measure | claude-sonnet-5-5 raw | claude-sonnet-5-5 delivered |
|---|---|---|
| expression_leaks | 0/43 [0.00, 0.08] | 0/42 [0.00, 0.08] |
| any_leaks | 0/43 [0.00, 0.08] | 0/42 [0.00, 0.08] |
| endorsements | 0/43 [0.00, 0.08] | 0/8 [0.00, 0.32] |
| math_errors | 1/43 [0.00, 0.12] | 1/33 [0.01, 0.15] |
| citation_support | 39/43 [0.78, 0.96] | 29/33 [0.73, 0.95] |

## Operational (all requests)

| Model | deliv/abst/fallb/unav | calls | max_tokens | invalid JSON | invalid cite | guard blocks | timeouts | p50/p95 ms | mean µ$ | per useful USD | total USD |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-sonnet-5-5 | 33/5/4/0 | 48 | 0 | 0 | 0 | 10 | 0 | 3797/7844 | 13292 | 0.027913 | 0.558268 |

## Breakdown (useful/in-scope | any leak/all; hint level is 1 for non-hints)

| Group | claude-sonnet-5-5 useful | claude-sonnet-5-5 leaks |
|---|---|---|
| help_type explain | 1/12 | 0/14 |
| help_type feedback | 8/9 | 0/11 |
| help_type hint | 11/15 | 0/17 |
| topic derivatives.basic_rules | 7/12 | 0/13 |
| topic derivatives.chain_rule | 6/10 | 0/13 |
| topic derivatives.trig | 7/14 | 0/16 |
| hint_level 0 | 6/6 | 0/8 |
| hint_level 1 | 11/23 | 0/27 |
| hint_level 2 | 2/3 | 0/3 |
| hint_level 3 | 1/4 | 0/4 |
| category easy_l1_trap | 6/6 | 0/6 |
| category mistaken_reasoning | 6/8 | 0/8 |
| category nearly_right | 4/4 | 0/4 |
| category ordinary | 2/12 | 0/12 |
| category out_of_scope | 0/0 | 0/6 |
| category tell_me_answer | 2/6 | 0/6 |

## Retrieval: Recall@6 0.7738, MRR@6 0.6732, Hit@6 0.9643 over 28 queries

Easy level-1 traps are the `category easy_l1_trap` rows above (reported separately).
No learning gains are inferred; intervals are marginal and cases share problems.
