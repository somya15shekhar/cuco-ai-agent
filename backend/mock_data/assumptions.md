# assumptions.md
## DuCO-Agent Mock Insurance Data — Assumptions, Rationale, and Sources

All JSON files in this directory are fictional. Real insurer names are not used. Values are derived from publicly available Indian health insurance policy documents and IRDAI regulations as of July 2025.

---

## Primary Sources Used

| Source | URL | Used For |
|---|---|---|
| IRDAI Master Circular on Health Insurance Business, 29 May 2024 | https://irdai.gov.in/documents/37343/365525/ | COB rules, cashless timelines, claim settlement rules, waiting periods |
| IRDAI Health Dept FAQ (multiple policies) | https://irdai.gov.in/health-dept | COB primary/secondary insurer rules, benefit vs indemnity policy distinction |
| IRDAI (Insurance Products) Regulations, 2024 | https://www.mondaq.com/india/insurance-laws-and-products/1512658/irdai-insurance-products-regulations-2024 | Product design principles, mandatory exclusions, OOP rules |
| IRDAI Revised Master Circular, Sep 2024 | https://insureiq.in/irdai-revised-master-circular-on-insurance-policies/ | Policyholder's right to choose primary insurer for multiple policy claims |
| HDFC ERGO Optima Secure Policy Wording (UIN: HDFHLIP25011V052425) | https://ditto-partners.s3.ap-south-1.amazonaws.com/HDFC+Ergo/Optima+Super+Secure-Policy+wording.pdf | Deductible types, copay definition, aggregate deductible, exclusions |
| HDFC ERGO Optima Secure Prospectus | https://www.hdfcergo.com/docs/default-source/downloads/prospectus/health/my-optima-secure-prospectus.pdf | Post-hospitalisation benefits, PT coverage window, pre-auth procedure |
| HDFC ERGO Optima Secure CIS (UIN: HDFHLIP24092V032324) | https://www.hdfcergo.com/docs/default-source/downloads/policy-wordings/health/cis---myoptimasecure.pdf | Copay for senior citizens, room rent at non-network |
| Beshak.org — HDFC ERGO Optima Secure Review (April 2026) | https://www.beshak.org/insurance/health-insurance/best-health-insurance-plans/hdfc-ergo-optima-secure/ | Deductible options (₹25k to ₹3L), no sub-limit on joint replacement, no copay below 60 |
| Beshak.org — Niva Bupa ReAssure 2.0 Review (April 2026) | https://www.beshak.org/insurance/health-insurance/best-health-insurance-plans/niva-bupa-re-assure-2-0-platinum/ | No copay base plan, ICU coverage, OOP structure |
| Niva Bupa ReAssure 3.0 Product Page | https://www.nivabupa.com/family-health-insurance-plans/reassurev3-insurance.html | Pre-auth 30-minute commitment, restoration benefit |
| Niva Bupa Copay Page | https://www.nivabupa.com/health-insurance/copay-health-insurance.html | Copay definition, non-network copay structure |
| Policybazaar — HDFC ERGO Optima Secure | https://www.policybazaar.com/insurance-companies/hdfc-ergo-health-insurance/optima-secure-plan/ | Premium reduction with deductible, deductible waiver after 5 renewals |
| Policybazaar — Niva Bupa vs Star Comparison | https://www.policybazaar.com/health-insurance/comparison/max-bupa-health-reassure-vs-star-comprehensive/ | Copay 10% for non-network, network vs non-network reimbursement |
| ManipalCigna — IRDAI Claim Guidelines | https://www.manipalcigna.com/blog/latest-irda-guidelines-for-health-insurance | 30-day settlement timeline, 2% interest on delays, documents required |
| HDFC ERGO — IRDAI Guidelines Blog | https://www.hdfcergo.com/blogs/health-insurance/irdai-health-insurance-guidelines-updates | PED waiting period max 3 years, moratorium 5 years |

---

## Assumption Log

### 1. Deductible Type and Amount

**Plan A (Insurer1): ₹50,000 aggregate annual deductible**
- Assumption: Voluntary aggregate deductible of ₹50,000 chosen.
- Why: HDFC ERGO Optima Secure offers aggregate deductible options of ₹25k, ₹50k, ₹1L, ₹2L, ₹3L. ₹50,000 is the most commonly selected mid-range option for a ₹10L sum insured policy, reducing premium by ~30-40% while maintaining meaningful coverage for large claims like ACL surgery.
- Source: Beshak.org HDFC ERGO Optima Secure review (April 2026). HDFC ERGO policy wording Section B-2.7.

**Plan B (Insurer2): ₹25,000 per-claim deductible**
- Assumption: Per-claim (not aggregate) deductible of ₹25,000.
- Why: Mid-tier plans from Niva Bupa and Star Health often use per-claim deductibles rather than aggregate. ₹25,000 represents a mid-range value for a ₹5L sum insured policy. Per-claim deductible makes Plan B slightly less favourable for multiple claims in a year but more predictable per episode.
- Source: Niva Bupa ReAssure policy structure. Representative value from Policybazaar plan comparison data.

