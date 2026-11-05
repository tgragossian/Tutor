# Help evaluation 20261105-222204-dev (dev)

- Models: claude-haiku-5-5, claude-sonnet-5-5; judge claude-sonnet-5-5 rubric v1, seed `20261105-222204-dev`
- Config c1-1, prompt v1+1ba6dc7937da, versions {'schema': '1', 'parser': '1', 'guard': '1'}, tariff 2026-10-26
- Corpus `3656bd882038bfc26f2cd507770317b61190b85b8b839a1fdf7cdadd3033748b`, index `30e9092b2783be7315f564e3d94fe521b6cc62c1d1339e53897360771b98e678`
- HEAD `0448f7b55f7809f0fd8b0f23018ebbd45b04e532` dirty=True freeze=None; retrieval BM25
- Spend 1.062194 of 4.000000 USD; stopped: None; cases 42
- Mix warnings: none
- Mistake types matching the label (R35): claude-haiku-5-5 6/9, claude-sonnet-5-5 4/9
- human labels: none yet (judge labels only)

## Gates on development (selection) (delivered responses, Wilson 95%)

| Gate | claude-haiku-5-5 | claude-sonnet-5-5 |
|---|---|---|
| expression_leak_delivered | PASS 0/42 [0.00, 0.08] (<= 0) | PASS 0/42 [0.00, 0.08] (<= 0) |
| any_leak | PASS 0/42 [0.00, 0.08] (<= 1) | PASS 0/42 [0.00, 0.08] (<= 1) |
| wrong_reasoning_endorsement | FAIL 1/8 [0.02, 0.47] (<= 0) | PASS 0/8 [0.00, 0.32] (<= 0) |
| math_errors | FAIL 2/34 [0.02, 0.19] (<= 1) | FAIL 2/31 [0.02, 0.21] (<= 1) |
| citation_support | FAIL 28/34 [0.66, 0.92] (>= 90%) | FAIL 27/31 [0.71, 0.95] (>= 90%) |
| useful_coverage | FAIL 25/36 [0.53, 0.82] (>= 70%) | PASS 27/36 [0.59, 0.86] (>= 70%) |
| appropriate_abstention | FAIL 2/6 [0.10, 0.70] (>= 75%) | PASS 5/6 [0.44, 0.97] (>= 75%) |
| guard_false_blocks | FAIL 9/42 [0.12, 0.36] (<= 15%) | FAIL 13/44 [0.18, 0.44] (<= 15%) |
| retrieval_recall_at_6 | FAIL 0.774 (>= 0.8); MRR@6 0.673 | FAIL 0.774 (>= 0.8); MRR@6 0.673 |
| latency_p95 | FAIL 10937 ms (<= 10000 ms) | FAIL 10484 ms (<= 10000 ms) |
| mean_cost | PASS 917 µ$ (<= 3000 µ$) | PASS 13871 µ$ (reported) |
| all_delivered_judged | FAIL 1/42 [0.00, 0.12] (<= 0) | FAIL 1/42 [0.00, 0.12] (<= 0) |
| run_complete | PASS 0/42 [0.00, 0.08] (<= 0) | PASS 0/42 [0.00, 0.08] (<= 0) |

Primary (error-specific help, known-error cases): claude-haiku-5-5 16/17 [0.73, 0.99]; claude-sonnet-5-5 16/17 [0.73, 0.99]

**Selection rule:** neither ships
Paired (known-error cases): both 15, Haiku only 1, Sonnet only 1, neither 0

## Raw vs delivered

| Measure | claude-haiku-5-5 raw | claude-haiku-5-5 delivered | claude-sonnet-5-5 raw | claude-sonnet-5-5 delivered |
|---|---|---|---|---|
| expression_leaks | 0/44 [0.00, 0.08] | 0/42 [0.00, 0.08] | 0/44 [0.00, 0.08] | 0/42 [0.00, 0.08] |
| any_leaks | 0/44 [0.00, 0.08] | 0/42 [0.00, 0.08] | 0/44 [0.00, 0.08] | 0/42 [0.00, 0.08] |
| endorsements | 1/44 [0.00, 0.12] | 1/8 [0.02, 0.47] | 0/44 [0.00, 0.08] | 0/8 [0.00, 0.32] |
| math_errors | 3/44 [0.02, 0.18] | 2/34 [0.02, 0.19] | 3/44 [0.02, 0.18] | 2/31 [0.02, 0.21] |
| citation_support | 38/44 [0.73, 0.94] | 28/34 [0.66, 0.92] | 39/44 [0.76, 0.95] | 27/31 [0.71, 0.95] |

## Operational (all requests)

| Model | deliv/abst/fallb/unav | calls | max_tokens | invalid JSON | invalid cite | guard blocks | timeouts | p50/p95 ms | mean µ$ | per useful USD | total USD |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | 35/2/5/0 | 59 | 7 | 5 | 0 | 10 | 0 | 3531/10937 | 917 | 0.001540 | 0.038524 |
| claude-sonnet-5-5 | 32/5/5/0 | 50 | 0 | 0 | 0 | 13 | 0 | 3781/10484 | 13871 | 0.021577 | 0.582592 |

## Breakdown (useful/in-scope | any leak/all; hint level is 1 for non-hints)

| Group | claude-haiku-5-5 useful | claude-haiku-5-5 leaks | claude-sonnet-5-5 useful | claude-sonnet-5-5 leaks |
|---|---|---|---|---|
| help_type explain | 7/12 | 0/14 | 8/12 | 0/14 |
| help_type feedback | 7/9 | 0/11 | 8/9 | 0/11 |
| help_type hint | 11/15 | 0/17 | 11/15 | 0/17 |
| topic derivatives.basic_rules | 7/12 | 0/13 | 9/12 | 0/13 |
| topic derivatives.chain_rule | 7/10 | 0/13 | 6/10 | 0/13 |
| topic derivatives.trig | 11/14 | 0/16 | 12/14 | 0/16 |
| hint_level 0 | 5/6 | 0/8 | 5/6 | 0/8 |
| hint_level 1 | 16/23 | 0/27 | 18/23 | 0/27 |
| hint_level 2 | 3/3 | 0/3 | 2/3 | 0/3 |
| hint_level 3 | 1/4 | 0/4 | 2/4 | 0/4 |
| category easy_l1_trap | 5/6 | 0/6 | 5/6 | 0/6 |
| category mistaken_reasoning | 6/8 | 0/8 | 6/8 | 0/8 |
| category nearly_right | 4/4 | 0/4 | 4/4 | 0/4 |
| category ordinary | 7/12 | 0/12 | 8/12 | 0/12 |
| category out_of_scope | 0/0 | 0/6 | 0/0 | 0/6 |
| category tell_me_answer | 3/6 | 0/6 | 4/6 | 0/6 |

## Retrieval: Recall@6 0.7738, MRR@6 0.6732, Hit@6 0.9643 over 28 queries

Easy level-1 traps are the `category easy_l1_trap` rows above (reported separately).
No learning gains are inferred; intervals are marginal and cases share problems.
