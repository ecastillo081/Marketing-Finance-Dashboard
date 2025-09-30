# Marketing → Finance Analytics Pipeline

## Overview
This project translates Google Ads + Meta Ads marketing data into finance KPIs:
- Customer Acquisition Cost
- Long Term Value per customer
- Payback months
- Return on Ad Spend
- Net Value Created

**Goal**: give finance & strategy teams actionable insight into where to allocate budget across channels/campaigns.

---

## Data Flow
```mermaid
  Raw: Daily Ad Data (Google + Meta) 
  Raw --> A[001_consolidated_ads_daily]
  A   --> B[002_monthly_channel_summary]
  B   --> C[003_monthly_cohorts]
  C   --> D[004_ltv_cac]
  D   --> E[005_channel_campaign_monthly_pnl]
  E   --> F[Final Dashboards & Reports]
```  
## Findings
**Meta & YouTube drive faster ROI**
* Google YouTube cohorts reach payback in ~4 months with LTV/CAC ~4.3×, generating the strongest near-term ROI.
* Google Search shows slower payback (~28 months) and lower LTV/CAC ~1.7×, suggesting budget reallocation.
* Google Search shows slower payback (~28 months) and lower LTV/CAC ~1.7×, suggesting budget reallocation.