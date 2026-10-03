# Caveman Style

Why use many token when few do trick.

## Where it applies

**Everything travelling to or from a subagent** — the brief going out, the report coming back.
Both directions, same style.

⛔ **Never a reply to the user.** Those follow `CLAUDE.md` § Langue and § Comportement.

## Rules

- Drop filler, pleasantries, preamble
- Fragments > complete sentences
- Substance only, no fluff
- Say it once — a rule written twice drifts without anything flagging it

## Never compress

- File paths and line numbers
- Exact error output
- The command that was run
- Branch names, PR URLs, ticket keys
- **Security warnings — full sentences, always**

Losing any of these costs a round-trip to ask again, which is more expensive than the words
saved. A security warning reduced to fragments loses the qualifier that made it actionable.

## Output format

**Each agent carries its own block, in its own declaration.** Not here: one form for five roles
would fit none of them.

## Examples

**Outbound — a brief**

> *Normal:* "I'd like you to have a look at the Bourg component and see whether the enclosure
> could be made less circular. Right now it draws a plain circle, and ideally we'd have something
> more irregular, with some rooftops inside it."
>
> *Caveman:* `BUT: le bourg cesse d'être un disque — enceinte irrégulière + toits dedans.`

**Inbound — a report**

> *Normal:* "I've finished the work. I modified the city_plan.tsx file to implement the changes
> you asked for, and I ran the linter, which passed without any issues, and the typechecker also
> came back clean."
>
> *Caveman:*
> ```
> STATUS: done
> CHANGED: inertia/components/city_plan.tsx
> VERIFIED: lint + typecheck verts
> ```
