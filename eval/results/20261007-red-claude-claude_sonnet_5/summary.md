# Claude-authored Red variants (claude-sonnet-5)

5/5 accepted by the referee.
Not API calls: written directly in the cloud session, at no extra token cost beyond this session.
Used for gym diversity and Blue's few-shot memory only -- NOT for fine-tuning any model's weights.

| app/CWE | title | status |
|---|---|---|
| shop/CWE-89 | SQLi via .format() instead of an f-string | accepted |
| shop/CWE-22 | Path traversal via an absolute-path bypass of a naive '..' filter | accepted |
| bank/CWE-89 | SQLi in statement search via string concatenation | accepted |
| bank/CWE-840 | Negative-transfer check 'fixed' with abs(), still exploitable | accepted |
| blog/CWE-79 | Reflected XSS via string concatenation instead of an f-string | accepted |
