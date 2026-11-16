# JSX and HTML Guidelines

JSX quality and HTML semantics are frontend craft. Code that renders correctly but uses the wrong elements, wraps every node in a meaningless div, or ignores keyboard interaction is not finished work.

---

## JSX composition

### Tree structure

The JSX tree should communicate the structure of the interface. A reader should be able to understand the component hierarchy without running the code.

**Avoid wrapper proliferation.** Every extra element that wraps for layout reasons adds mental overhead. Before adding a `<div>`, ask whether the layout could be achieved by styling the existing parent.

```tsx
// Bad — wrapper layers that add no meaning
<div className="container">
  <div className="inner">
    <div className="content">
      <h2>{title}</h2>
    </div>
  </div>
</div>

// Good — flat, with layout on the outer element
<section className="panel">
  <h2>{title}</h2>
</section>
```

### Fragment hygiene

Use `<>...</>` (fragment shorthand) when a component must return multiple elements without a DOM wrapper. Do not add a wrapping `<div>` just to satisfy "components must return one element" — that is what fragments are for.

When you need to set a key on a fragment, use `<Fragment key={...}>...</Fragment>` explicitly.

### Conditional rendering

Ternaries are readable for simple conditions. For complex conditions, extract the logic before the return:

```tsx
// Readable ternary
{isLoading ? <Spinner /> : <DataTable rows={rows} />}

// Harder to read — extract the logic
{isLoading ? <Spinner /> : hasError ? <ErrorMessage error={error} /> : rows.length === 0 ? <EmptyState /> : <DataTable rows={rows} />}

// Better — named variable
const content = isLoading ? <Spinner />
  : hasError ? <ErrorMessage error={error} />
  : rows.length === 0 ? <EmptyState />
  : <DataTable rows={rows} />;

return <div>{content}</div>;
```

Short-circuit `&&` is idiomatic for "show this if true":
```tsx
{showTooltip && <Tooltip content={label} />}
```

But beware of falsy values — `0 && <Component />` renders `0`, not nothing. Use `!!value && <Component />` or a ternary.

### Prop readability

Long prop lists should be broken across lines, one prop per line:
```tsx
// Unreadable on one line for complex components
<PositionTable rows={positions} onRowClick={handleSelect} sortKey={sort.key} sortDir={sort.dir} />

// Readable
<PositionTable
  rows={positions}
  onRowClick={handleSelect}
  sortKey={sort.key}
  sortDir={sort.dir}
/>
```

Boolean props: `<Component disabled />` is idiomatic for `disabled={true}`. But for clarity on non-obvious props, explicit values are better: `<Component sortDir="asc" />` over `<Component ascending />`.

### View logic vs. domain logic

JSX should orchestrate rendering, not execute business logic. Push calculations and transformations above the return statement or into hooks.

```tsx
// Bad — business logic in JSX
function PositionRow({ position }) {
  return (
    <tr>
      <td>{position.quantity * position.currentPrice - position.quantity * position.avgPrice}</td>
    </tr>
  );
}

// Good — named and extracted
function PositionRow({ position }) {
  const unrealizedPnL = (position.currentPrice - position.avgPrice) * position.quantity;
  return (
    <tr>
      <td>{unrealizedPnL}</td>
    </tr>
  );
}
```

---

## HTML semantics

Using the correct HTML element is not pedantry — it is how the browser knows what something is, which determines keyboard behavior, accessibility tree structure, and default styling.

### Element selection

**Interactive elements:**
- Something the user clicks to perform an action → `<button>`
- Something that navigates → `<a href="...">`
- Never `<div onClick>` or `<span onClick>` — these have no keyboard accessibility, no focus management, and no semantic meaning

**Headings:**
- Section titles are headings (`<h1>`–`<h6>`), not large bold text
- Heading levels reflect document structure, not visual size
- One `<h1>` per page (or region); headings should not skip levels (h1 → h3 without an h2)

**Lists:**
- Navigation links, tabs, items in a menu, and sets of related cards are `<ul>` / `<li>`
- Sequential steps or numbered items are `<ol>` / `<li>`

**Forms:**
- Every input has a `<label>` that is associated via `for`/`htmlFor` or wrapping
- Required fields use the `required` attribute
- Form controls are inside a `<form>` unless there is a specific reason not to (e.g., a single-field filter that submits on change)

**Landmarks:**
- `<nav>` — primary navigation
- `<main>` — the primary content of the page (one per page)
- `<aside>` — supplementary content, sidebars
- `<header>` / `<footer>` — at the document or section level
- `<section>` — a thematic grouping with a heading
- `<article>` — self-contained content that could stand alone (a post, a card, a table row representing a record)

These elements let assistive technology understand the page structure. They cost nothing to use correctly.

### Accessibility fundamentals

**Focus management.** Every interactive element must be reachable via keyboard. The focus order should follow the visual and logical reading order. Do not suppress focus outlines without providing a visible alternative.

**`aria-label` is a last resort.** The preferred order for naming an element:
1. Visible text content (the best option — the label is visible to everyone)
2. Associated `<label>` element
3. `aria-labelledby` pointing to another visible element
4. `aria-label` — only when no visible label exists and one cannot be added

**`role` attributes patch missing semantics.** If you are adding `role="button"` to a `<div>`, use a `<button>` instead. `role` attributes are for cases where the correct element cannot be used (e.g., custom components, framework constraints).

**Image alt text.** Decorative images: `alt=""` (empty, not omitted). Informative images: `alt="description of what the image conveys"`. Icon buttons: the `<button>` gets `aria-label`, the icon gets `aria-hidden="true"`.

**Color is not the only signal.** Do not use color alone to communicate status (error/success/warning). Always pair color with text, icon, or shape.

### Common mistakes

**`<div>` as button:**
```tsx
// Bad
<div className="btn" onClick={submit}>Submit</div>

// Good
<button type="button" onClick={submit}>Submit</button>
```

**`<span>` as heading:**
```tsx
// Bad
<span className="section-title">Positions</span>

// Good
<h2 className="section-title">Positions</h2>
```

**Unlabeled icon buttons:**
```tsx
// Bad
<button onClick={close}><CloseIcon /></button>

// Good
<button onClick={close} aria-label="Close dialog"><CloseIcon aria-hidden="true" /></button>
```

**Input without label:**
```tsx
// Bad
<input type="text" placeholder="Search..." />

// Good
<label>
  Search
  <input type="text" />
</label>

// Or with visually hidden label
<label htmlFor="search" className="sr-only">Search</label>
<input id="search" type="text" placeholder="Search..." />
```

---

## shadcn/ui usage

shadcn/ui components are well-architected primitives. Use them correctly:

- Use the component's intended composition API. `<Dialog>`, `<DialogTrigger>`, `<DialogContent>` — do not reach into the internals to override layout.
- When customizing appearance, use the `className` prop and the design token system. Do not override with inline styles.
- The `asChild` prop renders the component's behavior onto its child element. Use it when you need to combine a button's behavior with a link's rendering (`<Button asChild><a href="...">Go</a></Button>`).
- Do not wrap shadcn/ui components in unnecessary containers. If the component already handles spacing and layout, adding a wrapper div creates redundant nesting.
- Read the component's source before customizing — shadcn/ui ships source into your repo. If the behavior is not right, edit the component directly rather than working around it.
