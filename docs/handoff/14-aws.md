[Index](../../handoff.md) · [Review](../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 449–469. Review findings remain unresolved.

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

<!-- End preserved source. -->
