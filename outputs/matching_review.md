# Which inguinal repairs can be compared?

These 19 fictional operations each represent a different patient at one fictional hospital. All procedures were outpatient, with discharge on the surgery date.

## A routine label hides a recurrent repair

The operative label for **G19** reads “Elective laparoscopic inguinal repair”. Account V19 on 2025-05-03 carries ICD-10-CM K40.91 and CPT 49651. The screen records **excluded recurrent repair**. The label admits 19 candidates. Same-day billing evidence retains 18.

This fixture screens for initial repairs using CPT 49650 and diagnosis K40.90. Either recurrent code (49651 or K40.91) excludes the operation. Other code combinations require review. Billing rows join on account and service date. G01 has a later billing row on the same account, so only its index-date codes enter the screen.

## How much follow-up do the comparable patients have?

Match within each surgeon and operated side. Each patient received one implant. A dated catalog price is required for the price column. The final column also requires a recorded inpatient return on days 1–30 or observation through day 30. A missing or short event-free record has unknown return status.

| Surgeon | Side | Eligible A / B | Potential pairs | Both priced | Both priced with 30-day outcome |
|---|---|---:|---:|---:|---:|
| Birch | left | 4 / 1 | 1 | 1 | 0 |
| Birch | right | 1 / 0 | 0 | 0 | 0 |
| Cedar | left | 2 / 2 | 2 | 2 | 2 |
| Cedar | right | 3 / 5 | 3 | 2 | 1 |

The smaller arm sets the maximum number of one-to-one pairs in each group. Together the groups support **6** eligible pairs, **5** priced pairs and **3** pairs with both a price and an observable 30-day outcome.

| Mesh | Observed returns / priced patients in shared follow-up groups | Possible returns among selected pairs |
|---|---:|---:|
| MESH-A | 0 / 3 | 0–0 |
| MESH-B | 1 / 5 | 0–1 |

G04 has a documented inpatient return on day 8. The range counts how many observed events could enter a maximum-size pairing, allowing any eligible choice within each group. No individual pairs have been assigned.

The [case audit](coded_cases.csv) shows the codes, price and outcome used for each patient.
