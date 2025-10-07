# Marketing & Finance Analytics Pipeline

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

**Pipeline Overview**

1. **Raw Data Sources**
   - Google Ads (Search, YouTube)
   - Meta Ads (Facebook, Instagram)

2. **001_consolidated_ads_daily**
   - Combines Google + Meta into a unified daily table  
   - Standardizes columns: `date`, `channel`, `campaign_id`, `ad_id`, `spend`, `new_customers`, `conversions`, `conversion_value`

3. **002_monthly_channel_summary**
   - Aggregates daily spend & new customers by cohort month and channel  
   - Calculates **Customer Acquisition Cost (CAC)** = `spend / new_customers`

4. **003_monthly_cohorts**
   - Joins retention and ARPU templates  
   - Calculates **active customers**, **revenue**, **COGS**, **gross profit**, and **contribution margin**

5. **004_ltv_cac**
   - Summarizes cumulative contribution margin to derive **LTV per customer**  
   - Calculates **LTV/CAC** and **Payback Month** for each channel

6. **005_channel_campaign_monthly_pnl**
   - Campaign-level monthly P&L  
   - Includes **spend**, **ROAS**, **CAC_campaign**, **LTV per customer**, **LTV dollars**, and **Net Value Created**

7. **Final Dashboards & Reports**
   - Mode Analytics dashboard visualizing key metrics:
     - **LTV/CAC by Channel**
     - **Cohort Payback Curve**

---

## Findings
**Meta & YouTube drive faster ROI**
* Google YouTube cohorts reach payback in ~4 months with LTV/CAC ~4.3×, generating the strongest near-term ROI.
* Google Search shows slower payback (~28 months) and lower LTV/CAC ~1.7×, suggesting budget reallocation.
* **Recommendation**: Shift 10–15% of spend from Search into Meta and YouTube, which together deliver faster returns.

## Mode Report
[View Full Report on Mode](https://app.mode.com/castillo/reports/87a511823fba/runs/7e9dd33e3080)

If you don’t have Mode access, a static copy is included here:

📄 [Download Dashboard PDF](reports/marketing_dashboard.pdf)

🖼️ Preview Screenshot:  
![Marketing Finance Dashboard](reports/marketing_dashboard_preview.png)
