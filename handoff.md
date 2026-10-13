# HANDOFF.md — Adaptive Mathematics Tutoring Platform

## 1. Project Overview

We are developing an adaptive AI-powered mathematics tutoring and practice platform, initially targeting UC Berkeley's lower-division undergraduate mathematics curriculum.

The application will combine:

- A curated database of existing mathematics problems from openly licensed textbooks and authorized university practice exams.
- Personalized problem recommendations based on student performance, prerequisites, and estimated mastery.
- Reliable computational answer verification using symbolic and numerical mathematics.
- Retrieval-Augmented Generation (RAG) for textbook-grounded explanations and tutoring.
- An LLM-based tutoring assistant capable of providing progressively more detailed hints.
- A web interface supporting mathematical notation through a LaTeX-friendly equation editor.
- AWS infrastructure for deployment, storage, and potentially model training.

The primary objective is to build a technically rigorous, reliable, extensible ML engineering project rather than a generic LLM chatbot.

**Current status: Planning only. No code, repository, infrastructure, or dataset has been created.**

## 2. Developer Background and Goals

The developer is a recent UC Berkeley mathematics graduate with a Data Science minor.

Relevant experience includes:

- Python, Java, SQL, R, pandas, NumPy, scikit-learn, and LightGBM.
- Undergraduate and graduate-level mathematical coursework.
- Several years of mathematics tutoring and mentoring.
- Previous ML projects involving model comparison, feature engineering, hyperparameter tuning, and conformal prediction.

Primary goals:

1. Build a useful mathematics tutoring application.
2. Develop hands-on machine learning engineering and software engineering experience.
3. Gain practical experience with AWS, APIs, database systems, RAG, and possibly model fine-tuning.
4. Create a strong, defensible project for entry-level Machine Learning Engineer applications.
5. Maintain rigorous testing, evaluation, reproducibility, and clear technical documentation.

The developer understands programming and ML concepts but may consult documentation for syntax and implementation details. Do not assume a need for beginner-level programming instruction.

The project will be developed with assistance from Claude and ChatGPT. Technical decisions, experiments, and changes should be documented.

## 3. Target Courses

Initial target:

- Calculus I

Potential expansion:

- Calculus II
- Linear Algebra
- Multivariable / Vector Calculus
- Differential Equations
- Discrete Mathematics, initially restricted to computationally verifiable problems

Avoid general proof verification as a core capability.

Natural-language undergraduate proof verification remains unreliable and is an active research problem. The application should not claim to certify arbitrary proofs.

## 4. Core Product Requirements

### 4.1 Curated Problem Bank

Use existing mathematical problems rather than primarily generating new ones.

Potential sources:

- Openly licensed mathematics textbooks.
- Public university practice exams with appropriate reuse permissions.
- Authorized problem sets and worked examples.

Each problem should ideally contain:

- Unique ID
- Course
- Topic and subtopic
- Source and attribution
- Section, page, and problem number
- Problem statement
- Mathematical expressions
- Difficulty estimate
- Prerequisite concepts
- Answer, if available
- Verification method
- Validation status
- Relevant explanatory passages

The system must distinguish between successfully extracted problems and independently validated problems.

Problems with uncertain extraction or unsupported verification should not be presented as reliably auto-gradable.

### 4.2 Textbook and Exam Ingestion

Most source documents will be PDFs.

We cannot assume that original LaTeX source files or HTML versions are available.

**Preferred extraction service: Mathpix API.**

Investigate:

- Mathpix PDF conversion
- Mathpix Markdown output
- Batch document processing
- Mathematical notation preservation
- API cost and document retention policies

Proposed workflow:

1. Obtain a document with appropriate processing and reuse permissions.
2. Convert PDF to structured mathematical text using Mathpix.
3. Identify definitions, explanations, worked examples, exercises, and solutions.
4. Preserve original source locations.
5. Extract exercises into structured records.
6. Match available answers or solutions to exercises.
7. Validate mathematical extraction and answer correctness.
8. Store validated problem metadata in a database.
9. Index explanatory material for RAG.

