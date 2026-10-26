# 0005 supplement: sizing and cost assumptions

[Parent decision 0005](../0005-tutoring-datasets-and-fine-tuning.md)
· [Compute and serving](01-compute-and-serving.md)

Planning notes carried from the 2026-10-22 discussion and `3284327`, not measured results
or freshly verified provider quotes. Recheck specifications, rates and compatibility at the test.

## GPU sizing notes

| Recorded assumption | Planning value |
|---|---|
| Qwen3.5-9B parameters / advertised context | 9.65B (rounded 9.7B) / 262K tokens |
| bf16 weights alone | ≈19.3 GB |
| 8-bit weights alone | ≈9.7 GB |
| 4-bit weights alone | ≈5.5–6 GB |
| Attention KV estimate per token | ≈32 KB: 8 full-attention layers, 4 KV heads × 256 |
| Serving hardware assumption | Ampere or newer for the planned vLLM stack |

Weights and attention KV are not total runtime memory. Include runtime/adapter overhead,
other model state, context length and concurrency in the serving test before claiming 24 GB fits.
The advertised context is not a serving configuration or a promise that it fits on one worker.
V100 and Thomas's GTX 1070 Ti are excluded from the proposed serving setup.
Training uses AWS rather than the local 8 GB Pascal card; actual QLoRA fit must be measured too.

## RunPod monthly scenarios

Recorded calculator workload: 50 requests/day × 30 days × 5 seconds/request = 7,500 seconds.
This is also 50 students × 30 hints/month; it is not 50 hints per student per day.

| Scenario from the discussion | Approximate monthly compute |
|---|---:|
| Calculator execution only, excluding idle/cold starts | $0.92 |
| Idle tail/cold starts included; fast cached restarts mostly succeed | $2 |
| Full cold starts common | $5–8 |

These replace the older $3–5 estimate. The earlier rate note of $0.69/hour would instead
make 7,500 execution seconds ≈$1.44; the calculator's $0.92 and that rate are not consistent.
Capture the selected GPU, region, rate and billable seconds to resolve this during the test.
The discussion assumed sub-200 ms cached restarts and tens-of-seconds full weight loads;
neither latency nor cache-hit rate is established for this endpoint.
Storage, registry/network charges and hosted fallback usage need separate accounting.

## Other budgets

- C hosted-model comparison: about $5 total planned, with exact prices recorded at the run.
- AWS training: tens of dollars planned. Earlier third-party quotes were about $1.01/hour
  on demand and $0.5–0.8/hour spot in us-west-2; these are dated 2026-10-22 assumptions.
- Budget alerts do not enforce a spending cap; stop compute between runs.
- The [Lightsail sizing exception](../../ops/host-sizing.md) is separate from GPU spend.
  Re-measure web-host memory in C with the actual retrieval configuration.
