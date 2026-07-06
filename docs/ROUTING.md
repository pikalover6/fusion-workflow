# Implementation routing

Fusion routes implementation work by expected total cost to a verified result.

```text
expected pipeline cost =
    first attempt
  + P(failure) * diagnosis cost
  + P(failure) * escalation cost
  + review cost
  + hidden-regression risk
```

The cheapest first attempt is not always the cheapest route. The strongest model is not always the safest route either: a strong deterministic oracle can make an abundant model the rational choice for difficult code.

## 1. Manager responsibilities

GPT-5.5 High owns:

- repository inspection
- product and architectural intent
- decomposition
- implementation contracts
- model selection
- worker supervision
- diff review
- integration
- final verification
- aggregate routing memory

The manager should not spend its quota writing substantial features by default.

## 2. Implementation contract

Every meaningful delegated slice should contain:

```text
OBJECTIVE
One concrete outcome.

CONTEXT
Minimum architectural context and why the change exists.

RELEVANT SURFACES
Likely files, modules, interfaces, and existing patterns.

REQUIREMENTS
Behavior that must hold.

CONSTRAINTS
Behavior and surfaces that must not change.

NON-GOALS
Explicitly excluded work.

VERIFICATION
Exact tests, commands, fixtures, benchmarks, or acceptance criteria.

AUTONOMY
Decisions the worker may make independently.

STOP CONDITIONS
When to return blocked rather than improvise.

RETURN
Status, changed surfaces, verification evidence, commit, unresolved concerns.
```

A better contract should move work to a cheaper implementer by removing unnecessary judgment.

## 3. Task shape

The manager evaluates six dimensions.

| Axis | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| Specification ambiguity `S` | exact | mostly clear | important inference | exploratory |
| Verification strength `V` | subjective/hidden | weak | good automated coverage | strong deterministic oracle |
| Coupling `C` | local | bounded subsystem | cross-cutting | systemic |
| Blast radius `B` | cheap failure | reversible | subtle regressions | security/data/money/auth/destructive/public-contract risk |
| Autonomy horizon `H` | short | moderate | sustained | long-horizon multi-stage |
| Context burden `X` | named files | subsystem | broad repository | very large repo/monorepo/history |

Do not sum these into a fake precision score. They describe different failure modes.

## 4. Hard guards

These override normal cost optimization:

```text
B=3 and V<=1     -> Sonnet Medium
B=3 and V>=2     -> at least Sonnet Low, except tightly bounded reversible experiments
C>=2 and V<=1    -> at least Sonnet Low
unresolved intent -> manager resolves before delegation
race mode         -> forbidden when B>=2 or V<=1
```

## 5. Active implementation frontier

### Abundant tier

#### DeepSeek V4 Flash

First candidate for bounded real implementation with crisp contracts and strong verification.

Good tasks:

- feature slices with acceptance tests
- bugs with reliable reproducers
- algorithms
- parsers
- API endpoints with contracts
- state machines with exhaustive tests
- established-pattern backend or frontend work

#### MiMo-V2.5

Second abundant general implementer. Use when local history favors it or as the default independent challenger in race mode.

The abundant tier is not restricted to mechanical work.

### Workhorse and specialists

#### Qwen3.7 Plus

Default broader implementation workhorse. Prefer when:

- several related files are involved
- verification is moderate rather than excellent
- the task needs normal implementation judgment
- abundant-tier history is weak for the task family

#### MiniMax M3

Prefer when context burden dominates:

- large repository surface
- many related modules
- long files
- monorepo context

#### Kimi K2.7 Code

Prefer when autonomy horizon dominates:

- many dependent steps
- sustained implementation
- stable contract
- completion requires maintaining a coherent plan for a long run

#### GLM-5.2

Prefer when terminal investigation dominates:

- build failures
- dependency/toolchain failures
- environment debugging
- runtime reproduction
- repeated command-driven hypothesis testing

### Premium tier

#### Sonnet 5 Low

Use for:

- difficult but well-specified implementation
- broad cross-file changes
- weakly verified work where subtle mistakes matter
- high-confidence closing after an open-model failure