Important: Mathpix handles mathematical OCR, not the entire exercise extraction, classification, matching, or correctness-verification process.

Use manual inspection and automated validation where necessary.

Ingestion should run as an offline or batch process, not during every student interaction.

**Do not bulk-download copyrighted materials or assume that publicly accessible PDFs are freely redistributable.** Track source licenses and permitted uses.

### 4.3 Answer Verification

Use deterministic verification whenever practical.

Candidate technologies:

- SymPy
- NumPy
- Python numerical methods
- Validated answer keys

Support multiple answer types:

**Numerical answers**

Compare student and expected values using combined absolute and relative tolerances:

|student - expected| ≤ absolute_tolerance + relative_tolerance × |expected|

Tolerances should account for the problem's requested precision and mathematical context.

**Symbolic expressions**

Use SymPy to evaluate symbolic equivalence where supported.

**Derivatives**

Check symbolic equivalence between the submitted derivative and a validated expected derivative.

**Indefinite integrals**

Differentiate the student's proposed antiderivative and compare it to the integrand, accounting for domains and constants as appropriate.

**Linear algebra**

Support matrix operations, systems of linear equations, and other computational tasks.

**Differential equations**

Verify proposed solutions by substitution, including initial conditions where applicable.

The verifier should return at least:

- Correct
- Incorrect
- Unable to verify

Do not automatically classify unsupported or inconclusive checks as incorrect.

Important security requirement:

Student expressions are untrusted input. Avoid unrestricted Python evaluation or unsafe symbolic parsing. Use constrained parsing, resource limits, and isolation where appropriate.

Correct answers also do not necessarily imply correct reasoning.

### 4.4 Retrieval-Augmented Tutoring

RAG will primarily retrieve explanatory mathematical knowledge, not act as the entire problem database.

Use a structured database for problem records, answers, tags, and student attempts.

Use a retrieval index for:

- Definitions
- Theorems
- Explanations
- Worked examples
- Relevant textbook sections

Possible retrieval approaches:

- Dense vector retrieval
- BM25 keyword retrieval
- Hybrid retrieval

Initially compare a simple retrieval baseline against an improved approach.

Preserve citations to source documents, sections, and pages.

The tutor should:

- Explain relevant concepts.
- Offer progressive hints.
- Prefer guiding students over prematurely revealing solutions.
- Respond to the student's specific question or misconception.
- Support full explanations when appropriate.
- Acknowledge uncertainty when mathematical verification is unavailable.

RAG retrieval does not guarantee mathematical correctness.

### 4.5 Personalized Problem Recommendations

This should become one of the central ML components.

The system should select problems based on:

- Previously attempted problems
- Correctness history
- Prerequisite knowledge
- Topic mastery estimates
- Estimated difficulty
- Previously viewed hints
- Repeated attempts
- Recent performance

Start with a transparent rule-based recommendation algorithm.

Potential later approaches:

- Bayesian Knowledge Tracing
- Item Response Theory
- Other supervised student-performance models
- Contextual bandits, if sufficient reliable interaction data becomes available

Do not introduce complex ML before establishing baselines and obtaining suitable data.

Measure recommendation and student-performance prediction quality separately from claims about actual learning gains.

A core research question is whether personalized recommendations outperform static textbook order or simpler recommendation policies.

### 4.6 Practice Quizzes and Exams

Use the curated problem bank to assemble quizzes and practice exams.

Support:

- Topic-specific practice
- Mixed-topic quizzes
- Practice midterms and finals
- Eventually, adaptive quizzes based on student performance

Avoid relying on LLM-generated questions as the primary problem source.

Select existing problems using course coverage, difficulty, prerequisites, and student mastery.

### 4.7 Student-Submitted Questions

Students may type arbitrary mathematics questions.

A LaTeX-friendly equation editor is strongly preferred.

Candidate technology: MathLive.

Support a natural-language question field in addition to structured mathematical notation.

The system should distinguish two modes:

**Practice Mode**

- Uses curated, validated problems.
- Supports trusted answer checking where possible.
- Records results for personalization.

**Ask Mode**

