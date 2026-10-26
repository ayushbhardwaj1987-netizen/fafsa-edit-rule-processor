# Design Decisions, Assumptions, and Trade-offs

> **Candidate review note:** Verify each decision below, revise anything you disagree with, and **add your own honest time-spent statement** before submitting. The goal is to explain decisions you can defend, not to claim work or reasoning you did not personally perform.

## Problem boundary

Implement the seven assignment-specified FAFSA edit rules, expose an HTTP endpoint, and return all applicable results in a predictable format. This is a demonstration rule processor, **not** a production FAFSA eligibility determination service.

## Rule representation and extensibility

Each rule is a small Python function returning `(status, message)`. A fixed `RULES` registry defines rule ID, severity, and function. Adding a rule means writing one function, registering it, and adding tests. This avoids introducing a DSL, database, or rule-expression parser for only seven rules; a persisted/versioned rules engine could be introduced if non-developers needed to edit rules during the year.

## Rule priority, errors, and conflicts

All seven rules run in a fixed order without short-circuiting. Independent failures accumulate so an applicant can correct multiple issues in one pass. Conditional rules return `not_applicable` when their prerequisite is absent. The result is `invalid` if any rule fails. All currently implemented violations are `error` severity, since none of the seven mandatory rules is specified as merely advisory. A future warning category would require an explicit policy defining its effect on overall validity.

Rule conflicts are a product/policy concern, not resolved by arbitrary execution order. If new rules contradict, the change should be rejected during review or accompanied by an explicit versioned override/priority policy; the current seven rules have no known inherent contradictions.

## Input handling and assumptions

- The API accepts JSON **objects**. Invalid field content is reported through rule results so the evaluator can return all relevant errors, rather than failing early with per-field 422 errors. A non-object JSON body produces HTTP 422.
- Date of birth must be an ISO `YYYY-MM-DD` date. Age is calculated as of the server's current date (injected in unit tests for deterministic boundary cases); 14th birthday is valid. No maximum age is enforced because the seven **required** rules specify only a minimum.
- SSN is exactly nine ASCII digits, **not** real-world SSN issuance validation. The student SSN is always checked; a spouse SSN, if present, is also format-checked. For married applicants, spouse first name, last name, and SSN are required. The specification says “spouse information,” and these required fields make that obligation explicit.
- State codes are the 50 U.S. states only, in uppercase. DC and territories are excluded because the instruction says "US state abbreviation" rather than "state or territory". This should be clarified if production requirements differ.
- Student income is required and must be nonnegative; parent income is required only if dependent but is checked for nonnegative values whenever supplied. Missing optional parent income is valid for independent applicants.
- Household counts are nonnegative integers, with number in college at most number in household. A stricter minimum of one household member is not included because the provided rule does not specify it.
- The seven rules intentionally do not validate student name completeness or all possible status-enumeration values; those are logical future extensions, not named edit rules. In production, schema validations for these fields should be added deliberately.
- Examples use fictional SSNs. No real applicant data is retained or logged.

## Testing approach

Pytest tests each rule (including failure cases, boundary dates, missing/invalid data, spouse/parent dependencies) and exercises the HTTP route through TestClient. Coverage is measured for both lines and branches, with a 90% minimum gate. Coverage is evidence of executed code paths, **not proof** of correctness, so tests emphasize meaningful boundary and negative scenarios.

## Performance and scaling

Each application evaluates a fixed seven-rule registry: O(R) time per application and O(R) response size, with R = number of rules. Rules are in-memory, stateless and use no network calls, so the HTTP API can scale horizontally. For batch throughput, a later version could accept multiple applications, retain a versioned rule set, and add bounded parallelism; adding a queue is not justified by the current single-application requirements.

## Production follow-ups (intentionally out of scope)

- Authentication and authorization, request size limits, TLS, request IDs, structured redacted logs and metrics.
- Explicit rule versioning and effective dates for rules that change during the year.
- Proper treatment of personal information (SSN), privacy, retention and audit trails.
- Policy clarification for territories, invalid enumerations, missing names, minimum household size and warning severities.
- CI, containerization, rate limiting, and application-level telemetry.

## AI usage and time spent

GDIT explicitly encourages AI tools. Development assistance was used to draft and test this implementation. The submitting candidate should inspect the implementation, run it locally, decide whether to keep or change the design, and be able to extend it live.

**Actual active time spent by the candidate:** _Fill in truthfully before submission, including review, adjustments, testing, documentation and Git operations. Do not claim a two-hour duration without measuring it._
