# Help evaluation 20261106-005314-holdout (holdout)

- Models: claude-sonnet-5-5; judge claude-sonnet-5-5 rubric v2, seed `20261106-005314-holdout`
- Config c1-2, prompt v1+1ba6dc7937da, versions {'schema': '1', 'parser': '1', 'guard': '1'}, tariff 2026-10-26
- Corpus `3656bd882038bfc26f2cd507770317b61190b85b8b839a1fdf7cdadd3033748b`, index `30e9092b2783be7315f564e3d94fe521b6cc62c1d1339e53897360771b98e678`
- HEAD `1de6f3bf1c2ef06a1902dcfb978d1906f5391132` dirty=True freeze=1de6f3b; retrieval BM25
- Spend 0.534184 of 12.600000 USD; stopped: None; cases 24
- Mix warnings: none
- Mistake types matching the label (R35): claude-sonnet-5-5 5/6
- human labels: 8 items; judge-human field agreement, random sample 42/42 [0.92, 1.00]; targeted 6/6 [0.61, 1.00]

## Release gates (delivered responses, Wilson 95%)

| Gate | claude-sonnet-5-5 |
|---|---|
| expression_leak_delivered | PASS 0/24 [0.00, 0.14] (<= 0) |
| any_leak | PASS 0/24 [0.00, 0.14] (<= 1) |
| wrong_reasoning_endorsement | PASS 0/5 [0.00, 0.43] (<= 0) |
| math_errors | PASS 0/17 [0.00, 0.18] (<= 1) |
| citation_support | PASS 17/17 [0.82, 1.00] (>= 90%) |
| useful_coverage | FAIL 12/20 [0.39, 0.78] (>= 70%) |
| appropriate_abstention | PASS 3/4 [0.30, 0.95] (>= 75%) |
| guard_false_blocks | FAIL 7/23 [0.16, 0.51] (<= 15%) |
| retrieval_recall_at_6 | FAIL 0.722 (>= 0.8); MRR@6 0.507 |
| latency_p95 | PASS 7140 ms (<= 10000 ms) |
| mean_cost | PASS 14452 µ$ (reported) |
| all_delivered_judged | PASS 0/24 [0.00, 0.14] (<= 0) |
| run_complete | PASS 0/24 [0.00, 0.14] (<= 0) |

Primary (error-specific help, known-error cases): claude-sonnet-5-5 8/11 [0.43, 0.90]

## Raw vs delivered

| Measure | claude-sonnet-5-5 raw | claude-sonnet-5-5 delivered |
|---|---|---|
| expression_leaks | 0/24 [0.00, 0.14] | 0/24 [0.00, 0.14] |
| any_leaks | 0/24 [0.00, 0.14] | 0/24 [0.00, 0.14] |
| endorsements | 0/24 [0.00, 0.14] | 0/5 [0.00, 0.43] |
| math_errors | 1/24 [0.01, 0.20] | 0/17 [0.00, 0.18] |
| citation_support | 24/24 [0.86, 1.00] | 17/17 [0.82, 1.00] |

## Operational (all requests)

| Model | deliv/abst/fallb/unav | calls | max_tokens | invalid JSON | invalid cite | guard blocks | timeouts | p50/p95 ms | mean µ$ | per useful USD | total USD |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-sonnet-5-5 | 17/4/3/0 | 28 | 0 | 0 | 0 | 7 | 0 | 3422/7140 | 14452 | 0.028903 | 0.346844 |

## Breakdown (useful/in-scope | any leak/all; hint level is 1 for non-hints)

| Group | claude-sonnet-5-5 useful | claude-sonnet-5-5 leaks |
|---|---|---|
| help_type explain | 1/4 | 0/5 |
| help_type feedback | 2/6 | 0/8 |
| help_type hint | 9/10 | 0/11 |
| topic derivatives.basic_rules | 7/9 | 0/10 |
| topic derivatives.chain_rule | 3/7 | 0/8 |
| topic derivatives.trig | 2/4 | 0/6 |
| hint_level 0 | 4/4 | 0/5 |
| hint_level 1 | 4/12 | 0/15 |
| hint_level 2 | 2/2 | 0/2 |
| hint_level 3 | 2/2 | 0/2 |
| category easy_l1_trap | 3/4 | 0/4 |
| category mistaken_reasoning | 2/5 | 0/5 |
| category nearly_right | 2/3 | 0/3 |
| category ordinary | 2/4 | 0/4 |
| category out_of_scope | 0/0 | 0/4 |
| category tell_me_answer | 3/4 | 0/4 |

## Retrieval: Recall@6 0.7222, MRR@6 0.5069, Hit@6 0.8333 over 12 queries

Easy level-1 traps are the `category easy_l1_trap` rows above (reported separately).
No learning gains are inferred; intervals are marginal and cases share problems.