- Accepts student-entered questions.
- Retrieves relevant explanations.
- Provides tutoring and hints.
- May use symbolic verification when supported.
- Does not automatically add unverified questions to the shared problem database or treat them as reliable mastery assessments.

Student PDF or screenshot uploads are not required for the MVP.

## 5. Proposed Technology Stack

These are initial preferences, not irreversible commitments.

| Component | Candidate technology |
|---|---|
| Backend | Python, FastAPI |
| Frontend | React |
| Math input | MathLive |
| Database | SQLite initially, PostgreSQL later |
| Document extraction | Mathpix API |
| Symbolic computation | SymPy |
| Numerical computation | NumPy |
| Embeddings | Sentence Transformers or hosted embeddings API |
| Retrieval | FAISS initially |
| LLM | Pretrained model via API |
| Deployment | AWS |
| Document storage | AWS S3 |
| Testing | pytest |
| Containers | Docker |
| Version control | Git/GitHub |

Choose the simplest viable implementation before introducing additional infrastructure.

Do not introduce Kubernetes, distributed microservices, or heavyweight MLOps tools unless the requirements justify them.

## 6. Model Fine-Tuning

Fine-tuning is a possible future experiment, not an MVP dependency.

Potential tutoring dataset:

- MathDial

Potential approaches:

- Supervised fine-tuning
- LoRA / QLoRA

Proposed experiment:

1. Pretrained LLM + RAG
2. Pretrained LLM + RAG + explicit tutoring instructions
3. Fine-tuned LLM + RAG

Compare mathematical correctness, hint quality, solution leakage, and responsiveness to student mistakes.

Do not assume fine-tuning improves the system.

Fine-tuning should target tutoring behavior rather than attempt to replace mathematical reference retrieval.

TensorFlow is not required. PyTorch-based tooling may be more suitable for open-source LLM fine-tuning.

## 7. Evaluation Requirements

Evaluation is a priority because this is intended as a rigorous ML engineering project.

Maintain independent evaluation sets and reproducible experiments.

Potential metrics:

**Document ingestion**
- Exercise extraction accuracy
- Equation transcription accuracy
- Exercise/solution matching accuracy

**Answer verification**
- False acceptance rate
- False rejection rate
- Inconclusive verification rate
- Performance across supported problem types

**Retrieval**
- Recall@K
- Mean Reciprocal Rank
- Citation accuracy

**Tutoring**
- Mathematical correctness
- Hint usefulness
- Premature solution disclosure
- Responsiveness to misconceptions

**Recommendations**
- Student performance prediction accuracy
- Ranking quality against expert-labeled cases
- Performance relative to rule-based and static baselines

**System engineering**
- API latency
- Error rates
- LLM API costs
- Document processing costs
- Deployment reliability

Do not claim improved student learning without appropriately designed student testing.

## 8. AWS Architecture

AWS should be used where it provides genuine engineering value.

Likely uses:

- S3 for authorized document storage and processed artifacts.
- Container hosting for the backend API.
- Managed database services if justified.
- Optional training or batch-processing compute.

Do not introduce cloud services merely to accumulate technologies.

Start development locally and deploy once the application is functional.

Configure cost monitoring and avoid leaving unnecessary paid services running.

Keep credentials in environment variables or appropriate secrets-management services.

Never commit API keys or credentials to Git.

## 9. Initial MVP

The first release should target **Calculus I only**.

Initial scope:

- One openly licensed textbook PDF.
- Approximately 50–100 extracted practice problems.
- A smaller subset of independently validated, automatically gradable exercises.
- Basic topic and difficulty metadata.
- Numerical and symbolic answer verification.
- Simple student interaction history.
- Basic rule-based problem recommendations.
- Textbook-grounded explanations through RAG.
- Minimal user interface with math-friendly input.
- Automated backend tests.

The exact number of validated problems should depend on extraction quality and available time.

Do not expand to additional courses before the initial workflow is reliable.

## 10. Development Priorities

Recommended implementation order:

### Phase 1 — Foundation

- Choose repository structure.
- Establish Python backend.
- Define problem and student-attempt schemas.
- Set up pytest.
- Create a small manually validated problem fixture.

