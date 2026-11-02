# Substantive writing and revision

For substantial or prolonged work, retain decisions, findings, evidence and next
steps through the [chosen lifecycle's progress](../../../ecosystem/docs/progress.md).
Synchronize personal milestones only when local policy authorizes it; do not
open another contract or turn a small task into a tracking procedure.

## From the task to the document

Establish what the text must achieve, for whom, with what prior knowledge and
in which language, voice, length and format. For a revision, identify what may
change: expression, structure, argument or research. Respect the supplied
materials and conventions, and the requested depth and output surface.
An explanation in conversation does not become a file by default. Infer enough
to make progress; a question is justified if the answer changes the result,
not as a ritual.

A significant delivery is, for example, a complete article, a report intended
to inform a decision or a revision that changes an essential argument.
A sentence correction or tone adjustment normally needs no research,
delegation or review dossier. Fiction and creative prose are assessed by
intention, coherence and effect; factual checking applies when a claim is
presented as real and its accuracy matters to the task.

For a significant delivery, translate the task into observable requirements:
questions to answer, concepts to define, length, material to preserve, necessary
sources and acceptance conditions. Declare only intentional deliverables and
their exact paths. Do not archive prompts, conversations or transcripts as
though they were documentation of the work.

Choose the lifecycle using the
[common protocol](../../../ecosystem/references/protocol.md). For a substantive
delivery without publication, use its portable operations for requirements,
authorship, checks, review and closure. An ordinary Git edit uses the receiving
contract, without a second mandatory record merely because this skill is used.
If the report requires the portable engine's semantic guarantees as well as
publication, connect reviewed artifacts and their evidence to the Git
integration; do not assume equivalence or automatic synchronization between
their controls. Respect publication permissions and retain the existing task.
The portable engine works without Git: do not create a repository to be able
to write. If a required capability is unavailable, declare the limitation and
pending work; do not simulate an operation, a review or approved closure.

## Structure and responsibility

When a choice is material, compare a few structures according to purpose:
a decision may require a result, reasons and consequences; an explanation may
require concepts, mechanism and example; an essay may advance through a thesis,
objection and response. These are options, not mandatory templates. Choose by
the reader's needs and the strength of the argument. The structure must reveal
what each section contributes and how it connects to the previous one.

Keep an integrator responsible for thesis, terminology, voice, transitions and
conclusion. Delegate separable research questions, sections or reviews when
that saves time or provides a contrasting assessment. Assign one writer per
file; if several agents contribute to the same document, the integrator
incorporates their results. No agent discards others' changes or publishes
independently.

Use the editing, research and review profiles under the names advertised by
the client. For technical content, add the relevant mathematics or coding
roles. If the surface does not load those roles, pass their instructions to an
available native agent from the resources for
[editing](../../../ecosystem/agents/editor.toml),
[research](../../../ecosystem/agents/researcher.toml),
[review](../../../ecosystem/agents/reviewer.toml),
[mathematics](../../../ecosystem/agents/mathematician.toml) or
[coding](../../../ecosystem/agents/coder.toml), as appropriate. Inherit model,
reasoning effort and permissions; do not assume tools that the session does
not expose.

Each delegated task specifies scope, files, result and expected evidence, as
well as relevant skills and their accessible location. The agent checks its
catalogue and loads only the necessary instructions; a coordinator's capability
may be unavailable to that agent. Register contributors' actual native
identities before review. A role name or task ID does not identify the actual
author.

## Sources and claims

In factual writing, identify claims whose falsity would change the argument
or a reader's decision. Also check included quotations, figures and
attributions. Seek primary sources when they exist and are relevant; for
changing facts, verify the applicable version or date. A source's general
authority does not establish that it supports a specific sentence.

Link each essential claim to the part of the source supporting it and check
its scope: population, period, definition, unit, assumptions, uncertainty and
the distinction between correlation and causation where appropriate.
A review can help locate a source, but does not amount to reading the original.
A title, abstract or search result likewise does not justify attributing
conclusions to a full text that you have not checked.

Retain traceability proportional to the document, using notes or a brief record
of claim, source, location, check and limitation. If it must be a durable
artifact, declare it in scope; do not add an auxiliary file routinely.
In the final text, place references alongside what they support and apply the
requested citation style. Verify authors, title, date, URL or DOI when included;
do not fill bibliographic gaps by conjecture. Preserve the meaning and context
of quotations and respect reproduction limits.

If support is missing, choose according to the task: leave a question explicitly
pending in a research draft, qualify it as a hypothesis or inference, or remove
the claim. Do not turn a missing source into proof or hide the gap with an
invented reference. If the absence prevents fulfillment of an essential
requirement, deliver the partial state and its consequence clearly.
Do not claim an exhaustive review after checking only a sample.

## Explaining from first principles

The question determines how far back the explanation needs to go. Before
performing an operation, establish the entities involved, the relationships
defined between them and the data that make the operation meaningful. Give
the reason for each construction at the point where the reader needs it.
A definition specifies an object. The existence of an object satisfying a
condition, its uniqueness and its independence from a choice each require
their own justification.

Carry one example through two changes the reader might confuse. In a
finite-dimensional real vector space, changing basis can change the components
that describe a vector and a linear functional. Evaluating the same functional
on the same vector gives the same scalar. Choosing an inner product adds
another operation. It lets us represent the functional by the vector whose
inner product with each argument gives its value. Doubling the inner product
halves the representing vector. The functional still returns the same values.
This variation shows precisely what depended on the geometry. The
[ontology](../../../ecosystem/references/ontology.md) and its
[examples](../../../ecosystem/references/ontology-examples.md) develop the
construction and the hypotheses for more general cases.

In other disciplines, use the entities and questions of the subject. A
grayscale image assigns a level to each position. Its histogram counts the
positions at each level. Swapping two pixels of different levels preserves
the counts and changes the image. The counts suffice to calculate the mean
level, but recovering the image requires spatial information. The example
isolates the information lost by the representation and shows why that loss
matters to a particular question.

Before displaying a formula, explain the relationship it is meant to express.
Afterwards interpret what the formula lets the reader conclude. When a result
requires new assumptions, identify the precise step that uses them. An
intuition earns its place when the reader can use it to reconstruct the
argument. Honor the requested order of presentation and give a subtlety room
when resolving it changes how the reader understands or uses the conclusion.

## Technical content and mixed deliverables

For an essential mathematical argument, verify the hypotheses, types,
quantifiers and steps supporting the conclusion; distinguish proof, numerical
computation, approximation and conjecture. Use `mathematics` if available and
appropriate to the work. For essential computational results, verify inputs,
versions, execution and relevant behavior; use `coding` when available.
Do not describe a code example as executed when you have merely read it.
The absence of a specialized skill does not remove the obligation to verify
content or authorize pretending to have tools or results.

Determine dependencies by the result: drafting conclusions waits for
mathematical and computational evidence; research or independent sections can
advance in parallel with separate writers. Do not load skills unrelated to
the task or repeat every lifecycle for each selected skill. In the existing
report, it is enough to state which capability was used, for what purpose,
with what evidence and what failed; do not create a separate selection record
or save conversations.

In a report containing text, proof and code, declare the obligations appropriate
to each deliverable and, if they share a file, to each requirement in that file.
Editorial review checks clarity and attribution; mathematical review checks
the proof; software tests check behavior. One kind of evidence does not
discharge the other obligations. Also check that the text does not attribute
a broader conclusion to the proof or experiment than they actually support.

## Integration, review and final format

Review coverage, thesis, order, continuity of argument, omissions and material
objections first. Then adjust precision, voice, rhythm and length. The integrator
removes repetition and contradictions between contributions and checks claims
affected by integration again.

Compare opening, development and conclusion as one argument, with compatible
definitions, hypotheses and scope. Check which cases absolute terms such as
“only” or “always” apply to. Do not turn an equality or theoretical property
into a stronger or empirical conclusion without justifying the connection
and checking the necessary additional hypotheses.

Every significant delivery undergoes independent review proportional to risk
and with the common protocol's current coverage. Give the reviewer the
requirements, current files, relevant evidence and engine token where
appropriate. They must assess the actual result independently of its author,
including clarity, structure, voice, accuracy and the limits of conclusions.
For an explanation, check whether the reader can say what each object is,
derive the particular case from the general framework and reconstruct the
decisive step without mentally supplying a missing premise. Correcting those
gaps provides evidence of understanding; counting symbols or headings does
not. Record concrete findings and resolve them with evidence; later changes
require renewing affected checks and review. The lack of available reviewers
is a limitation, not implicit approval.

Mechanically check what can be observed: length, resolving references,
reproducible calculations or file integrity, according to the task. A word
counter does not assess clarity, a URL that opens does not support a claim,
and a hash does not establish editorial quality. Retain substantive judgment
and record only checks actually performed.

When Word, PDF or slides are requested, load the available document, PDF or
presentation skill, respectively. Use its tools and rendering workflow;
inspect the final result, including tables, formulas, citations, page breaks
and clipped text. Correct what is observed and recheck the affected parts.
Do not claim to have inspected a nonexistent render or create placeholder
files to simulate a conversion. If a necessary capability is missing, explain
the format limitation and deliver usable content you have completed without
presenting it as the requested file.

Deliver the requested text or files and a brief explanation of what changed,
how it was checked and what remains pending if anything limits the result.
Publication or sending to third parties follows the task's authorization and
the project's workflow; completing a draft grants no additional permissions.
