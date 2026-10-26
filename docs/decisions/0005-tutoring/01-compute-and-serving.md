# 0005 supplement: compute, serving and live A/B

[Parent decision 0005](../0005-tutoring-datasets-and-fine-tuning.md#6-timing-compute-and-serving-thomas-2026-10-22)
· [Sizing and costs](02-sizing-and-costs.md)

Accepted direction: Thomas, 2026-10-22. This is planned work after milestone C.
Imported from decision 0005 and the AI handoff in `3284327`; no endpoint has been tested here.

## Training

- Qwen3.5-9B, QLoRA, one adapter for the three help types; PyTorch/Hugging Face tooling.
- AWS `g5.xlarge` (A10G 24 GB), spot when possible; stop or terminate after each run.
- Request the EC2 GPU vCPU quota early and raise the $10/month budget alert before training.
  An alert is a notification, not a cap. Record actual resources and spend with each run.
- RunPod Pods is a proposed training alternative, not an accepted change from AWS.
- Dataset roles, contamination checks and unpublished artifacts remain governed by 0005 §§1–4.

## Serving

- RunPod Serverless: one 24 GB flex worker, vLLM, Qwen3.5-9B with and without the adapter.
  Maximum workers 1, active workers 0, short idle timeout, scale to zero.
- Candidate weight formats are 8-bit or AWQ 4-bit; compatibility and fit require the serving test.
- Both A/B arms share hardware. Keep weights/adapters in a private volume or private registry.
  Training artifacts and TutorBench rows stay out of git and the application Docker image.
- Fireworks/Together were rejected in the 2026-10-22 decision because the checked offerings
  did not provide the required per-token LoRA serving. This is a dated selection rationale.
- The Lightsail web host remains separate; it does not load the model weights.

## Live experiment and failure handling

- Each student keeps the base or LoRA arm assigned at sign-up; log the arm on every hint.
- Log the model actually used and fallback reason separately from the assigned arm, so hosted
  fallback responses are not silently counted as Qwen responses.
- Live outcomes: SymPy result of the next attempt, leak rate, reveal rate and thumbs up/down.
  At about 50 students these are descriptive only; the offline paired A/B is the headline result.
- Fallback: assigned base/LoRA on RunPod → selected hosted C model → “hints unavailable”.
  Practice continues independently. Cold starts that exceed the timeout use this same path.
- Enforce timeouts, per-user rate limits and the global usage budget before public launch.
  The same citation and leak checks apply to both models and hosted fallback output.

## Proposed serving test (not yet authorized or run)

Thomas's account and go-ahead are still needed to create a throwaway endpoint.
Use the worker limits above and delete the endpoint after measurement.
Record image/model/adapter versions, quantization, GPU, context/output limits and concurrency.
Measure initial cold start, latency, idle billing and cached-worker reuse after an hour idle.
Exercise requests with and without the adapter, timeout fallback and scale-to-zero behavior.
Record fit/peak memory and the actual bill; compare with the [cost assumptions](02-sizing-and-costs.md).
An unsuccessful test reopens serving choice; it does not silently change the accepted plan.

See the [open decisions register](../../superpowers/plans/portfolio-mvp/milestone-c/03-open-decisions.md).