#### Sonnet 5 Medium

Use when the implementer itself needs expensive judgment:

- architectural inference
- mysterious bugs
- subtle cross-system invariants
- high-risk changes
- escalation after strong models fail for different reasons

Do not use Sonnet Medium merely because a feature is large.

## 6. Initial selection algorithm

```text
resolve intent and design ambiguity
        |
        v
build explicit implementation contract
        |
        v
apply hard guards
        |
        v
build candidate set from task shape
        |
        +-- strong V + low B + bounded -> DeepSeek / MiMo
        +-- normal broader feature     -> Qwen Plus
        +-- context burden dominant    -> MiniMax M3
        +-- autonomy horizon dominant  -> Kimi K2.7 Code
        +-- terminal/debug dominant    -> GLM-5.2
        `-- weak oracle / high risk    -> Sonnet Low or Medium
        |
        v
adjust with empirical local history
        |
        v
choose lowest expected pipeline cost
```

## 7. Race mode

Race two workers only when:

- `V >= 2`
- `B <= 1`
- implementations can be isolated
- selection is objective and cheap

Default race:

```text
DeepSeek V4 Flash --\
                      > same contract -> verify -> inspect -> keep winner
MiMo-V2.5 ----------/
```

Good race tasks:

- difficult bugs with reproducers
- isolated algorithms
- parser/compiler tasks
- benchmarked optimization
- tricky but objectively tested components

Bad race tasks:

- subjective UX
- architecture
- weakly tested integrations
- security-sensitive changes

## 8. Failure handling

### Same-model repair

Allow one repair when:

- the overall approach is sound
- failure is localized
- a test or diagnostic identifies the problem

Send only:

- original contract
- diff summary
- failing evidence
- manager's concise suspected cause

Do not resend a giant transcript.

### Escalation

Typical path:

```text
DeepSeek / MiMo
        |
        v
Qwen or task specialist
        |
        v
Sonnet Low
        |
        v
Sonnet Medium
```

Skip tiers when failure reveals hidden risk, architectural ambiguity, or a specialist mismatch.

### Abort conditions

Stop a route when it:

- repeats substantially the same failed action twice
- makes no material progress across several tool cycles
- broadens scope without authorization
- changes tests to conceal failure
- cannot state the active acceptance criterion

The question is not whether the agent might eventually recover. The question is whether its expected future value remains positive.

## 9. Integration protocol

Every implementation worker:

1. runs in an isolated git worktree
2. performs its own foreground verification
3. commits completed work
4. returns the commit SHA and evidence

The manager then:

1. inspects the commit and diff
2. rejects, repairs, or cherry-picks it
3. resolves small integration issues directly
4. reruns relevant verification in the main checkout
5. exercises runtime behavior when practical

A green worker summary is not sufficient evidence.

## 10. Learning from real work

The manager maintains compact aggregate routing memory.

Recommended fields:

```text
model
task family
S/V/C/B/H/X
first-attempt success
repair required
escalation required
verification result
major review defect
rough quota/turn cost when observable
```

Task families should stay broad:

- backend-feature
- frontend-feature
- debugging
- integration
- algorithmic
- build-tooling
- infrastructure
- migration
- large-refactor

After enough local evidence exists, empirical success on your projects should beat generic benchmark priors.

## 11. Exploration policy

For low-risk strongly verified tasks, occasionally route to a cheaper challenger with insufficient data rather than always exploiting the current favorite.

Suggested starting point:

```text
90-95%  choose the current expected-cost winner
5-10%   try a cheaper under-sampled challenger
```

Never explore on high-blast-radius or weakly verifiable work.

## 12. Healthy routing distribution

This is a smell test, not a quota:

| Approximate share | Destination |
|---|---|
| 30-40% | DeepSeek Flash / MiMo |
| 30-40% | Qwen Plus / MiniMax M3 |
| 10-15% | Kimi / GLM |
| 10-20% | Sonnet Low |
| under 5% | Sonnet Medium |

If most work goes to Sonnet, contracts may be too ambiguous or the manager may be underusing verification leverage. If almost everything goes to the abundant tier, review and retry costs may be dominating.
