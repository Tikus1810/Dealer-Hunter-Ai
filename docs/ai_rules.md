# AI Rules Framework (Band 16: AI_Rules)

Band 16's spec (`Band 16/Band_16_AI_Rules.md` — supplied separately by the
user after the original upload, see the root README's "Decisions made"
note) is a section-header skeleton, not a filled specification (true of
Bands 11–15 and 17–20 — see [README.md](../README.md#status)). This
document is the governance layer Band 16 asks for: it doesn't introduce
new AI features —
DealBrain (Band 05/Task #6), RepairBrain (Band 06/Task #7), and Vision AI
(Band 08/Task #8) already existed — it formalizes the rules those three
were already following ad hoc, closes the two concrete gaps that review
surfaced (model/prompt versioning, and score/confidence values that could
only be trusted if every producer remembered to clamp them), and gives
future AI features one place to check themselves against.

## The five rules

Every AI-derived value this codebase produces — a Deal Score, a repair
score, a cosmetic-condition assessment — follows these, and any new
AI-adjacent feature should too:

### 1. Explainable — no hidden rules

Every score ships with the human-readable reasons behind it, not just a
number. `ExplanationFactor` (DealBrain: `scoring/domain/entities.py`) and
the equivalent free-text `summary`/`risk_notes` (RepairBrain) and
`reasoning` (Vision AI's `CosmeticAssessment`) are not optional fields
bolted on for a UI — `ScoringEngine`/`RepairScoringEngine` cannot produce a
`DealScoreResult`/`RepairReport` without them structurally requiring at
least the *shape* for an explanation (an empty list is possible, a field
that doesn't exist is not).

### 2. Honest about uncertainty — never guess to fill a gap

"We don't know" and "we know, and it's bad" are different facts, and this
codebase keeps them different rather than defaulting one to the other:

- Vision AI's `cosmetic_condition` is `"not_available"` (not `"unclear"`,
  not a guessed value) when no analyzer is configured at all;
  `"unclear"` is a real answer *from* the model, reserved for when photos
  exist but don't show enough to judge.
- RepairBrain's `DetectedFault.is_confirmed` separates faults the listing
  explicitly states from faults only inferred from suspicious phrasing —
  both feed the repair score, but the confirmed/inferred distinction is
  preserved all the way to `RepairScoringEngine`'s per-fault penalty
  (`PER_FAULT_PENALTY` vs. the smaller `PER_INFERRED_FAULT_PENALTY`).
- The Claude Vision system prompt (`claude_vision_provider.py`'s
  `_SYSTEM_PROMPT`) explicitly instructs the model to answer `"unclear"`
  with low confidence rather than guess when photos are insufficient —
  this rule is enforced at the prompt level, not just trusted.

### 3. Versioned — every AI-derived value is traceable to what produced it

| Field | Entity | What it tracks |
| --- | --- | --- |
| `scoring_version` | `DealScoreResult` | The `ScoringEngine`/analyzer formula version |
| `report_version` | `RepairReport` | The `RepairScoringEngine` formula version |
| `observation_version` | `VisionObservation` | The classical image-quality pipeline version |
| `cosmetic_model_used` | `VisionObservation` | The actual Claude model that ran (new, Task #17) |
| `cosmetic_prompt_version` | `VisionObservation` | The system prompt version that ran (new, Task #17) |

The last two closed a real gap: `ANTHROPIC_VISION_MODEL` is
operator-configurable (`.env`), so two cosmetic assessments taken months
apart could have run against entirely different Claude models with no way
to tell after the fact. `ClaudeCosmeticConditionAnalyzer.analyze()` now
stamps `model_used=self._model` and `prompt_version=_PROMPT_VERSION` onto
every `CosmeticAssessment` it returns, and `OutputFormatter` carries both
through to the final `VisionObservation` (`None` when no analyzer ran at
all — there's nothing to attribute).

**Rule for changing a prompt or a scoring formula**: bump the
corresponding version string whenever the change alters the *meaning* of
the output (not for comment/typo fixes) — see `claude_vision_provider.py`'s
comment next to `_PROMPT_VERSION` for the exact line. A version bump is
free; a silently-reinterpreted historical assessment is not.

### 4. Bounded — a score value cannot exist outside its documented range

New in Task #17: `app/core/ai_rules.py`'s `validate_score`/
`validate_confidence` run from every score/confidence-bearing entity's
`__post_init__` (`DealScoreResult`, `AnalyzerOutput`, `RepairReport`,
`CosmeticAssessment`, `VisionObservation`) — the entity **refuses to be
constructed** outside its documented range (score: 0–100 integer,
confidence: 0.0–1.0), regardless of what code tried to build it.

This is deliberately a second line of defense, not a replacement for the
first: `ScoringEngine.combine()`/`RepairScoringEngine.score()` already
clamp their outputs into range before returning. The entity-level check
exists because clamping-at-the-engine only protects values that flow
through that one code path — a future analyzer, a bugfix, or a test double
that constructs one of these entities directly bypasses it entirely.
Raises a plain `ValueError` (a programming-invariant violation, this
codebase's bug — not `app.core.exceptions.ValidationError`, which is for
rejecting bad *user input*); see `ai_rules.py`'s own docstring for that
distinction.

`AnalyzerOutput.score_contribution` is the one deliberate exception — it's
an unbounded signed delta by design (`ScoringEngine.combine()` sums every
analyzer's contribution before clamping the *final* score), so it is not
range-checked; only `AnalyzerOutput.confidence` is.

### 5. Reviewable weights — tunable, not hardcoded assumptions

Every scoring/penalty constant lives at module level with a name and a
comment, not inline as a magic number:

- DealBrain: `app/modules/scoring/domain/analyzers.py` (per-analyzer
  keyword lists, score deltas) and `scoring_engine.py`'s `BASE_SCORE`.
- RepairBrain: `app/modules/repair/domain/scoring_engine.py`'s
  `BASE_SCORE`, `PER_FAULT_PENALTY`, `DIFFICULTY_PENALTY`, cost thresholds.
- Vision AI: `app/modules/vision/domain/confidence.py`'s
  `MIN_IMAGES_FOR_COMPLETE_SET`, `INCOMPLETE_SET_CONFIDENCE_PENALTY`, and
  `observation_engine.py`'s `BLUR_VARIANCE_THRESHOLD`.

All of these are documented, in every module's own docstring, as a
reasonable v1 starting point rather than a specification-mandated formula
— Band 05/06/08 define the required *properties* of a score (explainable,
deterministic, versioned, bounded) but never a concrete calculation.
**Governance for changing a weight**: bump the corresponding version
string (rule 3) alongside the change, and — once real usage/outcome data
exists to validate against (none does yet, see "Known gaps") — prefer
tuning against measured accuracy over intuition.

## Confidence handling: what the number means, and what nothing does with it yet

Confidence is informational everywhere in this codebase today — no code
path currently *branches* on a confidence value (e.g. hiding a
low-confidence score, or refusing to surface a repair recommendation below
some threshold). `DealScoreResult.confidence` is the average of every
analyzer's own confidence; `VisionObservation.confidence` is the average
of image-quality confidence and (if run) the cosmetic model's own
confidence. Both are exposed via the API for the Flutter app to decide how
to present, not filtered server-side. If a confidence-gated behavior
becomes a real product requirement (e.g. "don't push a notification for a
Deal Score below 0.5 confidence"), that's a new, explicit rule to add here
— don't infer one from the number just being present.

## Prompt management

One prompt exists in this codebase today: `claude_vision_provider.py`'s
`_SYSTEM_PROMPT`, versioned via `_PROMPT_VERSION` (rule 3). There is no
external prompt-management system (no prompt registry, no A/B testing, no
per-environment prompt override) — the prompt is source code, reviewed and
versioned the same way as everything else. Revisit this if a second prompt
is added and the two need independent lifecycle management.

## Known gaps

- **No confidence-gated behavior** exists yet — see "Confidence handling"
  above. Not a bug, just not built, because nothing has asked for it.
- **No real usage/outcome data** exists to validate any scoring weight
  against (no deployment has run long enough to know if a v1 DealBrain
  "buy" recommendation actually correlated with a good purchase) — every
  weight is an informed starting point, explicitly documented as such in
  its own module.
- **Only one AI provider (Claude) is wired in** — model versioning (rule
  3) tracks *which Claude model*, not provider-swapping; if a second
  vision provider is ever added, `model_used` should probably become
  `provider:model` to stay unambiguous.
- **`AnalyzerOutput`/`DealScoreResult`/`RepairReport`/`CosmeticAssessment`/
  `VisionObservation`'s new `__post_init__` checks are a new pattern in
  this codebase** (no prior domain entity used `__post_init__` before
  Task #17) — if this pattern proves useful, consider applying the same
  "entity validates its own invariants" principle to other bounded domain
  values as they're identified, not just the five above.
