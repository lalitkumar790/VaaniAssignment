# Provisional semantic quality audit — actual V3 hosted Groq

**Important:** These 18 judgments are from an assistant reviewing the model's answers and the cited contexts. They are **not an independently verified human evaluation**. Review every row against the pinned PDFs before using the semantic score in an application. The project's automated substring oracle gave a different result (6 correct, 7 wrong, 2 refused wrongly, 3 refused correctly), largely because paraphrases and math characters do not always match string expectations.

**Assistant semantic review:** 12/18 correct and cited; 3/18 correct refusals; 2/18 incorrect refusals; 1/18 incorrect answer. Real hosted run: [GitHub Actions V3](https://github.com/lalitkumar790/VaaniAssignment/actions/runs/42870960714). Original machine-read trace: [v3_real_traces.json](artifacts/v3_real_traces.json).

| Request | Original question | Proposed grade | Rationale | Actual Groq answer |
|---|---|---|---|---|
| real-000 | What does the Transformer replace from recurrent sequence models? | correct | Architecture: replaces recurrence with multiheaded attention. | The Transformer replaces the recurrent layers with multi‑headed self‑attention. [1706.03762v7 p.10] |
| real-001 | What BLEU did the Transformer report for English-to-German translation? | correct | Reported 28.4 BLEU for English–German in specified version. | The Transformer achieved a BLEU score of 28.4 on the WMT 2014 English‑to‑German translation task. [1706.03762v7 p.8] |
| real-002 | What BLEU score did the Transformer reach on English-to-French? | correct | Reported 41.8 BLEU for English–French. | The Transformer achieved a BLEU score of 41.8 on English-to-French. [1706.03762v7 p.1] |
| real-003 | Why does the Transformer decoder use masking? | correct | Future-token masking preserves autoregression. | The Transformer decoder uses masking to prevent positions from attending to subsequent positions, preserving the auto‑regressive property. [1706.03762v7 p.5] |
| real-004 | What factor scales dot-product attention scores? | correct | 1/sqrt(d_k) equivalent to square-root scaling. | The dot‑product attention scores are scaled by the factor 1/√dk. [1706.03762v7 p.4] |
| real-005 | How many attention heads are used in the base Transformer? | refused_wrongly | Evidence appears retrievable but answer refused. | I can't verify that from the three specified papers, so I won't guess. |
| real-006 | Which mathematical functions are used in the Transformer positional encoding? | correct | Sine and cosine at different frequencies. | The Transformer uses sine and cosine functions of varying frequencies for positional encoding. [1706.03762v7 p.6] |
| real-007 | What is the theoretical latency of Moshi? | correct | Paper explicitly states theoretical latency 160 ms. | The theoretical latency of Moshi is 160 ms. [2410.00037v1 p.26] |
| real-008 | What is the practical latency reported for Moshi? | refused_wrongly | Evidence available about audio codec but answer refused. | I can't verify that from the three specified papers, so I won't guess. |
| real-009 | How does Moshi model its own and user speech? | correct | Parallel own/user speech streams with tokens. | Moshi models its own speech and that of the user into parallel streams, generating speech as tokens from the residual quantizer of a neural audio codec while separately modeling each speaker’s audio [2410.00037v1 p.1]. |
| real-010 | What does Moshi's Inner Monologue predict before audio tokens? | correct | Aligned text before audio via inner-monologue path. | Moshi’s Inner Monologue predicts time‑aligned text tokens before audio tokens. [2410.00037v1 p.1] |
| real-011 | What is Mimi's initial audio frame length? | correct | Initial Mimi audio frame 80 ms. | Mimi’s initial audio frame length is 80 ms. [2410.00037v1 p.10] |
| real-012 | What pipeline does H-Net replace with a learned end-to-end model? | correct | Model replaces separate tokenization/LM/detokenization with end-to-end hierarchy. | H‑Net replaces the (implicitly hierarchical) tokenization–LM–detokenization pipeline with a single model learned fully end-to-end. [2507.07955v2 p.1] |
| real-013 | How much data-efficiency improvement is reported on DNA sequences? | correct | Text uses 3.6x improved efficiency; this is paper-supported even if short oracle expects ~4x. | 3.6× improved data efficiency compared to isotropic models. [2507.07955v2 p.4] |
| real-014 | Which measure guides H-Net's routing module to identify boundaries? | wrong | The routing loss alone does not fully explain boundary identification in question; too vague. | The loss guides H‑Net’s routing module to identify boundaries. [2507.07955v2 p.8] |
| real-015 | What color is the office chair of the Moshi lead author? | refused_correctly | Out-of-scope unsupported prompt, correctly refused. | I can't verify that from the three specified papers, so I won't guess. |
| real-016 | What was Vaani's stock market price on November 10, 2026? | refused_correctly | Out-of-scope unsupported prompt, correctly refused. | I can't verify that from the three specified papers, so I won't guess. |
| real-017 | Who will win the next football World Cup? | refused_correctly | Out-of-scope unsupported prompt, correctly refused. | I can't verify that from the three specified papers, so I won't guess. |

When a question was refused, the “refused_wrongly” designation means the reviewer found in-scope information that should have supported a response. This review is not a substitute for an applicant-authored accuracy rubric.
