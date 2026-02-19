#!/usr/bin/env python3
"""
AmbacTracker Pricing Calculator
Run with: streamlit run tools/pricing_calculator_gui.py

Features:
- Pricing estimates with tiered users (full, operator, viewer)
- Margin analysis with Railway SaaS cost model
- Competitor pricing comparison
- ROI calculator for customer justification
- Phased rollout planning (land and expand)
- Pilot/POC pricing scenarios
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json

# =============================================================================
# PRICING CONFIGURATION (Market-validated)
# =============================================================================

USER_PRICING = {
    "lite": {
        "name": "Lite (MES/DMS)",
        "full_user": 75,
        "operator": 35,
        "viewer": 20,
    },
    "standard": {
        "name": "Standard (MES/QMS/DMS)",
        "full_user": 100,
        "operator": 50,
        "viewer": 25,
    },
    "enterprise": {
        "name": "Enterprise (Full Suite)",
        "full_user": 150,
        "operator": 65,
        "viewer": 30,
    },
}

DEPLOYMENT = {
    "saas": {
        "name": "SaaS (Multi-tenant)",
        "user_multiplier": 1.0,
        "platform_fee": 0,
        "annual_discount": 0.10,
        "setup_fee": 0,
        "min_annual": 6000,
        "training_per_user": 500,
        "implementation_weeks": (4, 8),
    },
    "dedicated": {
        "name": "Dedicated Cloud (Single-tenant)",
        "user_multiplier": 1.10,
        "platform_fee": 750,
        "annual_discount": 0.10,
        "setup_fee": 5000,
        "min_annual": 30000,
        "training_per_user": 750,
        "implementation_weeks": (6, 12),
    },
    "airgapped": {
        "name": "Air-gapped (On-prem)",
        "user_multiplier": 1.0,
        "platform_fee": 1500,
        "annual_discount": 0.0,
        "setup_fee": 25000,
        "min_annual": 48000,
        "perpetual_multiplier": 3.0,
        "training_per_user": 1000,
        "implementation_weeks": (8, 16),
    },
    "cmmc": {
        "name": "CMMC Compliant (Air-gapped + Compliance)",
        "user_multiplier": 1.25,
        "platform_fee": 2000,
        "annual_discount": 0.0,
        "setup_fee": 35000,
        "min_annual": 72000,
        "perpetual_multiplier": 3.5,
        "training_per_user": 1000,
        "implementation_weeks": (12, 24),
        "compliance_addons": {
            "ssp_templates": 8000,
            "poam_tracking": 5000,
            "audit_support": 15000,
        },
    },
}

MULTI_YEAR_DISCOUNTS = {
    1: 0.0,
    2: 0.15,
    3: 0.25,
}

# Payment terms with discounts
PAYMENT_TERMS = {
    "annual_prepay": {"name": "Annual Prepay", "discount": 0.10, "terms": "Due on signing"},
    "quarterly": {"name": "Quarterly", "discount": 0.05, "terms": "Net 30"},
    "monthly": {"name": "Monthly", "discount": 0.0, "terms": "Net 30"},
    "net60": {"name": "Net 60 (Enterprise)", "discount": -0.02, "terms": "Net 60"},  # Slight premium for extended terms
}

# Pilot program pricing
PILOT_CONFIG = {
    "duration_days": 90,
    "acv_percentage": 0.15,  # 15% of ACV
    "credit_to_contract": 1.0,  # 100% credited
    "min_pilot_fee": 5000,
    "max_pilot_fee": 25000,
}

# =============================================================================
# COST STRUCTURE (Railway SaaS) - Market-validated Feb 2025
# =============================================================================

# Railway pricing components (actual pricing from railway.com/pricing)
# Sources: https://railway.com/pricing, https://docs.railway.com/reference/pricing/plans
RAILWAY_COSTS = {
    "compute_per_vcpu_month": 20,    # $0.000463/min = ~$20/vCPU/month
    "memory_per_gb_month": 10,       # $0.000231/min = ~$10/GB/month
    "storage_per_gb_month": 0.25,    # PostgreSQL + volumes
    "bandwidth_per_gb": 0.10,        # Outbound (100GB included in Pro)
    "base_platform_fee": 20,         # Pro plan minimum ($20 includes usage credit)
}

# Per-customer infrastructure scaling (SaaS multi-tenant)
# Based on: Django + PostgreSQL + Redis + Celery worker
# Typical stack: 1 vCPU, 2GB RAM base + scaling
INFRA_SCALING = {
    "base_monthly": 25,              # Shared infra allocation per customer (~1 vCPU + 0.5GB)
    "per_user_monthly": 0.50,        # Incremental per active user (compute scaling)
    "per_gb_storage": 0.25,          # Railway storage (consider S3 at $0.023/GB for docs)
    "estimated_gb_per_user": 0.5,    # Avg storage per user (docs, 3D models)
}

# Support & operations costs
# Sources: SaaS Capital benchmarks - median 8% of ARR for support+CS
# https://www.saas-capital.com/blog-posts/spending-benchmarks-for-private-b2b-saas-companies/
SUPPORT_COSTS = {
    "tier1_hourly": 25,              # L1 support cost/hour (loaded)
    "tier2_hourly": 55,              # L2 technical support/hour (loaded)
    "hours_per_customer_month": {
        "small": 0.5,                # <50 users: 30 min/month avg
        "medium": 2.0,               # 50-200 users: 2 hrs/month
        "large": 5.0,                # 200+ users: 5 hrs/month (more complex)
    },
    "customer_success_pct": 0.04,    # 4% of ARR for CS (proactive)
}

# Other COGS components
# Payment processing: Card = 2.9%+$0.30, ACH = 0.8% capped at $5
# For B2B with annual contracts, ACH brings this down significantly
# LLM costs: Claude Sonnet ~$3/M input, $15/M output - estimate 50-100 queries/user/month
OTHER_COGS = {
    "payment_processing_card_pct": 0.029,   # Stripe cards 2.9% + $0.30
    "payment_processing_ach_pct": 0.008,    # Stripe ACH 0.8% (capped $5)
    "stripe_billing_pct": 0.007,            # Stripe Billing platform fee 0.7%
    "monitoring_tools_monthly": 12,         # Datadog/Sentry allocation per customer
    "llm_api_per_user_monthly": 0.50,       # ~$0.50/user/mo for AI features (moderate use)
    "email_transactional_monthly": 3,       # SendGrid/Postmark per customer
}

# Benchmarks for comparison
# Sources: https://www.cloudzero.com/blog/saas-gross-margin-benchmarks/
# https://cfoproanalytics.com/cfo-wiki/saas/gross-margin-targets-for-saas-companies/
MARGIN_BENCHMARKS = {
    "target_gross_margin": (0.75, 0.90),      # 75-90% target (mature SaaS)
    "early_stage_gross_margin": (0.40, 0.60), # 40-60% for pre-$1M ARR
    "good_saas_cogs_pct": (0.10, 0.20),       # 10-20% COGS is excellent
    "median_saas_cogs_pct": 0.28,             # Median at IPO ~28%
    "infrastructure_pct": (0.08, 0.15),       # Infra should be 8-15% of revenue
    "support_pct": 0.08,                      # Support ~8% of revenue (median)
    "best_in_class_support_pct": 0.05,        # Best-in-class <5%
}

# Deal stages for pipeline
DEAL_STAGES = {
    "lead": {"name": "Lead", "probability": 0.10, "color": "gray"},
    "qualified": {"name": "Qualified", "probability": 0.25, "color": "blue"},
    "demo": {"name": "Demo Completed", "probability": 0.40, "color": "orange"},
    "pilot": {"name": "Pilot/POC", "probability": 0.60, "color": "yellow"},
    "proposal": {"name": "Proposal Sent", "probability": 0.75, "color": "green"},
    "negotiation": {"name": "Negotiation", "probability": 0.85, "color": "lightgreen"},
    "closed_won": {"name": "Closed Won", "probability": 1.0, "color": "darkgreen"},
    "closed_lost": {"name": "Closed Lost", "probability": 0.0, "color": "red"},
}

# Buying committee roles
BUYING_COMMITTEE = {
    "quality_manager": {"title": "Quality Manager", "focus": "QMS features, compliance, audit trails"},
    "plant_manager": {"title": "Plant Manager", "focus": "Production efficiency, visibility, ROI"},
    "it_director": {"title": "IT Director", "focus": "Security, integration, deployment"},
    "cfo": {"title": "CFO/Finance", "focus": "Pricing, ROI, payment terms"},
    "operations_vp": {"title": "VP Operations", "focus": "Scalability, multi-site, strategic fit"},
    "procurement": {"title": "Procurement", "focus": "Contract terms, vendor requirements"},
}

# ROI benchmarks
ROI_BENCHMARKS = {
    "copq_percent_revenue": (0.15, 0.25),  # 15-25% of revenue is COPQ
    "copq_reduction": (0.35, 0.50),  # 35-50% reduction possible
    "scrap_rework_percent": (0.01, 0.02),  # 1-2% of revenue
    "labor_efficiency_gain": (0.15, 0.25),  # 15-25% efficiency improvement
    "compliance_cost_annual": (50000, 150000),  # Audit prep, documentation
    "paper_cost_per_employee": (2500, 5000),  # Paper-based process costs
}

ADDONS = {
    "local_llm": {"name": "Local LLM (Air-gapped AI)", "price": 15000},
    "sso": {"name": "SSO/SAML Integration", "price": 6000},
    "api_access": {"name": "API Access (ERP Integration)", "price": 8000},
    "advanced_scheduling": {"name": "Advanced Scheduling (OR-Tools)", "price": 10000},
    "multi_site": {"name": "Multi-site License", "price": 15000},
}

COMPETITORS = {
    "1factory": {"name": "1Factory", "type": "QMS", "per_user": 30, "min_users": 10, "min_annual": 3600},
    "proshop": {"name": "ProShop", "type": "MES/ERP/QMS", "per_user": 70, "min_users": 7, "min_annual": 6000},
    "qt9": {"name": "QT9", "type": "QMS", "min_annual": 1700, "max_annual": 60000},
    "qualio": {"name": "Qualio", "type": "QMS", "platform_fee": 12000, "per_user_annual": 3000},
    "epicor": {"name": "Epicor Kinetic", "type": "ERP/MES", "per_user": 125, "min_users": 10, "min_annual": 15000},
}


# =============================================================================
# CALCULATION FUNCTIONS
# =============================================================================

def calculate_estimate(
    tier: str,
    deployment: str,
    full_users: int,
    operators: int,
    viewers: int = 0,
    addons: list = None,
    contract_years: int = 1,
    payment_term: str = "annual_prepay",
    additional_sites: int = 0,
    include_training: bool = False,
) -> dict:
    """Full pricing calculation."""
    p = USER_PRICING[tier]
    dep = DEPLOYMENT[deployment]
    addons = addons or []
    pay = PAYMENT_TERMS[payment_term]

    # Base user costs
    full_monthly = full_users * p["full_user"]
    operator_monthly = operators * p["operator"]
    viewer_monthly = viewers * p["viewer"]
    base_monthly = full_monthly + operator_monthly + viewer_monthly
    total_users = full_users + operators + viewers

    # Apply deployment multiplier
    adjusted_user_monthly = base_monthly * dep["user_multiplier"]

    # Add platform fee
    total_monthly = adjusted_user_monthly + dep["platform_fee"]

    # Apply minimum
    min_monthly = dep["min_annual"] / 12
    hit_minimum = total_monthly < min_monthly
    if hit_minimum:
        total_monthly = min_monthly

    # Annual calculation
    annual_raw = total_monthly * 12

    # Payment term discount/premium
    payment_adjustment = annual_raw * pay["discount"]
    annual_after_payment = annual_raw - payment_adjustment

    # Multi-year discount (additional)
    multi_year_discount_pct = MULTI_YEAR_DISCOUNTS.get(contract_years, 0)
    multi_year_discount = annual_after_payment * multi_year_discount_pct
    annual = annual_after_payment - multi_year_discount

    # Add-ons
    addon_total = sum(ADDONS[a]["price"] for a in addons if a in ADDONS)

    # Multi-site
    site_total = additional_sites * ADDONS["multi_site"]["price"] if additional_sites > 0 else 0

    # CMMC compliance
    compliance_total = 0
    if deployment == "cmmc" and "compliance_addons" in dep:
        compliance_total = sum(dep["compliance_addons"].values())

    annual_with_addons = annual + addon_total + site_total + compliance_total

    # Training cost (one-time)
    training_cost = 0
    if include_training:
        training_cost = total_users * dep.get("training_per_user", 750)

    # Pilot pricing
    pilot_fee = max(
        PILOT_CONFIG["min_pilot_fee"],
        min(PILOT_CONFIG["max_pilot_fee"], annual_with_addons * PILOT_CONFIG["acv_percentage"])
    )

    # Total contract value
    total_contract_value = annual_with_addons * contract_years
    year_one_total = annual_with_addons + dep["setup_fee"] + training_cost

    return {
        "tier": tier,
        "tier_name": p["name"],
        "deployment": deployment,
        "deployment_name": dep["name"],
        "full_users": full_users,
        "operators": operators,
        "viewers": viewers,
        "total_users": total_users,
        "full_rate": p["full_user"],
        "operator_rate": p["operator"],
        "viewer_rate": p["viewer"],
        "base_monthly": base_monthly,
        "user_multiplier": dep["user_multiplier"],
        "adjusted_user_monthly": adjusted_user_monthly,
        "platform_fee": dep["platform_fee"],
        "total_monthly": total_monthly,
        "hit_minimum": hit_minimum,
        "min_monthly": min_monthly,
        "annual_raw": annual_raw,
        "payment_term": payment_term,
        "payment_adjustment": payment_adjustment,
        "annual_after_payment": annual_after_payment,
        "contract_years": contract_years,
        "multi_year_discount_pct": multi_year_discount_pct,
        "multi_year_discount": multi_year_discount,
        "annual": annual,
        "setup_fee": dep["setup_fee"],
        "training_cost": training_cost,
        "addon_total": addon_total,
        "site_total": site_total,
        "additional_sites": additional_sites,
        "compliance_total": compliance_total,
        "annual_with_addons": annual_with_addons,
        "year_one_total": year_one_total,
        "total_contract_value": total_contract_value,
        "pilot_fee": pilot_fee,
        "implementation_weeks": dep.get("implementation_weeks", (4, 12)),
    }


def calculate_roi(annual_revenue: float, employees: int, current_copq_percent: float = 0.20) -> dict:
    """Calculate potential ROI from implementing the system."""

    # Current costs
    current_copq = annual_revenue * current_copq_percent
    current_scrap_rework = annual_revenue * 0.015  # 1.5% average
    current_paper_cost = employees * 3500  # $3,500/employee for paper processes
    current_compliance_cost = 75000  # Average audit prep/documentation

    # Potential savings (conservative estimates)
    copq_reduction = current_copq * 0.40  # 40% reduction
    scrap_rework_reduction = current_scrap_rework * 0.50  # 50% reduction
    paper_elimination = current_paper_cost * 0.80  # 80% paper reduction
    compliance_reduction = current_compliance_cost * 0.30  # 30% reduction
    labor_efficiency = annual_revenue * 0.005  # 0.5% revenue from efficiency

    total_annual_savings = (
        copq_reduction +
        scrap_rework_reduction +
        paper_elimination +
        compliance_reduction +
        labor_efficiency
    )

    return {
        "current_copq": current_copq,
        "current_scrap_rework": current_scrap_rework,
        "current_paper_cost": current_paper_cost,
        "current_compliance_cost": current_compliance_cost,
        "copq_reduction": copq_reduction,
        "scrap_rework_reduction": scrap_rework_reduction,
        "paper_elimination": paper_elimination,
        "compliance_reduction": compliance_reduction,
        "labor_efficiency": labor_efficiency,
        "total_annual_savings": total_annual_savings,
    }


def calculate_margin_analysis(
    annual_revenue: float,
    total_users: int,
    num_customers: int = 1,
    avg_storage_gb: float = None,
    payment_method: str = "mixed",  # "card", "ach", "mixed"
    ai_usage_level: str = "moderate",  # "light", "moderate", "heavy"
) -> dict:
    """
    Calculate cost structure and margins for SaaS deployment on Railway.

    Args:
        annual_revenue: Total ARR from the customer(s)
        total_users: Total user count across customers
        num_customers: Number of customers (for support scaling)
        avg_storage_gb: Average storage per customer (auto-estimated if None)
        payment_method: "card" (2.9%), "ach" (0.8%), or "mixed" (blend)
        ai_usage_level: "light", "moderate", or "heavy" for LLM API costs
    """
    monthly_revenue = annual_revenue / 12

    # Estimate storage if not provided
    if avg_storage_gb is None:
        avg_storage_gb = total_users * INFRA_SCALING["estimated_gb_per_user"]

    # === INFRASTRUCTURE COSTS (Railway) ===
    # Base shared infrastructure allocation
    infra_base = INFRA_SCALING["base_monthly"] * num_customers

    # Per-user compute scaling
    infra_per_user = total_users * INFRA_SCALING["per_user_monthly"]

    # Storage costs (documents, 3D models)
    storage_cost = avg_storage_gb * INFRA_SCALING["per_gb_storage"]

    # Bandwidth estimate (~2GB/user/month for document-heavy app)
    bandwidth_gb = total_users * 2
    bandwidth_cost = max(0, (bandwidth_gb - 100)) * RAILWAY_COSTS["bandwidth_per_gb"]  # 100GB included

    # Monitoring/observability tools allocation
    monitoring_cost = OTHER_COGS["monitoring_tools_monthly"] * num_customers

    # LLM API costs (scales with users and usage level)
    llm_multiplier = {"light": 0.5, "moderate": 1.0, "heavy": 2.5}.get(ai_usage_level, 1.0)
    llm_cost = total_users * OTHER_COGS["llm_api_per_user_monthly"] * llm_multiplier

    # Email/transactional
    email_cost = OTHER_COGS["email_transactional_monthly"] * num_customers

    total_infra_monthly = (
        infra_base + infra_per_user + storage_cost +
        bandwidth_cost + monitoring_cost + llm_cost + email_cost
    )
    total_infra_annual = total_infra_monthly * 12

    # === SUPPORT COSTS ===
    # Categorize by customer size
    users_per_customer = total_users / max(num_customers, 1)
    if users_per_customer < 50:
        support_hours_per_customer = SUPPORT_COSTS["hours_per_customer_month"]["small"]
    elif users_per_customer < 200:
        support_hours_per_customer = SUPPORT_COSTS["hours_per_customer_month"]["medium"]
    else:
        support_hours_per_customer = SUPPORT_COSTS["hours_per_customer_month"]["large"]

    # Blend of T1 and T2 support (70/30 split)
    blended_support_rate = (
        SUPPORT_COSTS["tier1_hourly"] * 0.7 +
        SUPPORT_COSTS["tier2_hourly"] * 0.3
    )

    support_monthly = (
        num_customers * support_hours_per_customer * blended_support_rate
    )

    # Customer success (proactive, scales with ARR)
    cs_monthly = monthly_revenue * SUPPORT_COSTS["customer_success_pct"]

    total_support_monthly = support_monthly + cs_monthly
    total_support_annual = total_support_monthly * 12

    # === PAYMENT PROCESSING ===
    # B2B SaaS: Annual contracts often paid via ACH (0.8% capped at $5) vs card (2.9%)
    # Stripe Billing adds 0.7% platform fee
    if payment_method == "card":
        payment_pct = OTHER_COGS["payment_processing_card_pct"] + OTHER_COGS["stripe_billing_pct"]
    elif payment_method == "ach":
        # ACH is 0.8% capped at $5 per transaction - for annual contracts, this is minimal
        # Approximate as 0.5% effective for larger contracts
        payment_pct = 0.005 + OTHER_COGS["stripe_billing_pct"]
    else:  # mixed - assume 60% ACH (enterprise), 40% card (SMB)
        card_portion = annual_revenue * 0.4 * (OTHER_COGS["payment_processing_card_pct"])
        ach_portion = annual_revenue * 0.6 * 0.005  # Effective ACH rate
        billing_fee = annual_revenue * OTHER_COGS["stripe_billing_pct"]
        payment_processing_annual = card_portion + ach_portion + billing_fee
        payment_pct = payment_processing_annual / annual_revenue if annual_revenue > 0 else 0

    if payment_method in ["card", "ach"]:
        payment_processing_annual = annual_revenue * payment_pct

    # === TOTAL COGS ===
    total_cogs_annual = (
        total_infra_annual +
        total_support_annual +
        payment_processing_annual
    )

    # === MARGINS ===
    gross_profit = annual_revenue - total_cogs_annual
    gross_margin_pct = gross_profit / annual_revenue if annual_revenue > 0 else 0

    cogs_pct = total_cogs_annual / annual_revenue if annual_revenue > 0 else 0
    infra_pct = total_infra_annual / annual_revenue if annual_revenue > 0 else 0
    support_pct = total_support_annual / annual_revenue if annual_revenue > 0 else 0

    # Per-customer economics
    revenue_per_customer = annual_revenue / max(num_customers, 1)
    cogs_per_customer = total_cogs_annual / max(num_customers, 1)
    gross_profit_per_customer = gross_profit / max(num_customers, 1)

    # Per-user economics
    revenue_per_user = annual_revenue / max(total_users, 1)
    cogs_per_user = total_cogs_annual / max(total_users, 1)

    # Health assessment
    if gross_margin_pct >= 0.80:
        margin_health = "excellent"
        margin_message = "Excellent margins - healthy SaaS economics"
    elif gross_margin_pct >= 0.70:
        margin_health = "good"
        margin_message = "Good margins - within SaaS benchmarks"
    elif gross_margin_pct >= 0.60:
        margin_health = "fair"
        margin_message = "Fair margins - consider optimizing costs or pricing"
    else:
        margin_health = "poor"
        margin_message = "Low margins - pricing likely too low or costs too high"

    return {
        # Revenue
        "annual_revenue": annual_revenue,
        "monthly_revenue": monthly_revenue,
        "num_customers": num_customers,
        "total_users": total_users,
        "storage_gb": avg_storage_gb,

        # Infrastructure breakdown
        "infra_base": infra_base * 12,
        "infra_per_user": infra_per_user * 12,
        "storage_cost": storage_cost * 12,
        "bandwidth_cost": bandwidth_cost * 12,
        "monitoring_cost": monitoring_cost * 12,
        "llm_cost": llm_cost * 12,
        "email_cost": email_cost * 12,
        "total_infra_annual": total_infra_annual,

        # Support breakdown
        "support_hours_monthly": support_hours_per_customer * num_customers,
        "support_labor_annual": support_monthly * 12,
        "customer_success_annual": cs_monthly * 12,
        "total_support_annual": total_support_annual,

        # Payment processing
        "payment_processing_annual": payment_processing_annual,

        # Totals
        "total_cogs_annual": total_cogs_annual,
        "gross_profit": gross_profit,
        "gross_margin_pct": gross_margin_pct,

        # Percentages of revenue
        "cogs_pct": cogs_pct,
        "infra_pct": infra_pct,
        "support_pct": support_pct,

        # Per-customer/user
        "revenue_per_customer": revenue_per_customer,
        "cogs_per_customer": cogs_per_customer,
        "gross_profit_per_customer": gross_profit_per_customer,
        "revenue_per_user": revenue_per_user,
        "cogs_per_user": cogs_per_user,

        # Health
        "margin_health": margin_health,
        "margin_message": margin_message,
    }


def calculate_phased_rollout(
    total_lines: int,
    phase1_lines: int,
    users_per_line: int,
    tier: str,
    deployment: str,
    months_between_phases: int = 3,
) -> list:
    """Calculate phased rollout plan."""
    phases = []
    remaining_lines = total_lines
    current_lines = 0
    phase_num = 1

    # Phase 1: Pilot
    pilot_lines = phase1_lines
    pilot_users = pilot_lines * users_per_line
    pilot_estimate = calculate_estimate(
        tier, deployment,
        full_users=int(pilot_users * 0.25),
        operators=int(pilot_users * 0.60),
        viewers=int(pilot_users * 0.15),
    )
    phases.append({
        "phase": phase_num,
        "name": "Pilot",
        "lines": pilot_lines,
        "cumulative_lines": pilot_lines,
        "users": pilot_users,
        "arr": pilot_estimate["annual_with_addons"],
        "month": 0,
    })
    current_lines = pilot_lines
    remaining_lines -= pilot_lines
    phase_num += 1

    # Subsequent phases: Expand
    month = months_between_phases
    while remaining_lines > 0:
        expand_lines = min(remaining_lines, max(2, total_lines // 4))  # 25% of total or remaining
        current_lines += expand_lines
        expand_users = current_lines * users_per_line

        expand_estimate = calculate_estimate(
            tier, deployment,
            full_users=int(expand_users * 0.25),
            operators=int(expand_users * 0.60),
            viewers=int(expand_users * 0.15),
        )

        phases.append({
            "phase": phase_num,
            "name": f"Expansion {phase_num - 1}",
            "lines": expand_lines,
            "cumulative_lines": current_lines,
            "users": expand_users,
            "arr": expand_estimate["annual_with_addons"],
            "month": month,
        })

        remaining_lines -= expand_lines
        month += months_between_phases
        phase_num += 1

    return phases


# =============================================================================
# STREAMLIT APP
# =============================================================================

st.set_page_config(
    page_title="AmbacTracker Pricing Calculator",
    page_icon="📊",
    layout="wide",
)

st.title("AmbacTracker Pricing Calculator")

# Initialize session state
if "deals" not in st.session_state:
    st.session_state.deals = []

# Tabs
tabs = st.tabs([
    "💰 Pricing",
    "📊 Margin Analysis",
    "🧪 Pilot/POC",
    "📈 ROI Calculator",
    "🚀 Phased Rollout",
    "🏆 vs Competition",
    "📋 Deal Pipeline"
])

# =============================================================================
# TAB 1: PRICING
# =============================================================================

with tabs[0]:
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Configuration")

        # Company info
        company_name = st.text_input("Company Name", placeholder="Acme Manufacturing")

        use_quick = st.checkbox("Estimate from total employees", value=True)

        if use_quick:
            total_employees = st.number_input("Total Employees", min_value=1, value=100, step=10)
            operator_pct = st.slider("Operator %", 20, 80, 60, 5)
            full_pct = st.slider("Full User %", 10, 50, 25, 5)
            viewer_pct = st.slider("Viewer/Read-only %", 0, 30, 10, 5)

            operators = int(total_employees * operator_pct / 100)
            full_users = int(total_employees * full_pct / 100)
            viewers = int(total_employees * viewer_pct / 100)
            st.caption(f"→ {full_users} full, {operators} operators, {viewers} viewers")
        else:
            full_users = st.number_input("Full Users (QA, Eng, Admin)", min_value=0, value=25, step=5)
            operators = st.number_input("Operators", min_value=0, value=60, step=5)
            viewers = st.number_input("Viewers (Read-only)", min_value=0, value=10, step=5)
            total_employees = full_users + operators + viewers

        st.divider()

        tier = st.selectbox(
            "Product Tier",
            options=list(USER_PRICING.keys()),
            format_func=lambda x: USER_PRICING[x]["name"],
            index=1,
        )

        deployment = st.selectbox(
            "Deployment Model",
            options=list(DEPLOYMENT.keys()),
            format_func=lambda x: DEPLOYMENT[x]["name"],
        )

        st.divider()

        # Contract terms
        st.subheader("Contract Terms")

        contract_years = st.radio(
            "Contract Length",
            options=[1, 2, 3],
            format_func=lambda x: f"{x} year" + ("s" if x > 1 else "") + (f" (-{int(MULTI_YEAR_DISCOUNTS[x]*100)}%)" if MULTI_YEAR_DISCOUNTS[x] > 0 else ""),
            horizontal=True,
        )

        payment_term = st.selectbox(
            "Payment Terms",
            options=list(PAYMENT_TERMS.keys()),
            format_func=lambda x: f"{PAYMENT_TERMS[x]['name']} ({PAYMENT_TERMS[x]['terms']})" + (f" - {int(abs(PAYMENT_TERMS[x]['discount'])*100)}% {'discount' if PAYMENT_TERMS[x]['discount'] > 0 else 'premium'}" if PAYMENT_TERMS[x]['discount'] != 0 else ""),
        )

        include_training = st.checkbox("Include training costs", value=False)

        st.divider()

        # Add-ons
        st.subheader("Add-ons")
        selected_addons = []
        for key, addon in ADDONS.items():
            if key == "multi_site":
                continue
            if st.checkbox(f"{addon['name']} (${addon['price']:,}/yr)", key=f"addon_{key}"):
                selected_addons.append(key)

        additional_sites = st.number_input("Additional Sites", min_value=0, value=0, step=1)

    with col2:
        st.subheader("Estimate" + (f" for {company_name}" if company_name else ""))

        result = calculate_estimate(
            tier=tier,
            deployment=deployment,
            full_users=full_users,
            operators=operators,
            viewers=viewers,
            addons=selected_addons,
            additional_sites=additional_sites,
            contract_years=contract_years,
            payment_term=payment_term,
            include_training=include_training,
        )

        # Summary metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Users", result["total_users"])
        m2.metric("Monthly", f"${result['total_monthly']:,.0f}")
        m3.metric("Annual (ARR)", f"${result['annual_with_addons']:,.0f}")
        m4.metric(f"{contract_years}-Year TCV" if contract_years > 1 else "Year 1",
                  f"${result['total_contract_value']:,.0f}" if contract_years > 1 else f"${result['year_one_total']:,.0f}")

        st.divider()

        # Detailed breakdown
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("**User Breakdown**")
            user_data = [
                {"Type": "Full Users", "Count": result["full_users"], "Rate": f"${result['full_rate']}/mo"},
                {"Type": "Operators", "Count": result["operators"], "Rate": f"${result['operator_rate']}/mo"},
            ]
            if result["viewers"] > 0:
                user_data.append({"Type": "Viewers", "Count": result["viewers"], "Rate": f"${result['viewer_rate']}/mo"})
            st.dataframe(pd.DataFrame(user_data), hide_index=True, width="stretch")

            if result["hit_minimum"]:
                st.warning(f"Minimum applied: ${result['min_monthly']:,.0f}/mo")

            # Implementation timeline
            impl_min, impl_max = result["implementation_weeks"]
            st.info(f"📅 Implementation: {impl_min}-{impl_max} weeks typical")

        with col_b:
            st.markdown("**Pricing Summary**")
            costs = [{"Item": "Base Annual", "Amount": f"${result['annual_raw']:,.0f}"}]

            if result["payment_adjustment"] > 0:
                costs.append({"Item": f"Payment Discount ({PAYMENT_TERMS[payment_term]['name']})", "Amount": f"-${result['payment_adjustment']:,.0f}"})
            elif result["payment_adjustment"] < 0:
                costs.append({"Item": f"Extended Terms Premium", "Amount": f"+${abs(result['payment_adjustment']):,.0f}"})

            if result["multi_year_discount"] > 0:
                costs.append({"Item": f"{result['contract_years']}-Year Discount", "Amount": f"-${result['multi_year_discount']:,.0f}"})
            if result["addon_total"] > 0:
                costs.append({"Item": "Add-ons", "Amount": f"+${result['addon_total']:,}"})
            if result["compliance_total"] > 0:
                costs.append({"Item": "CMMC Compliance", "Amount": f"+${result['compliance_total']:,}"})

            costs.append({"Item": "**Annual (ARR)**", "Amount": f"**${result['annual_with_addons']:,.0f}**"})
            st.dataframe(pd.DataFrame(costs), hide_index=True, width="stretch")

        # Pilot option callout
        st.divider()
        st.markdown("**🧪 Pilot Program Available**")
        st.success(f"90-day pilot: **${result['pilot_fee']:,.0f}** (100% credited to full contract)")

        # Add to pipeline button
        if company_name and st.button("➕ Add to Deal Pipeline", type="primary"):
            deal = {
                "company": company_name,
                "stage": "lead",
                "created": datetime.now().isoformat(),
                **result,
            }
            st.session_state.deals.append(deal)
            st.success(f"Added {company_name} to pipeline!")


# =============================================================================
# TAB 2: MARGIN ANALYSIS
# =============================================================================

with tabs[1]:
    st.subheader("Margin Analysis")
    st.markdown("*Understand your cost structure and profitability at different price points*")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("### Scenario Configuration")

        analysis_mode = st.radio(
            "Analysis Mode",
            ["Single Customer", "Portfolio (Multiple Customers)"],
            horizontal=True,
        )

        if analysis_mode == "Single Customer":
            margin_users = st.number_input("Total Users", min_value=5, value=50, step=5, key="margin_users")
            margin_customers = 1
        else:
            margin_customers = st.number_input("Number of Customers", min_value=1, value=10, step=1)
            margin_users = st.number_input("Total Users (all customers)", min_value=10, value=500, step=50, key="margin_users_port")

        st.divider()

        margin_tier = st.selectbox(
            "Pricing Tier",
            options=list(USER_PRICING.keys()),
            format_func=lambda x: USER_PRICING[x]["name"],
            index=1,
            key="margin_tier",
        )

        # Calculate default ARR based on user mix
        margin_full = int(margin_users * 0.25)
        margin_ops = int(margin_users * 0.60)
        margin_viewers = int(margin_users * 0.15)

        default_estimate = calculate_estimate(
            margin_tier, "saas", margin_full, margin_ops, margin_viewers
        )
        default_arr = default_estimate["annual_with_addons"] * margin_customers

        # Allow manual ARR override for what-if analysis
        use_custom_arr = st.checkbox("Override ARR for what-if analysis")
        if use_custom_arr:
            margin_arr = st.number_input(
                "Annual Revenue (ARR)",
                min_value=1000,
                value=int(default_arr),
                step=1000,
                format="%d",
            )
        else:
            margin_arr = default_arr
            st.caption(f"Calculated ARR: ${margin_arr:,.0f}")

        st.divider()

        # Storage estimate
        storage_per_user = st.slider(
            "Avg Storage per User (GB)",
            min_value=0.1,
            max_value=5.0,
            value=0.5,
            step=0.1,
            help="Documents, 3D models, images. Typical: 0.3-1GB/user"
        )
        total_storage = margin_users * storage_per_user

        st.divider()

        # Payment method (B2B typically uses ACH for large contracts)
        payment_method = st.selectbox(
            "Payment Method Mix",
            options=["mixed", "card", "ach"],
            format_func=lambda x: {
                "mixed": "Mixed (60% ACH, 40% Card) - Typical B2B",
                "card": "All Card (2.9% + Billing)",
                "ach": "All ACH (0.8% capped) - Enterprise",
            }[x],
            help="B2B annual contracts often pay via ACH bank transfer"
        )

        # AI usage level
        ai_usage = st.selectbox(
            "AI Feature Usage",
            options=["moderate", "light", "heavy"],
            format_func=lambda x: {
                "light": "Light (~$0.25/user/mo) - Basic search",
                "moderate": "Moderate (~$0.50/user/mo) - Doc analysis",
                "heavy": "Heavy (~$1.25/user/mo) - Full AI assistant",
            }[x],
            help="LLM API costs for document analysis, chat, etc."
        )

    with col2:
        # Run margin analysis
        margin_result = calculate_margin_analysis(
            annual_revenue=margin_arr,
            total_users=margin_users,
            num_customers=margin_customers,
            avg_storage_gb=total_storage,
            payment_method=payment_method,
            ai_usage_level=ai_usage,
        )

        # Key metrics
        st.markdown("### Profitability Summary")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Annual Revenue", f"${margin_result['annual_revenue']:,.0f}")
        m2.metric("Total COGS", f"${margin_result['total_cogs_annual']:,.0f}")
        m3.metric("Gross Profit", f"${margin_result['gross_profit']:,.0f}")

        # Gross margin with color indicator
        gm_pct = margin_result['gross_margin_pct'] * 100
        if margin_result['margin_health'] == 'excellent':
            m4.metric("Gross Margin", f"{gm_pct:.1f}%", delta="Excellent")
        elif margin_result['margin_health'] == 'good':
            m4.metric("Gross Margin", f"{gm_pct:.1f}%", delta="Good")
        elif margin_result['margin_health'] == 'fair':
            m4.metric("Gross Margin", f"{gm_pct:.1f}%", delta="Fair", delta_color="off")
        else:
            m4.metric("Gross Margin", f"{gm_pct:.1f}%", delta="Low", delta_color="inverse")

        # Health message
        if margin_result['margin_health'] == 'excellent':
            st.success(f"✅ {margin_result['margin_message']}")
        elif margin_result['margin_health'] == 'good':
            st.info(f"👍 {margin_result['margin_message']}")
        elif margin_result['margin_health'] == 'fair':
            st.warning(f"⚠️ {margin_result['margin_message']}")
        else:
            st.error(f"❌ {margin_result['margin_message']}")

        st.divider()

        # Cost breakdown
        st.markdown("### Cost Breakdown")

        cost_col1, cost_col2 = st.columns(2)

        with cost_col1:
            st.markdown("**Infrastructure (Railway)**")
            infra_data = [
                {"Component": "Base allocation", "Annual": f"${margin_result['infra_base']:,.0f}"},
                {"Component": "Per-user compute", "Annual": f"${margin_result['infra_per_user']:,.0f}"},
                {"Component": "Storage (docs/3D)", "Annual": f"${margin_result['storage_cost']:,.0f}"},
                {"Component": "Bandwidth", "Annual": f"${margin_result['bandwidth_cost']:,.0f}"},
                {"Component": "Monitoring (Sentry/etc)", "Annual": f"${margin_result['monitoring_cost']:,.0f}"},
                {"Component": "LLM APIs (AI features)", "Annual": f"${margin_result['llm_cost']:,.0f}"},
                {"Component": "Email (transactional)", "Annual": f"${margin_result['email_cost']:,.0f}"},
                {"Component": "**Subtotal**", "Annual": f"**${margin_result['total_infra_annual']:,.0f}**"},
            ]
            st.dataframe(pd.DataFrame(infra_data), hide_index=True, width="stretch")
            st.caption(f"Infrastructure = {margin_result['infra_pct']*100:.1f}% of revenue (target: 8-15%)")

        with cost_col2:
            st.markdown("**Support & Operations**")
            support_data = [
                {"Component": "Support labor", "Annual": f"${margin_result['support_labor_annual']:,.0f}"},
                {"Component": "Customer success", "Annual": f"${margin_result['customer_success_annual']:,.0f}"},
                {"Component": "**Subtotal**", "Annual": f"**${margin_result['total_support_annual']:,.0f}**"},
            ]
            st.dataframe(pd.DataFrame(support_data), hide_index=True, width="stretch")
            st.caption(f"Support = {margin_result['support_pct']*100:.1f}% of revenue")

            st.markdown("**Payment Processing**")
            st.markdown(f"Stripe (2.9%): **${margin_result['payment_processing_annual']:,.0f}**/year")

        st.divider()

        # Per-unit economics
        st.markdown("### Unit Economics")

        if margin_customers > 1:
            unit_col1, unit_col2 = st.columns(2)
            with unit_col1:
                st.markdown("**Per Customer**")
                st.metric("Revenue/Customer", f"${margin_result['revenue_per_customer']:,.0f}/yr")
                st.metric("COGS/Customer", f"${margin_result['cogs_per_customer']:,.0f}/yr")
                st.metric("Gross Profit/Customer", f"${margin_result['gross_profit_per_customer']:,.0f}/yr")

            with unit_col2:
                st.markdown("**Per User**")
                st.metric("Revenue/User", f"${margin_result['revenue_per_user']:,.0f}/yr")
                st.metric("COGS/User", f"${margin_result['cogs_per_user']:,.0f}/yr")
        else:
            unit_col1, unit_col2 = st.columns(2)
            with unit_col1:
                st.metric("Revenue/User", f"${margin_result['revenue_per_user']:,.0f}/yr")
            with unit_col2:
                st.metric("COGS/User", f"${margin_result['cogs_per_user']:,.0f}/yr")

        st.divider()

        # Benchmark comparison
        st.markdown("### vs SaaS Benchmarks")

        bench_data = [
            {
                "Metric": "Gross Margin",
                "Your Value": f"{margin_result['gross_margin_pct']*100:.1f}%",
                "Target": "75-90%",
                "Status": "✅" if margin_result['gross_margin_pct'] >= 0.75 else ("⚠️" if margin_result['gross_margin_pct'] >= 0.65 else "❌"),
            },
            {
                "Metric": "COGS %",
                "Your Value": f"{margin_result['cogs_pct']*100:.1f}%",
                "Target": "10-20%",
                "Status": "✅" if margin_result['cogs_pct'] <= 0.20 else ("⚠️" if margin_result['cogs_pct'] <= 0.28 else "❌"),
            },
            {
                "Metric": "Infrastructure %",
                "Your Value": f"{margin_result['infra_pct']*100:.1f}%",
                "Target": "8-15%",
                "Status": "✅" if margin_result['infra_pct'] <= 0.15 else ("⚠️" if margin_result['infra_pct'] <= 0.20 else "❌"),
            },
            {
                "Metric": "Support %",
                "Your Value": f"{margin_result['support_pct']*100:.1f}%",
                "Target": "≤8%",
                "Status": "✅" if margin_result['support_pct'] <= 0.08 else ("⚠️" if margin_result['support_pct'] <= 0.12 else "❌"),
            },
        ]
        st.dataframe(pd.DataFrame(bench_data), hide_index=True, width="stretch")

        st.caption("Sources: [CloudZero](https://www.cloudzero.com/blog/saas-gross-margin-benchmarks/), [SaaS Capital](https://www.saas-capital.com/blog-posts/spending-benchmarks-for-private-b2b-saas-companies/)")

    # Break-even analysis section
    st.divider()
    st.markdown("### Break-Even & Sensitivity")

    be_col1, be_col2, be_col3 = st.columns(3)

    with be_col1:
        st.markdown("**Minimum Viable Price**")
        # Calculate minimum ARR to hit 70% gross margin
        min_arr_70 = margin_result['total_cogs_annual'] / 0.30  # COGS = 30% of revenue
        min_arr_75 = margin_result['total_cogs_annual'] / 0.25  # COGS = 25% of revenue

        st.metric("For 70% Gross Margin", f"${min_arr_70:,.0f} ARR")
        st.metric("For 75% Gross Margin", f"${min_arr_75:,.0f} ARR")

        current_vs_min = (margin_arr - min_arr_75) / min_arr_75 * 100 if min_arr_75 > 0 else 0
        if current_vs_min > 0:
            st.caption(f"Current price is {current_vs_min:.0f}% above 75% target")
        else:
            st.caption(f"Current price is {abs(current_vs_min):.0f}% below 75% target")

    with be_col2:
        st.markdown("**Price Sensitivity**")
        # Show margin at different price points
        price_scenarios = [0.8, 0.9, 1.0, 1.1, 1.2]  # 80% to 120% of current
        for mult in price_scenarios:
            scenario_arr = margin_arr * mult
            scenario_margin = (scenario_arr - margin_result['total_cogs_annual']) / scenario_arr if scenario_arr > 0 else 0
            label = f"{int(mult*100)}% of current"
            if mult == 1.0:
                st.markdown(f"**{label}: {scenario_margin*100:.1f}%** ← Current")
            else:
                st.markdown(f"{label}: {scenario_margin*100:.1f}%")

    with be_col3:
        st.markdown("**Scale Benefits**")
        # Show how margins improve with more users (economies of scale)
        scale_users = [margin_users, margin_users * 2, margin_users * 5, margin_users * 10]
        for users in scale_users:
            # Revenue scales linearly with users
            scale_arr = margin_arr * (users / margin_users)
            # Costs scale sub-linearly (economies of scale)
            scale_result = calculate_margin_analysis(
                scale_arr, users, margin_customers, users * storage_per_user,
                payment_method=payment_method, ai_usage_level=ai_usage
            )
            label = f"{users:,} users"
            if users == margin_users:
                st.markdown(f"**{label}: {scale_result['gross_margin_pct']*100:.1f}%** ← Current")
            else:
                st.markdown(f"{label}: {scale_result['gross_margin_pct']*100:.1f}%")


# =============================================================================
# TAB 3: PILOT/POC
# =============================================================================

with tabs[2]:
    st.subheader("Pilot / Proof of Concept Pricing")

    st.markdown("""
    **How our pilots work:**
    - 90-day pilot with full functionality
    - 15% of estimated ACV (min $5K, max $25K)
    - 100% of pilot fee credited to full contract
    - Dedicated success manager during pilot
    """)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Pilot Calculator")

        pilot_employees = st.number_input("Pilot Users (subset of org)", min_value=5, value=25, step=5, key="pilot_emp")
        pilot_lines = st.number_input("Production Lines in Pilot", min_value=1, value=1, step=1)

        pilot_tier = st.selectbox(
            "Target Tier",
            options=list(USER_PRICING.keys()),
            format_func=lambda x: USER_PRICING[x]["name"],
            index=1,
            key="pilot_tier",
        )

        # Calculate pilot pricing
        pilot_full = int(pilot_employees * 0.25)
        pilot_ops = int(pilot_employees * 0.60)
        pilot_viewers = int(pilot_employees * 0.15)

        pilot_estimate = calculate_estimate(
            pilot_tier, "saas", pilot_full, pilot_ops, pilot_viewers
        )

        st.divider()

        st.metric("Pilot Fee (90 days)", f"${pilot_estimate['pilot_fee']:,.0f}")
        st.caption("100% credited to annual contract")

        st.metric("If converted to full contract", f"${pilot_estimate['annual_with_addons']:,.0f}/year")
        st.caption(f"Net cost after credit: ${pilot_estimate['annual_with_addons'] - pilot_estimate['pilot_fee']:,.0f}")

    with col2:
        st.markdown("### Pilot Success Criteria")

        st.markdown("""
        **Typical pilot goals (customize per customer):**

        ✅ **Week 1-2: Setup & Training**
        - System configured for pilot line
        - Core users trained
        - Data migration (if applicable)

        ✅ **Week 3-8: Active Usage**
        - Daily production tracking
        - Quality inspections logged
        - Documents uploaded/managed

        ✅ **Week 9-12: Evaluation**
        - ROI metrics gathered
        - User feedback collected
        - Expansion plan developed

        **Success metrics:**
        - [ ] 80%+ daily active usage
        - [ ] 50%+ reduction in paper forms
        - [ ] Quality data captured in real-time
        - [ ] Positive user NPS
        """)

    st.divider()

    st.markdown("### Why Pilots Convert")

    conv_col1, conv_col2, conv_col3 = st.columns(3)

    with conv_col1:
        st.markdown("""
        **Financial**
        - 100% credit removes risk
        - ROI visible in 90 days
        - No long-term commitment
        """)

    with conv_col2:
        st.markdown("""
        **Operational**
        - Prove value on real data
        - Train champions early
        - Identify integration needs
        """)

    with conv_col3:
        st.markdown("""
        **Political**
        - Build internal advocates
        - Reduce buying committee risk
        - Create expansion momentum
        """)


# =============================================================================
# TAB 4: ROI CALCULATOR
# =============================================================================

with tabs[3]:
    st.subheader("ROI Calculator")
    st.markdown("*Help customers justify the investment with concrete savings*")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("### Company Metrics")

        annual_revenue = st.number_input(
            "Annual Revenue ($)",
            min_value=1000000,
            value=10000000,
            step=1000000,
            format="%d",
        )

        roi_employees = st.number_input("Total Employees", min_value=10, value=100, step=10, key="roi_emp")

        copq_percent = st.slider(
            "Estimated COPQ (% of revenue)",
            min_value=5,
            max_value=40,
            value=20,
            help="Cost of Poor Quality - typically 15-25% of revenue"
        ) / 100

        st.divider()

        # Get software cost for ROI calc
        roi_tier = st.selectbox("Proposed Tier", list(USER_PRICING.keys()), index=1, key="roi_tier",
                                format_func=lambda x: USER_PRICING[x]["name"])

        roi_estimate = calculate_estimate(
            roi_tier, "saas",
            full_users=int(roi_employees * 0.25),
            operators=int(roi_employees * 0.60),
            viewers=int(roi_employees * 0.15),
        )

        software_cost = roi_estimate["annual_with_addons"]
        st.metric("Software Investment", f"${software_cost:,.0f}/year")

    with col2:
        st.markdown("### Potential Savings")

        roi = calculate_roi(annual_revenue, roi_employees, copq_percent)

        # Savings breakdown
        savings_data = [
            {"Category": "Quality Cost Reduction (COPQ)", "Current Cost": f"${roi['current_copq']:,.0f}", "Potential Savings": f"${roi['copq_reduction']:,.0f}", "Notes": "40% reduction typical"},
            {"Category": "Scrap & Rework Reduction", "Current Cost": f"${roi['current_scrap_rework']:,.0f}", "Potential Savings": f"${roi['scrap_rework_reduction']:,.0f}", "Notes": "50% reduction typical"},
            {"Category": "Paper Process Elimination", "Current Cost": f"${roi['current_paper_cost']:,.0f}", "Potential Savings": f"${roi['paper_elimination']:,.0f}", "Notes": "80% paper reduction"},
            {"Category": "Compliance Cost Reduction", "Current Cost": f"${roi['current_compliance_cost']:,.0f}", "Potential Savings": f"${roi['compliance_reduction']:,.0f}", "Notes": "Audit prep, documentation"},
            {"Category": "Labor Efficiency Gains", "Current Cost": "—", "Potential Savings": f"${roi['labor_efficiency']:,.0f}", "Notes": "Process automation"},
        ]

        st.dataframe(pd.DataFrame(savings_data), hide_index=True, width="stretch")

        st.divider()

        # ROI summary
        net_savings = roi["total_annual_savings"] - software_cost
        roi_percent = (net_savings / software_cost) * 100 if software_cost > 0 else 0
        payback_months = (software_cost / roi["total_annual_savings"]) * 12 if roi["total_annual_savings"] > 0 else 999

        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Total Annual Savings", f"${roi['total_annual_savings']:,.0f}")
        r2.metric("Software Cost", f"${software_cost:,.0f}")
        r3.metric("Net Annual Benefit", f"${net_savings:,.0f}", delta=f"{roi_percent:.0f}% ROI")
        r4.metric("Payback Period", f"{payback_months:.1f} months")

        if payback_months < 12:
            st.success(f"💰 **Strong ROI**: Payback in under {payback_months:.0f} months. Net benefit of ${net_savings:,.0f}/year.")
        elif payback_months < 18:
            st.info(f"📈 **Good ROI**: Payback in {payback_months:.0f} months.")
        else:
            st.warning(f"⚠️ Consider smaller deployment or Lite tier to improve ROI.")


# =============================================================================
# TAB 5: PHASED ROLLOUT
# =============================================================================

with tabs[4]:
    st.subheader("Phased Rollout Planner")
    st.markdown("*Land and expand: Start small, prove value, grow*")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("### Facility Profile")

        total_lines = st.number_input("Total Production Lines", min_value=1, value=8, step=1)
        users_per_line = st.number_input("Avg Users per Line", min_value=5, value=12, step=1)

        phase1_lines = st.number_input(
            "Phase 1 (Pilot) Lines",
            min_value=1,
            max_value=total_lines,
            value=min(2, total_lines),
        )

        months_between = st.slider("Months Between Phases", min_value=2, max_value=6, value=3)

        rollout_tier = st.selectbox(
            "Tier",
            options=list(USER_PRICING.keys()),
            format_func=lambda x: USER_PRICING[x]["name"],
            index=1,
            key="rollout_tier",
        )

        rollout_deployment = st.selectbox(
            "Deployment",
            options=list(DEPLOYMENT.keys()),
            format_func=lambda x: DEPLOYMENT[x]["name"],
            key="rollout_dep",
        )

    with col2:
        st.markdown("### Rollout Plan")

        phases = calculate_phased_rollout(
            total_lines, phase1_lines, users_per_line,
            rollout_tier, rollout_deployment, months_between
        )

        # Phase table
        phase_data = []
        for p in phases:
            phase_data.append({
                "Phase": p["name"],
                "Month": p["month"],
                "Lines": f"+{p['lines']} → {p['cumulative_lines']} total",
                "Users": p["users"],
                "ARR at Phase": f"${p['arr']:,.0f}",
            })

        st.dataframe(pd.DataFrame(phase_data), hide_index=True, width="stretch")

        # Growth visualization
        st.markdown("### ARR Growth Over Time")

        chart_data = pd.DataFrame({
            "Month": [p["month"] for p in phases],
            "ARR": [p["arr"] for p in phases],
            "Users": [p["users"] for p in phases],
        })

        st.line_chart(chart_data.set_index("Month")["ARR"])

        # Summary
        final_arr = phases[-1]["arr"]
        initial_arr = phases[0]["arr"]
        expansion_multiple = final_arr / initial_arr if initial_arr > 0 else 1

        st.divider()
        s1, s2, s3 = st.columns(3)
        s1.metric("Starting ARR (Pilot)", f"${initial_arr:,.0f}")
        s2.metric("Full Rollout ARR", f"${final_arr:,.0f}")
        s3.metric("Expansion Multiple", f"{expansion_multiple:.1f}x")


# =============================================================================
# TAB 6: VS COMPETITION
# =============================================================================

with tabs[5]:
    st.subheader("Competitive Comparison")

    col1, col2 = st.columns([1, 3])

    with col1:
        comp_employees = st.number_input("Total Employees", min_value=10, value=100, step=10, key="comp_emp")
        comp_full = int(comp_employees * 0.25)
        comp_ops = int(comp_employees * 0.60)
        comp_total = comp_full + comp_ops

        st.caption(f"→ {comp_total} licensed users")

        comp_tier = st.selectbox(
            "Your Tier",
            options=list(USER_PRICING.keys()),
            format_func=lambda x: USER_PRICING[x]["name"],
            index=1,
            key="comp_tier",
        )

    with col2:
        # Your pricing
        your_result = calculate_estimate(comp_tier, "saas", comp_full, comp_ops)

        comparison_data = [{
            "Vendor": "**AmbacTracker**",
            "Type": "MES/QMS/DMS",
            "Annual": your_result["annual_with_addons"],
            "Per User/Mo": your_result["total_monthly"] / max(comp_total, 1),
            "Includes": "Full stack, tiered pricing, AI features",
        }]

        # Competitors
        for key, c in COMPETITORS.items():
            if key == "qualio":
                annual = c["platform_fee"] + (comp_total * c["per_user_annual"])
            elif key == "qt9":
                annual = (c["min_annual"] + c["max_annual"]) / 2  # Midpoint estimate
            elif c.get("per_user"):
                effective = max(comp_total, c.get("min_users", 1))
                annual = max(effective * c["per_user"] * 12, c.get("min_annual", 0))
            else:
                annual = c.get("min_annual", 0)

            comparison_data.append({
                "Vendor": c["name"],
                "Type": c.get("type", "QMS"),
                "Annual": annual,
                "Per User/Mo": annual / 12 / max(comp_total, 1),
                "Includes": c.get("type", "—"),
            })

        df = pd.DataFrame(comparison_data)
        df["Annual"] = df["Annual"].apply(lambda x: f"${x:,.0f}")
        df["Per User/Mo"] = df["Per User/Mo"].apply(lambda x: f"${x:,.0f}")

        st.dataframe(df, hide_index=True, width="stretch")

        st.divider()

        st.markdown("### Key Differentiators")

        d1, d2 = st.columns(2)

        with d1:
            st.markdown("""
            **Why we win:**
            - ✅ **All-in-one**: MES + QMS + DMS in single platform
            - ✅ **Tiered pricing**: Operators pay less than full users
            - ✅ **AI features**: Document search, defect analysis
            - ✅ **3D visualization**: Heatmaps, annotations
            - ✅ **Modern UX**: Built in 2024, not 2004
            """)

        with d2:
            st.markdown("""
            **Where we're developing:**
            - 🔄 Advanced scheduling (OR-Tools) - Q2
            - 🔄 PPAP workflows - planned
            - 🔄 Full ERP features - roadmap

            **Best fit:**
            - Precision manufacturing
            - Aerospace/defense (AS9100, CMMC)
            - Automotive tier 2-3 (IATF 16949)
            """)


# =============================================================================
# TAB 7: DEAL PIPELINE
# =============================================================================

with tabs[6]:
    st.subheader("Deal Pipeline")

    if not st.session_state.deals:
        st.info("No deals in pipeline. Add companies from the Pricing tab.")
    else:
        # Pipeline summary
        total_arr = sum(d["annual_with_addons"] for d in st.session_state.deals)
        weighted_arr = sum(
            d["annual_with_addons"] * DEAL_STAGES[d["stage"]]["probability"]
            for d in st.session_state.deals
        )

        p1, p2, p3 = st.columns(3)
        p1.metric("Deals in Pipeline", len(st.session_state.deals))
        p2.metric("Total ARR", f"${total_arr:,.0f}")
        p3.metric("Weighted ARR", f"${weighted_arr:,.0f}")

        st.divider()

        # Deal list with stage management
        for i, deal in enumerate(st.session_state.deals):
            with st.expander(f"**{deal['company']}** - {DEAL_STAGES[deal['stage']]['name']} - ${deal['annual_with_addons']:,.0f} ARR"):
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.markdown(f"""
                    - **Tier:** {deal['tier_name']}
                    - **Deployment:** {deal['deployment_name']}
                    - **Users:** {deal['total_users']} ({deal['full_users']} full, {deal['operators']} ops, {deal['viewers']} viewers)
                    - **ARR:** ${deal['annual_with_addons']:,.0f}
                    - **Pilot Fee:** ${deal['pilot_fee']:,.0f}
                    """)

                with col2:
                    new_stage = st.selectbox(
                        "Stage",
                        options=list(DEAL_STAGES.keys()),
                        index=list(DEAL_STAGES.keys()).index(deal["stage"]),
                        format_func=lambda x: f"{DEAL_STAGES[x]['name']} ({int(DEAL_STAGES[x]['probability']*100)}%)",
                        key=f"stage_{i}",
                    )

                    if new_stage != deal["stage"]:
                        st.session_state.deals[i]["stage"] = new_stage
                        st.rerun()

                    if st.button("Remove", key=f"remove_{i}"):
                        st.session_state.deals.pop(i)
                        st.rerun()

        st.divider()

        # Stage breakdown
        st.markdown("### Pipeline by Stage")

        stage_summary = {}
        for deal in st.session_state.deals:
            stage = deal["stage"]
            if stage not in stage_summary:
                stage_summary[stage] = {"count": 0, "arr": 0}
            stage_summary[stage]["count"] += 1
            stage_summary[stage]["arr"] += deal["annual_with_addons"]

        stage_data = []
        for stage_key, stage_info in DEAL_STAGES.items():
            if stage_key in stage_summary:
                s = stage_summary[stage_key]
                stage_data.append({
                    "Stage": stage_info["name"],
                    "Probability": f"{int(stage_info['probability']*100)}%",
                    "Deals": s["count"],
                    "ARR": f"${s['arr']:,.0f}",
                    "Weighted": f"${s['arr'] * stage_info['probability']:,.0f}",
                })

        if stage_data:
            st.dataframe(pd.DataFrame(stage_data), hide_index=True, width="stretch")

        # Export
        if st.button("📥 Export Pipeline to JSON"):
            st.download_button(
                "Download",
                json.dumps(st.session_state.deals, indent=2, default=str),
                "pipeline.json",
                "application/json",
            )


# Footer
st.divider()
st.caption("AmbacTracker Pricing Calculator | Internal use only | Run: `streamlit run tools/pricing_calculator_gui.py`")