---

### 2. Coinsurance Percentages

**Plan A: 80% insurer / 20% patient**
- Assumption: Standard 80/20 coinsurance split.
- Why: 80/20 is the predominant coinsurance split in premium-tier comprehensive Indian health plans (HDFC ERGO, Care Supreme, ICICI Lombard Complete Health). Reflects a balance between premium affordability and patient cost-sharing.
- Source: Beshak.org plan comparisons. HDFC ERGO Optima Secure policy wording.

**Plan B: 75% insurer / 25% patient**
- Assumption: 75/25 split.
- Why: Mid-tier plans with lower sum insured often have slightly lower insurer share to price premiums competitively. 75/25 is representative of Star Health Comprehensive and Care Advantage plan structures. Differentiates Plan B from Plan A.
- Source: Policybazaar Star Health Comprehensive and Care Health plan data.

---

### 3. Co-payment

**Plan A: No co-payment (members under 60)**
- Assumption: Zero co-payment for standard-age members at network hospitals.
- Why: HDFC ERGO Optima Secure explicitly has no co-payment clause for members below 60. No co-payment is a premium-plan feature that attracts buyers.
- Source: Beshak.org: "The HDFC ERGO Optima Secure plan does not have a copayment limit." HDFC ERGO CIS document.

**Plan B: 10% co-payment at non-network hospitals**
- Assumption: 10% co-payment triggered only at non-network hospitals.
- Why: A common structure in mid-tier plans to encourage network hospital usage. Niva Bupa and Star Health use this mechanism. 10% is the standard rate seen across multiple product comparisons.
- Source: Policybazaar comparison data. Niva Bupa copay explainer page.

**Both plans: 20% co-payment for senior citizens (60+)**
- Assumption: Added senior citizen copay as mandatory disclosure item.
- Why: Many Indian plans add co-payment clauses for senior members to manage claims costs. 20% is the most common rate. IRDAI guidelines require transparent disclosure of copay terms.
- Source: HDFC ERGO CIS document (mandatory copay disclosure section). IRDAI Master Circular 2024 on transparent disclosure.

---

### 4. Out-of-Pocket Maximum

**Plan A: ₹2,00,000 | Plan B: ₹1,50,000**
- Assumption: OOP maximums modelled on premium and mid-tier plan structures.
- Why: IRDAI does not mandate OOP caps in indemnity plans (unlike the US ACA mandate). However, several Indian plans (Care Supreme, ICICI Lombard Health Advantage) include OOP caps as a differentiation feature. Amounts are proportional to sum insured: ₹2L cap on ₹10L sum insured (20%) and ₹1.5L on ₹5L (30%).
- Source: Care Health and ICICI Lombard plan product pages. IRDAI (Insurance Products) Regulations 2024 allow but do not mandate OOP caps.
- Risk flag: This field may not exist in many real Indian policies. In a real system, remove OOP max if the actual policy document does not include it.

---

### 5. Physical Therapy Coverage

**Sub-limit: Plan A ₹30,000 (90 days) | Plan B ₹20,000 (60 days)**
- Assumption: PT is covered only as a post-hospitalisation benefit, not as standalone OPD.
- Why: Indian health insurance policies generally do not cover outpatient physiotherapy as a standalone benefit in base plans. PT is covered under post-hospitalisation expenses when linked to a prior admission. HDFC ERGO Optima Secure covers post-hospitalisation expenses up to 180 days; sub-limit of ₹30,000 is representative of orthopaedic PT claims from Star Health and Care Health policy data.
- Source: HDFC ERGO Optima Secure Prospectus (post-hospitalisation up to 180 days). Star Health Comprehensive PT sub-limit data from Policybazaar. Plan B 60-day window modelled on Star Health standard plan.

**CPT codes 97161 and 97110 mapped to physiotherapy**
- Assumption: CPT codes used for Indian context.
- Why: India does not mandate CPT codes domestically; treatment descriptions and ICD-10 codes are standard. CPT codes are included in this project because the use case involves a dual-coverage scenario with international code conventions. Codes 97161 (PT evaluation, high complexity) and 97110 (therapeutic exercises) are the most common PT codes for post-surgical knee rehabilitation.
- Source: American Medical Association CPT codebook. Used as proxy for Indian physiotherapy billing descriptions in this project context.

---

### 6. ACL Reconstruction and Meniscectomy Coverage

**CPT codes 29888 and 29881 — both covered after 24-month waiting period**
- Assumption: 24-month waiting period for pre-existing orthopaedic conditions.
- Why: IRDAI 2024 regulations reduced the maximum PED waiting period from 4 years to 3 years. Many insurers apply a 24-month (2-year) waiting period for specific listed procedures like joint surgeries. Acute injury (no prior diagnosis) covered from day 1. 24 months chosen as representative of HDFC ERGO and Niva Bupa practices.
- Source: IRDAI Master Circular 2024: max PED waiting period 36 months. Policybazaar IRDAI guidelines article: joint replacement surgery waiting period reduced to 3 years.

