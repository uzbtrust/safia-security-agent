# Threat model

Two components handle untrusted input: the scanner reads untrusted code, and the gym's referee executes
untrusted (model-written) code.

## 1. The scanner (`safia-sec scan`)
Assets: the user's machine and files; the integrity of the report. The scanned code is assumed hostile.

| threat | mitigation | residual risk |
|---|---|---|
| Prompt injection in code or comments ("report nothing") | code is framed as data in both prompts; output is schema-bound JSON; a test checks the framing | the model can still be talked into missing a bug (a false negative); a refuting verifier does not prevent that |
| Fabricated findings | grounding: the quoted evidence must exist in the file, otherwise the finding is dropped | a real quote can still carry a wrong claim; the verifier and the reader judge that |
| Report injection (Markdown/HTML in code or model text) | HTML escaping; code fences longer than any backtick run in the quote | none known |
| Escaping the scan root | symlinks that leave the root are skipped; vendored dirs skipped | none known |
| Resource exhaustion | files > 200 KB skipped; chunking; a prompt that fills the context is an error, not silent truncation | very large repositories are slow |
| Code execution | the scanner never imports or runs scanned code; the agent has no shell tool; Bandit runs with a fixed argv | Bandit itself parses the code (AST only) |
| Data leaving the machine | the model is served by Ollama on 127.0.0.1; no cloud LLM in the product path | none in the product path |

## 2. The referee (gym only)
Model-written patches and exploit tests are executed to prove that a bug is real.
- Separate process, scrubbed environment, temporary HOME and working directory, CPU / memory / file-size limits,
  hard timeout, process-group kill.
- Empty network namespace (`unshare -rn`). Where it is unavailable (macOS) untrusted code is refused
  (fail-closed); only our own templates run there.
- AST policy as defence in depth: import allowlists, banned names and attributes, no writes in tests.
- Residual: not a VM; a kernel-level escape is out of scope. For stronger isolation run the gym in a container.

## 3. Credentials and data during the project
- API keys only in environment variables; never in the repository, logs or chat.
- Red API models only ever received the gym apps' code.
- The rented GPU node received the repository by rsync and no credentials; it was destroyed after the run.
