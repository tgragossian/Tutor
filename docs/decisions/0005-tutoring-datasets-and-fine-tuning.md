# 0005: tutoring datasets and the fine-tuning experiment

[Decisions index](README.md) · [Decision 0004](0004-rag-source-models-and-evaluation.md) · [Fine-tuning plan](../superpowers/plans/portfolio-mvp/04-release.md)

Status: accepted by Thomas, 2026-10-22 (§1–§3). §4 items are open. Licences as found on 2026-10-22.

## 1. Datasets and their roles

| Dataset | Content | Licence found | Role |
|---|---|---|---|
| [ScaleAI/TutorBench](https://huggingface.co/datasets/ScaleAI/TutorBench) | 1,473 expert tasks with per-task rubrics; 6 subjects (Calculus 258); use cases: adaptive explanation, feedback on work, hints; ~55% with images | none on the dataset card; [sample](https://huggingface.co/datasets/ScaleAI/tutorbench_sample) `cc-by-nc-4.0`; [paper](https://arxiv.org/abs/2510.02663) CC BY-NC-ND 4.0 | **train on non-calculus; evaluate on calculus** |
| [Eedi Question-Anchored Tutoring Dialogues 2k](https://huggingface.co/datasets/Eedi/Question-Anchored-Tutoring-Dialogues-2k) | 1,971 human tutor–student chats (UK, age ~12), anchored to misconception questions; GPT-predicted talk moves | `cc-by-nc-4.0` tag; card text says CC BY-NC-SA 4.0 | train |
| [allenai/tutormoments-preview](https://huggingface.co/datasets/allenai/tutormoments-preview) | 462 transcripts (grades 2–7), teacher-flagged "step in vs hold back" moments | `cc-by-4.0` | **evaluation only** (over-helping) |
| MathDial | teachers tutoring simulated students with errors | not yet checked | candidate for training |
| StudentBench (Handshake) | GRE study, ~175k student–AI messages | dataset not located | not used |

## 2. TutorBench training (Thomas's decision)

- **Basis:** Thomas judges training a private, noncommercial portfolio model on TutorBench to be
  fair use. Recorded facts: the dataset card states no licence; the public sample is CC BY-NC
  4.0; the paper is CC BY-NC-ND 4.0, which licenses the paper, not the dataset.
- **Split:** all 258 Calculus tasks are held out for evaluation and never used in training,
  prompting examples or response selection. Training uses the other subjects, tagged by use case.
- **Method:** TutorBench has rubrics, not reference answers. Generate several responses per
  training task, score them against the task's rubric, and train on the best (or best-vs-worst
  pairs). Judge model, prompts and scores are versioned.
- **Weights are not published.** Adapters, checkpoints and generated training sets stay out of git
  (`.gitignore`: `models/`, `data/`, `*.safetensors`, `*.gguf`) and out of the Docker image. Only
  configs, task IDs, scores and the write-up are committed. No TutorBench rows enter the repo.
- **Credit:** the README credits TutorBench (Scale AI; Srinivasa et al., 2025) and notes the
  paper's CC BY-NC-ND 4.0 licence. Eedi and others are credited under their own licences.
- Revisit if Scale AI publishes a dataset licence or objects, or before any commercial use.

## 3. Rules that keep the evaluation meaningful

- Never train on evaluation data: TutorBench Calculus, TutorMoments, and the milestone C hint
  cases. A contamination check (task-ID and text overlap) runs before every training job.
- One adapter for all three use cases (use case in the prompt), compared against the hosted model
  selected in milestone C under fixed retrieval, prompts and decoding.
- Report rubric scores with uncertainty, per use case, plus cost per hint. A null result is a
  reported finding. OpenStax text is not used for training (decision 0004 §1).

## 4. Open (Thomas to decide)

- **Use-case routing:** Claude recommends choosing the use case from the student's action (wrong
  answer → feedback on work; Hint → active-learning hint; "explain more" → adaptive explanation)
  rather than an LLM classifier, which is needed only for free-text chat.
- **Timing:** move the fine-tuning experiment to directly after milestone C, or keep it last in
  the expansion queue.
