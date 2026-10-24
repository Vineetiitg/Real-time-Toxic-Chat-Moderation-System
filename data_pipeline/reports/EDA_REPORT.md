# SafeChat Data Pipeline — EDA Report

**Total Samples:** `37246`  
**Generated:** `2026-10-21 23:27:59`

---

## 1. Source Distribution

| Source | Count | Percentage |
|---|---|---|
| `english (jigsaw)` | 14614 | 39.2% |
| `english` | 8958 | 24.1% |
| `hindi` | 5860 | 15.7% |
| `hindi/hinglish (hasoc)` | 4889 | 13.1% |
| `hinglish` | 2881 | 7.7% |
| `hinglish (curated)` | 27 | 0.1% |
| `hindi_devanagari (curated)` | 15 | 0.0% |
| `english (curated)` | 2 | 0.0% |

## 2. Class Distribution & pos_weight

| Tag | Positives | Negatives | Rate | pos_weight |
|---|---|---|---|---|
| **toxic** | 19239 | 18007 | 51.65% | `1.0` |
| **severe_toxic** | 1497 | 35749 | 4.02% | `23.88` |
| **obscene** | 8242 | 29004 | 22.13% | `3.52` |
| **threat** | 477 | 36769 | 1.28% | `25.0` |
| **insult** | 17033 | 20213 | 45.73% | `1.19` |
| **identity_hate** | 2489 | 34757 | 6.68% | `13.96` |

## 3. Text Length Statistics

- **Characters:** mean=220.5, median=127.0, p95=690.0, max=1991
- **Words:** mean=38.9, median=24.0, p95=118.0, max=371

## 4. Script Breakdown

- Latin ASCII: `90.9%`
- Devanagari: `8.9%`
- Other: `0.2%`

## 5. Data Quality

- Safe samples (all labels=0): `17383` (46.7%)
- Toxic samples (any label=1): `19863`