### Phase 2 — Mathematical Verification

- Implement numerical answer checking.
- Implement supported symbolic checks.
- Test edge cases and invalid inputs.
- Provide explicit inconclusive outcomes.

### Phase 3 — Document Ingestion

- Test Mathpix on representative textbook and exam pages.
- Assess mathematical transcription accuracy.
- Parse exercises and source metadata.
- Store structured records.
- Create an inspection/validation workflow.

### Phase 4 — RAG Tutoring

- Chunk explanatory textbook content.
- Build embeddings and a retrieval index.
- Add citation-aware tutoring responses.
- Implement progressive hints.
- Evaluate retrieval quality.

### Phase 5 — Frontend

- Build problem selection UI.
- Integrate MathLive.
- Implement answer submission.
- Display verification feedback and tutoring hints.

### Phase 6 — Personalization

- Implement student attempt history.
- Add topic mastery estimates.
- Establish a static recommendation baseline.
- Implement a simple adaptive recommendation policy.
- Develop an evaluation framework.

### Phase 7 — Cloud Deployment

- Containerize the backend.
- Deploy through AWS.
- Configure storage and credentials.
- Measure costs, latency, and operational reliability.

### Phase 8 — Advanced ML

Only after working baseline infrastructure:

- Evaluate knowledge tracing approaches.
- Compare recommendation algorithms.
- Investigate tutoring fine-tuning.
- Expand to additional mathematics courses.

## 11. Engineering Standards

Use:

- Modular Python code.
- Type annotations where appropriate.
- Clear interfaces between components.
- Unit and integration tests.
- Reproducible experiments.
- Explicit error handling.
- Structured logging.
- API and dataset versioning where useful.
- Environment-based configuration.
- Clear README and documentation.
- Small, meaningful Git commits.

Prefer straightforward solutions over speculative abstraction.

Keep ingestion, retrieval, verification, recommendation, tutoring, and API logic logically separate.

Do not claim features have been implemented before they exist.

## 12. Instructions for Claude and ChatGPT

The developer will use multiple LLM assistants, including Claude with Superpowers and ChatGPT.

Treat this document as the shared project handoff.

When beginning work:

1. Review this document and identify assumptions or unresolved architectural decisions.
2. Use Superpowers brainstorming to examine the MVP before implementing it.
3. Produce a concrete technical design and phased implementation plan.
4. Break work into small, independently testable tasks.
5. Ask for clarification when a decision materially affects architecture or project scope.
6. Prefer tests and verified outputs over assumptions.
7. Explain important design tradeoffs without unnecessarily overexplaining familiar programming concepts.
8. Avoid implementing future-phase features prematurely.

When making substantial changes:

- Update project documentation.
- Record architectural decisions and their rationale.
- Record completed features and test results.
- Identify limitations and unresolved issues.
- Preserve a clear next-step handoff for the other assistant.

Superpowers skills should be used when appropriate, particularly brainstorming, planning, test-driven development, debugging, and verification.

Do not claim tests passed, deployment succeeded, or code was executed unless independently confirmed.

## 13. Open Questions

These remain to be resolved during brainstorming:

- Which openly licensed Calculus I PDF should be used first?
- What is the minimum problem schema?
- What Mathpix output format is easiest to process reliably?
- How should exercises be separated from explanatory text?
- How should exercise solutions be matched and verified?
- Which answer formats should the first verifier support?
- Which embedding model and retrieval baseline should be used?
- Which LLM provider offers a suitable cost/quality balance?
- How should student progress be stored during the MVP?
- What is the simplest useful recommendation baseline?
- Which AWS hosting arrangement is justified by expected usage?

## 14. Immediate Next Action

**Do not begin by building the entire application.**

Start Claude's Superpowers brainstorming workflow using this document.

The first objective is to agree on:

1. A narrow MVP specification.
2. The initial data schemas.
3. The mathematical verification strategy.
4. The PDF ingestion design.
5. A measurable definition of MVP success.

After the design is approved, produce a task-level implementation plan and begin development.

The current priority is reliability, meaningful ML engineering, and completing a working system — not maximizing the number of technologies involved.