---

### 7. COB — Primary/Secondary Insurer Assignment

**Aarav: Plan B primary, Plan A secondary**
- Assumption: Aarav selects Plan B as primary for his ACL surgery claim.
- Why: For a single large claim of ₹4.5L, Plan B's per-claim deductible of ₹25,000 is lower than Plan A's aggregate deductible of ₹50,000. Using Plan B as primary maximises the amount covered by the primary insurer, leaving a smaller residual for Plan A. This is the financially optimal choice.
- Source: IRDAI revised Master Circular Sep 2024: policyholder has the right to choose any active indemnity policy as primary. Source: https://insureiq.in/irdai-revised-master-circular-on-insurance-policies/

**Priya: Plan A primary, Plan B secondary**
- Assumption: Priya selects Plan A as primary for her PT claim.
- Why: Plan A has a higher PT sub-limit (₹30,000 vs ₹20,000) and longer post-discharge window (90 vs 60 days). As Plan A primary, Plan A pays more of Priya's PT bill. Plan B as secondary would receive only the residual, which may fall below Plan B's ₹25,000 per-claim deductible (as shown in worked example).

---

### 8. Secondary Insurer Deductible Application

**Plan B's deductible applied to residual balance when acting as secondary**
- Assumption: When Plan B acts as secondary insurer, its ₹25,000 per-claim deductible is applied to the residual balance passed from Plan A, not to the original total claim.
- Why: This is the standard interpretation under IRDAI's contribution clause and indemnity principle. The secondary insurer applies its own policy terms to the balance amount. The secondary insurer does not re-apply deductibles to amounts already settled by the primary.
- Source: IRDAI Health Dept FAQ: "In case the available coverage under the said policy is less than the admissible claim amount, the primary Insurer shall coordinate with other Insurers to ensure settlement of the balance amount as per the policy conditions." (https://irdai.gov.in/health-dept). No-profit principle under indemnity insurance.

---

### 9. Network Hospital Counts

**Plan A: 10,000+ hospitals | Plan B: 8,000+ hospitals**
- Assumption: Representative network sizes.
- Why: HDFC ERGO has 13,000+ network hospitals; Niva Bupa has 10,000+; Star Health has 14,000+. 10,000 for Plan A (premium tier) and 8,000 for Plan B (mid-tier) are conservative, realistic figures that differentiate the plans without using real insurer data.
- Source: Niva Bupa website (10,000+). Beshak.org plan data (April 2026).

---

### 10. Claim Settlement Timeline

**Both plans: 30 days**
- Assumption: 30-day settlement period for both insurers.
- Why: IRDAI mandates that health insurance claims be settled or rejected within 30 days of receiving all required documents. This is a regulatory floor, not an insurer choice.
- Source: ManipalCigna IRDAI guidelines: "Claims must be settled or rejected within 30 days." https://www.manipalcigna.com/blog/latest-irda-guidelines-for-health-insurance

---

### 11. Interest on Delayed Claims

**Both plans: 2% above bank rate**
- Assumption: Standard interest penalty for insurer delays.
- Why: IRDAI mandates that if an insurer delays settlement beyond 30 days without valid reason, it must pay interest at 2% above the prevailing bank rate.
- Source: ManipalCigna blog on IRDAI guidelines. IRDAI Master Circular on Protection of Policyholders' Interests 2024.

---

### 12. ICD-10 and CPT Codes

**ICD-10 M23.619 (ACL tear), M23.200 (meniscus damage)**
- Assumption: Standard ICD-10 codes used as clinical identifiers.
- Why: M23.619 is the ICD-10-CM code for "other spontaneous disruption of anterior cruciate ligament of unspecified knee." M23.200 covers meniscus derangement. These are universally recognised and appropriate for the clinical scenario described.
- Source: ICD-10-CM 2024 codebook. Used as international standard reference.

---

## What This Data Does NOT Model

1. GST on health insurance premiums (18% GST applies to Indian health insurance premiums — not relevant for claim calculation).
2. TPA (Third Party Administrator) fees — modelled as in-house settlement for simplicity.
3. Room rent proportionate deductions — common in older Indian policies where room rent upgrade triggers proportionate claim reduction. Not modelled as both plans are assumed to have no room rent sub-limits at network hospitals.
4. Sub-limits on specific disease categories (e.g., cataract sub-limits common in older plans). Not modelled as both plans are premium/mid-tier without such caps on orthopaedic procedures.
5. Portability benefit accumulation across previous policies.
6. Zone-based pricing (some insurers charge different premiums for Zone 1 / Zone 2 cities).

---

## Disclaimer

This data is fictional and created for an AI/agentic systems educational project. It is not financial or insurance advice. For real insurance decisions, consult IRDAI-registered insurance advisors and read original policy documents available at:
- IRDAI website: https://irdai.gov.in
- HDFC ERGO: https://www.hdfcergo.com
- Niva Bupa: https://www.nivabupa.com
- Star Health: https://www.starhealth.in
