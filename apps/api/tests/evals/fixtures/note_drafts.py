"""Fake clinical note drafts used by the safety eval harness.

Every string here is invented. No PHI. No real patient names. No
real provider names. Used only to keep the safety linter honest
against the cases that motivated the linter in the first place.
"""

# A clean OD-laterality retina note. Expected: no block, completeness ≈ 100.
CLEAN_RETINA_OD = """\
Chief complaint: floaters OD x 4 days.
History: 62yo F, no trauma, no PMH of retinal disease.
Exam: VA OD 20/30. DFE OD: PVD without tear.
Imaging review: OCT OD unremarkable; macula intact.
Assessment: Acute symptomatic PVD OD without retinal tear.
Plan: Re-exam in 2 weeks; return precautions reviewed.
"""

# Laterality mismatch: encounter is OD, draft talks about OS.
LATERALITY_CONFLICT_OS_IN_OD_VISIT = """\
Chief complaint: floaters OS x 4 days.
History: 62yo F, no trauma, no PMH of retinal disease.
Exam: VA OS 20/30. DFE OS: PVD without tear.
Imaging review: OCT OS unremarkable.
Assessment: PVD OS without retinal tear.
Plan: Re-exam in 2 weeks.
"""

# Banned-phrase example.
BANNED_AUTODX = """\
Chief complaint: vision loss OD.
History: 1 week.
Exam: OCT findings consistent with edema.
Imaging review: macular edema OD.
Assessment: autonomous diagnosis pending review.
Plan: refer to retina.
"""

# Duplicate Plan section — should warn once.
DUPLICATE_PLAN = """\
Chief complaint: itch OU.
History: 2 days.
Exam: lids clear.
Assessment: allergic conjunctivitis.
Plan: artificial tears.
Plan: f/u 1 week.
"""

# Empty draft.
EMPTY = ""

# Draft asserting a finding that the extracted-findings layer negates.
CONTRADICTION_DRAFT = """\
Chief complaint: floaters OS.
History: 3 days.
Exam: peripheral retinal detachment noted.
Imaging review: OCT OS shows attached macula.
Assessment: retinal detachment OS.
Plan: urgent retina referral.
"""
CONTRADICTION_EXTRACTED = "No retinal detachment on exam."
