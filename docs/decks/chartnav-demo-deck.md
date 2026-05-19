# ChartNav Demo Deck — Index

> The demo deck is **split into two**. Pick the right one for
> the audience:
>
> - **`chartnav-buyer-demo-deck.md`** — slides used **during** the
>   live ChartNav demo with a buyer (practice, advisor, partner).
>   No terminal commands, no repo paths, no operator-only
>   references. **13 slides** describing what the buyer sees —
>   covers the ophthalmology lane cycle, role-based dashboards,
>   retina + glaucoma tracking, imaging metadata pipeline, OD/OS
>   retinal workflow, internal coordination, and the
>   ophthalmology-specific non-goals.
> - **`chartnav-operator-demo-deck.md`** — **internal-only** deck
>   the operator uses to rehearse the demo. Boot, reset,
>   pre-flight checklist (now 9 rows), click path (now 14 steps
>   covering Phase 20C / 21A / 21B), fallback plan, tear-down.
>   8 slides. **Never present this deck to a buyer.**

**Audience:** anyone selecting which demo deck to present.
**Purpose:** route to the right deck for the audience without
risking accidentally showing internal terminal commands during a
buyer meeting.
**CTA / next step:** open the deck listed in the routing table
below — buyer demo for buyer meetings, operator demo for
internal rehearsal.

---

## When to use which

| Situation | Use this deck |
|---|---|
| Sales meeting with a practice owner, clinical champion, or compliance lead | `chartnav-buyer-demo-deck.md` |
| Investor / advisor walkthrough that includes a live demo | `chartnav-buyer-demo-deck.md` |
| Partner / agency demo for a referral conversation | `chartnav-buyer-demo-deck.md` |
| Operator pre-flight rehearsal before a buyer meeting | `chartnav-operator-demo-deck.md` |
| Onboarding a new operator (Maria training Jean-Max's understudy, future hires, partner agency runner) | `chartnav-operator-demo-deck.md` |
| Triaging a broken demo environment | `chartnav-operator-demo-deck.md` |

## Companion documents (both decks)

- **What to say (Phase 6→11 narration)** — `docs/demo/chartnav-clinical-workflow-demo-script.md`
- **What to say (Phase 20C / 21A / 21B narration)** — `docs/demo/chartnav-ophthalmology-demo-script.md`
- **What to click** — `docs/demo/chartnav-demo-click-path.md` *(Phase 21C addendum covers the new dashboards / tracking / imaging surfaces)*
- **What to capture** — `docs/demo/chartnav-video-clip-shot-list.md`
- **Operator guide** — `docs/demo/chartnav-demo-operator-guide.md`
- **Demo environment** — `docs/demo/chartnav-demo-environment.md`
- **Pre-demo checklist** — `docs/commercial/demo-package/chartnav-demo-review-checklist.md`
- **Troubleshooting** — `docs/commercial/demo-package/chartnav-local-demo-troubleshooting.md`
- **Approved language (master)** — `docs/commercial/chartnav-approved-claims-language.md`
- **Ophthalmology language guide** — `docs/commercial/chartnav-ophthalmology-positioning-language-guide.md`

## Safety

Both decks obey the same safe-claims contract at
`docs/commercial/chartnav-approved-claims-language.md` and the
ophthalmology language guide at
`docs/commercial/chartnav-ophthalmology-positioning-language-guide.md`.
ChartNav is provider-reviewed workflow support — no autonomous
diagnosis, no auto-grading of DR severity, no auto-interpretation
of OCTs, no auto-determination of cup-to-disc ratio, no IOL power
selection, no anti-VEGF dosing recommendation, no automatic
orders / coding / referrals / patient messaging, no certified-EHR
replacement claim, no current vendor adapter for Cirrus /
Spectralis / Triton / Optos / IOLMaster / Humphrey / Topcon.
Demos run against fake patient data only.
