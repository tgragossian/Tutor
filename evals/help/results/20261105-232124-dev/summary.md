# Help evaluation 20261105-232124-dev (dev)

- Models: claude-haiku-5-5, claude-sonnet-5-5; judge claude-sonnet-5-5 rubric v1, seed `20261105-232124-dev`
- Config c1-2, prompt v1+1ba6dc7937da, versions {'schema': '1', 'parser': '1', 'guard': '1'}, tariff 2026-10-26
- Corpus `3656bd882038bfc26f2cd507770317b61190b85b8b839a1fdf7cdadd3033748b`, index `30e9092b2783be7315f564e3d94fe521b6cc62c1d1339e53897360771b98e678`
- HEAD `3bb2b9c966c57401236587586222c4eddec58f94` dirty=True freeze=None; retrieval BM25
- Spend 1.026552 of 4.000000 USD; stopped: None; cases 42
- Mix warnings: none
- Mistake types matching the label (R35): claude-haiku-5-5 5/9, claude-sonnet-5-5 5/9
- human labels: 29 items; judge-human field agreement, random sample 136/138 [0.95, 1.00]; targeted 30/36 [0.68, 0.92]

## Gates on development (selection) (delivered responses, Wilson 95%)

| Gate | claude-haiku-5-5 | claude-sonnet-5-5 |
|---|---|---|
| expression_leak_delivered | PASS 0/42 [0.00, 0.08] (<= 0) | PASS 0/42 [0.00, 0.08] (<= 0) |
| any_leak | PASS 0/42 [0.00, 0.08] (<= 1) | PASS 0/42 [0.00, 0.08] (<= 1) |
| wrong_reasoning_endorsement | FAIL 1/8 [0.02, 0.47] (<= 0) | FAIL 1/8 [0.02, 0.47] (<= 0) |
| math_errors | FAIL 2/34 [0.02, 0.19] (<= 1) | PASS 1/34 [0.01, 0.15] (<= 1) |
| citation_support | FAIL 26/34 [0.60, 0.88] (>= 90%) | FAIL 28/34 [0.66, 0.92] (>= 90%) |
| useful_coverage | FAIL 25/36 [0.53, 0.82] (>= 70%) | PASS 31/36 [0.71, 0.94] (>= 70%) |
| appropriate_abstention | FAIL 2/6 [0.10, 0.70] (>= 75%) | PASS 5/6 [0.44, 0.97] (>= 75%) |
| guard_false_blocks | FAIL 10/44 [0.13, 0.37] (<= 15%) | FAIL 7/41 [0.09, 0.31] (<= 15%) |
| retrieval_recall_at_6 | FAIL 0.774 (>= 0.8); MRR@6 0.673 | FAIL 0.774 (>= 0.8); MRR@6 0.673 |
| latency_p95 | PASS 7016 ms (<= 10000 ms) | PASS 7750 ms (<= 10000 ms) |
| mean_cost | PASS 809 µ$ (<= 3000 µ$) | PASS 12973 µ$ (reported) |
| all_delivered_judged | FAIL 1/42 [0.00, 0.12] (<= 0) | FAIL 1/42 [0.00, 0.12] (<= 0) |
| run_complete | PASS 0/42 [0.00, 0.08] (<= 0) | PASS 0/42 [0.00, 0.08] (<= 0) |

Primary (error-specific help, known-error cases): claude-haiku-5-5 14/17 [0.59, 0.94]; claude-sonnet-5-5 15/17 [0.66, 0.97]

**Selection rule:** neither ships
Paired (known-error cases): both 13, Haiku only 1, Sonnet only 2, neither 1

## Raw vs delivered

| Measure | claude-haiku-5-5 raw | claude-haiku-5-5 delivered | claude-sonnet-5-5 raw | claude-sonnet-5-5 delivered |
|---|---|---|---|---|
| expression_leaks | 0/46 [0.00, 0.08] | 0/42 [0.00, 0.08] | 0/41 [0.00, 0.09] | 0/42 [0.00, 0.08] |
| any_leaks | 0/46 [0.00, 0.08] | 0/42 [0.00, 0.08] | 0/41 [0.00, 0.09] | 0/42 [0.00, 0.08] |
| endorsements | 1/46 [0.00, 0.11] | 1/8 [0.02, 0.47] | 1/41 [0.00, 0.13] | 1/8 [0.02, 0.47] |
| math_errors | 5/46 [0.05, 0.23] | 2/34 [0.02, 0.19] | 1/41 [0.00, 0.13] | 1/34 [0.01, 0.15] |
| citation_support | 37/46 [0.67, 0.89] | 26/34 [0.60, 0.88] | 34/41 [0.69, 0.91] | 28/34 [0.66, 0.92] |

## Operational (all requests)

| Model | deliv/abst/fallb/unav | calls | max_tokens | invalid JSON | invalid cite | guard blocks | timeouts | p50/p95 ms | mean µ$ | per useful USD | total USD |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | 35/2/5/0 | 53 | 0 | 4 | 0 | 12 | 0 | 3625/7016 | 809 | 0.001359 | 0.033996 |
| claude-sonnet-5-5 | 35/5/2/0 | 47 | 0 | 0 | 0 | 7 | 0 | 3813/7750 | 12973 | 0.017576 | 0.544870 |

## Breakdown (useful/in-scope | any leak/all; hint level is 1 for non-hints)

| Group | claude-haiku-5-5 useful | claude-haiku-5-5 leaks | claude-sonnet-5-5 useful | claude-sonnet-5-5 leaks |
|---|---|---|---|---|
| help_type explain | 8/12 | 0/14 | 9/12 | 0/14 |
| help_type feedback | 5/9 | 0/11 | 8/9 | 0/11 |
| help_type hint | 12/15 | 0/17 | 14/15 | 0/17 |
| topic derivatives.basic_rules | 6/12 | 0/13 | 10/12 | 0/13 |
| topic derivatives.chain_rule | 9/10 | 0/13 | 9/10 | 0/13 |
| topic derivatives.trig | 10/14 | 0/16 | 12/14 | 0/16 |
| hint_level 0 | 6/6 | 0/8 | 6/6 | 0/8 |
| hint_level 1 | 15/23 | 0/27 | 19/23 | 0/27 |
| hint_level 2 | 2/3 | 0/3 | 2/3 | 0/3 |
| hint_level 3 | 2/4 | 0/4 | 4/4 | 0/4 |
| category easy_l1_trap | 6/6 | 0/6 | 6/6 | 0/6 |
| category mistaken_reasoning | 4/8 | 0/8 | 7/8 | 0/8 |
| category nearly_right | 3/4 | 0/4 | 3/4 | 0/4 |
| category ordinary | 8/12 | 0/12 | 9/12 | 0/12 |
| category out_of_scope | 0/0 | 0/6 | 0/0 | 0/6 |
| category tell_me_answer | 4/6 | 0/6 | 6/6 | 0/6 |

## Retrieval: Recall@6 0.7738, MRR@6 0.6732, Hit@6 0.9643 over 28 queries

Easy level-1 traps are the `category easy_l1_trap` rows above (reported separately).
No learning gains are inferred; intervals are marginal and cases share problems.
