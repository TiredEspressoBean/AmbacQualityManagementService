#!/usr/bin/env python3
"""
Internal Pricing Calculator for AmbacTracker
Quick estimates for sales conversations and planning.

Deployment Models:
- SaaS: Multi-tenant cloud, per-user pricing
- Dedicated: Single-tenant cloud, per-user + platform fee
- Air-gapped: On-prem, annual license + support
- CMMC: Air-gapped with compliance add-ons
"""

# =============================================================================
# PRICING CONFIGURATION
# =============================================================================

# Per-user monthly rates by tier
USER_PRICING = {
    "lite": {
        "name": "Lite (MES/DMS)",
        "full_user": 75,
        "operator": 35,
    },
    "standard": {
        "name": "Standard (MES/QMS/DMS)",
        "full_user": 100,
        "operator": 50,
    },
    "enterprise": {
        "name": "Enterprise (Full Suite)",
        "full_user": 150,
        "operator": 65,
    },
}

# Deployment model modifiers (market-validated pricing)
DEPLOYMENT = {
    "saas": {
        "name": "SaaS (Multi-tenant)",
        "user_multiplier": 1.0,      # Base pricing
        "platform_fee": 0,           # No platform fee
        "annual_discount": 0.10,     # 10% for annual commit
        "setup_fee": 0,
        "min_annual": 0,
    },
    "dedicated": {
        "name": "Dedicated Cloud (Single-tenant)",
        "user_multiplier": 1.10,     # 10% premium for isolation
        "platform_fee": 750,         # Monthly infrastructure cost
        "annual_discount": 0.10,
        "setup_fee": 5000,           # One-time setup
        "min_annual": 30000,         # $2.5K/mo minimum
    },
    "airgapped": {
        "name": "Air-gapped (On-prem)",
        "user_multiplier": 1.0,      # No software premium - customer handles infra
        "platform_fee": 1500,        # Monthly support/maintenance commitment
        "annual_discount": 0.0,      # Already annual
        "setup_fee": 25000,          # Installation + training (realistic SMB)
        "min_annual": 48000,         # $4K/mo minimum
        "perpetual_multiplier": 3.0, # 3x annual for perpetual license (~5yr payback)
    },
    "cmmc": {
        "name": "CMMC Compliant (Air-gapped + Compliance)",
        "user_multiplier": 1.25,     # 25% premium (aligned with 20-35% industry)
        "platform_fee": 2000,        # Includes compliance support
        "annual_discount": 0.0,
        "setup_fee": 35000,          # Compliance documentation + setup
        "min_annual": 72000,         # $6K/mo minimum
        "perpetual_multiplier": 3.5,
        "compliance_addons": {
            "ssp_templates": 8000,    # System Security Plan templates
            "poam_tracking": 5000,    # Plan of Action & Milestones
            "audit_support": 15000,   # Annual audit prep support
        },
    },
}

# Optional add-ons (annual pricing, market-validated)
ADDONS = {
    "local_llm": {
        "name": "Local LLM (Air-gapped AI)",
        "price": 15000,
        "description": "On-prem AI inference, no data leaves network",
    },
    "sso": {
        "name": "SSO/SAML Integration",
        "price": 6000,
        "description": "Enterprise identity provider integration",
    },
    "api_access": {
        "name": "API Access (ERP Integration)",
        "price": 8000,
        "description": "REST API + webhooks for ERP/MRP sync",
    },
    "advanced_scheduling": {
        "name": "Advanced Scheduling (OR-Tools)",
        "price": 10000,
        "description": "Constraint-based production scheduling",
    },
    "multi_site": {
        "name": "Multi-site License",
        "price": 15000,
        "description": "Per additional facility",
    },
}


# =============================================================================
# CALCULATION FUNCTIONS
# =============================================================================

def calculate_base(tier: str, full_users: int, operators: int) -> dict:
    """Calculate base user pricing (before deployment modifiers)."""
    p = USER_PRICING[tier]

    return {
        "tier": tier,
        "tier_name": p["name"],
        "full_users": full_users,
        "operators": operators,
        "total_users": full_users + operators,
        "full_rate": p["full_user"],
        "operator_rate": p["operator"],
        "full_monthly": full_users * p["full_user"],
        "operator_monthly": operators * p["operator"],
        "base_monthly": (full_users * p["full_user"]) + (operators * p["operator"]),
    }


def calculate_full(
    tier: str,
    deployment: str,
    full_users: int,
    operators: int,
    addons: list = None,
    annual_commit: bool = True,
    perpetual: bool = False,
) -> dict:
    """Full pricing calculation with deployment model and add-ons."""

    base = calculate_base(tier, full_users, operators)
    dep = DEPLOYMENT[deployment]
    addons = addons or []

    # Apply deployment multiplier to user costs
    adjusted_user_monthly = base["base_monthly"] * dep["user_multiplier"]

    # Add platform fee
    total_monthly = adjusted_user_monthly + dep["platform_fee"]

    # Apply minimum
    min_monthly = dep["min_annual"] / 12
    if total_monthly < min_monthly:
        total_monthly = min_monthly
        hit_minimum = True
    else:
        hit_minimum = False

    # Annual calculation
    annual = total_monthly * 12

    # Annual discount (SaaS/dedicated only, if annual commit)
    discount = 0
    if annual_commit and dep["annual_discount"] > 0:
        discount = annual * dep["annual_discount"]
        annual = annual - discount

    # Add-ons
    addon_total = 0
    addon_details = []
    for addon_key in addons:
        if addon_key in ADDONS:
            addon = ADDONS[addon_key]
            addon_total += addon["price"]
            addon_details.append({"key": addon_key, "name": addon["name"], "price": addon["price"]})

    # CMMC compliance add-ons
    compliance_total = 0
    if deployment == "cmmc" and "compliance_addons" in dep:
        for name, price in dep["compliance_addons"].items():
            compliance_total += price

    annual_with_addons = annual + addon_total + compliance_total

    # Perpetual option (air-gapped/cmmc only)
    perpetual_price = None
    if perpetual and "perpetual_multiplier" in dep:
        perpetual_price = annual_with_addons * dep["perpetual_multiplier"]

    return {
        **base,
        "deployment": deployment,
        "deployment_name": dep["name"],
        "user_multiplier": dep["user_multiplier"],
        "adjusted_user_monthly": adjusted_user_monthly,
        "platform_fee": dep["platform_fee"],
        "total_monthly": total_monthly,
        "hit_minimum": hit_minimum,
        "min_monthly": min_monthly,
        "annual_raw": total_monthly * 12,
        "annual_discount": discount,
        "annual": annual,
        "setup_fee": dep["setup_fee"],
        "addons": addon_details,
        "addon_total": addon_total,
        "compliance_total": compliance_total,
        "annual_with_addons": annual_with_addons,
        "perpetual_price": perpetual_price,
        "year_one_total": annual_with_addons + dep["setup_fee"],
    }


def print_full_estimate(r: dict):
    """Pretty print a full estimate."""
    print("\n" + "=" * 60)
    print(f"  {r['deployment_name']}")
    print(f"  {r['tier_name']}")
    print("=" * 60)

    print(f"\n  USERS")
    print(f"  {'-' * 50}")
    print(f"    Full users:    {r['full_users']:>4} @ ${r['full_rate']}/mo")
    print(f"    Operators:     {r['operators']:>4} @ ${r['operator_rate']}/mo")
    print(f"    Total:         {r['total_users']:>4} users")

    print(f"\n  MONTHLY BREAKDOWN")
    print(f"  {'-' * 50}")
    print(f"    Base user cost:        ${r['base_monthly']:>10,}/mo")
    if r['user_multiplier'] != 1.0:
        print(f"    Deployment adj ({r['user_multiplier']:.0%}):   ${r['adjusted_user_monthly']:>10,.0f}/mo")
    if r['platform_fee'] > 0:
        print(f"    Platform fee:          ${r['platform_fee']:>10,}/mo")
    print(f"    {'-' * 40}")
    print(f"    Monthly total:         ${r['total_monthly']:>10,.0f}/mo")
    if r['hit_minimum']:
        print(f"    (minimum applied: ${r['min_monthly']:,.0f}/mo)")

    print(f"\n  ANNUAL PRICING")
    print(f"  {'-' * 50}")
    print(f"    Annual (base):         ${r['annual_raw']:>10,.0f}")
    if r['annual_discount'] > 0:
        print(f"    Annual discount:       -${r['annual_discount']:>9,.0f}")
        print(f"    Annual (discounted):   ${r['annual']:>10,.0f}")

    if r['addons']:
        print(f"\n  ADD-ONS (Annual)")
        print(f"  {'-' * 50}")
        for addon in r['addons']:
            print(f"    {addon['name']:<30} ${addon['price']:>8,}")
        print(f"    {'─' * 40}")
        print(f"    Add-on total:          ${r['addon_total']:>10,}")

    if r['compliance_total'] > 0:
        print(f"\n  CMMC COMPLIANCE PACKAGE")
        print(f"  {'-' * 50}")
        print(f"    SSP Templates, POAM Tracking, Audit Support")
        print(f"    Compliance total:      ${r['compliance_total']:>10,}")

    print(f"\n  TOTALS")
    print(f"  {'-' * 50}")
    print(f"    Annual recurring:      ${r['annual_with_addons']:>10,.0f}")
    if r['setup_fee'] > 0:
        print(f"    One-time setup:        ${r['setup_fee']:>10,}")
        print(f"    {'-' * 40}")
        print(f"    YEAR ONE TOTAL:        ${r['year_one_total']:>10,.0f}")

    if r['perpetual_price']:
        print(f"\n  PERPETUAL OPTION")
        print(f"  {'-' * 50}")
        print(f"    Perpetual license:     ${r['perpetual_price']:>10,.0f}")
        print(f"    (includes first year support)")

    print()


def compare_deployments(tier: str, full_users: int, operators: int):
    """Compare all deployment models."""
    print("\n" + "=" * 70)
    print(f"  DEPLOYMENT COMPARISON: {full_users} full + {operators} operators ({USER_PRICING[tier]['name']})")
    print("=" * 70)

    print(f"\n  {'Deployment':<35} {'Monthly':>12} {'Annual':>12} {'Year 1':>12}")
    print(f"  {'-' * 71}")

    for dep_key in ["saas", "dedicated", "airgapped", "cmmc"]:
        r = calculate_full(tier, dep_key, full_users, operators)
        print(f"  {r['deployment_name']:<35} ${r['total_monthly']:>10,.0f} ${r['annual']:>10,.0f} ${r['year_one_total']:>10,.0f}")

    print()


def scenario_builder():
    """Interactive scenario planning for multiple prospects."""
    print("\n" + "=" * 60)
    print("  SCENARIO BUILDER")
    print("=" * 60)

    scenarios = []

    while True:
        name = input("\n  Customer name (or 'done'): ").strip()
        if name.lower() == 'done':
            break

        try:
            employees = input("  Total employees (or specify 'full,operators'): ").strip()

            if ',' in employees:
                full, ops = map(int, employees.split(','))
            else:
                emp = int(employees)
                ops = int(emp * 0.6)
                full = int(emp * 0.3)
                print(f"    → Assuming {full} full users, {ops} operators")

            print("  Tier options: lite, standard, enterprise")
            tier = input("  Tier [standard]: ").strip() or "standard"
            if tier not in USER_PRICING:
                tier = "standard"

            print("  Deployment options: saas, dedicated, airgapped, cmmc")
            deployment = input("  Deployment [saas]: ").strip() or "saas"
            if deployment not in DEPLOYMENT:
                deployment = "saas"

            result = calculate_full(tier, deployment, full, ops)
            result["customer"] = name
            scenarios.append(result)

            print(f"    → Added: {name} @ ${result['annual_with_addons']:,}/yr ARR")

        except ValueError:
            print("  Invalid input, skipping...")

    if scenarios:
        print("\n" + "=" * 80)
        print("  PIPELINE SUMMARY")
        print("=" * 80)
        print(f"\n  {'Customer':<20} {'Deployment':<15} {'Users':>6} {'Monthly':>10} {'ARR':>12} {'Yr 1':>12}")
        print(f"  {'-' * 78}")

        total_arr = 0
        total_yr1 = 0
        total_users = 0

        for s in scenarios:
            dep_short = s['deployment'][:10]
            print(f"  {s['customer']:<20} {dep_short:<15} {s['total_users']:>6} ${s['total_monthly']:>8,.0f} ${s['annual_with_addons']:>10,} ${s['year_one_total']:>10,}")
            total_arr += s['annual_with_addons']
            total_yr1 += s['year_one_total']
            total_users += s['total_users']

        print(f"  {'-' * 78}")
        print(f"  {'TOTAL':<20} {'':<15} {total_users:>6} ${total_arr//12:>8,.0f} ${total_arr:>10,} ${total_yr1:>10,}")
        print()


def interactive_estimate():
    """Guided estimate builder."""
    print("\n  ESTIMATE BUILDER")
    print("  " + "-" * 40)

    try:
        # Users
        employees = input("\n  Total employees (or 'full,operators'): ").strip()
        if ',' in employees:
            full_users, operators = map(int, employees.split(','))
        else:
            emp = int(employees)
            operators = int(emp * 0.6)
            full_users = int(emp * 0.3)
            print(f"  → Estimated: {full_users} full users, {operators} operators")

        # Tier
        print("\n  Product tiers:")
        print("    1. Lite - MES/DMS basics")
        print("    2. Standard - Full QMS/MES/DMS")
        print("    3. Enterprise - Advanced features")
        tier_choice = input("  Select tier [2]: ").strip() or "2"
        tier = {"1": "lite", "2": "standard", "3": "enterprise"}.get(tier_choice, "standard")

        # Deployment
        print("\n  Deployment model:")
        print("    1. SaaS (cloud multi-tenant)")
        print("    2. Dedicated (cloud single-tenant)")
        print("    3. Air-gapped (on-prem)")
        print("    4. CMMC (air-gapped + compliance)")
        dep_choice = input("  Select deployment [1]: ").strip() or "1"
        deployment = {"1": "saas", "2": "dedicated", "3": "airgapped", "4": "cmmc"}.get(dep_choice, "saas")

        # Add-ons
        addons = []
        if input("\n  Add optional features? (y/n) [n]: ").strip().lower() == 'y':
            print("\n  Available add-ons:")
            addon_keys = list(ADDONS.keys())
            for i, key in enumerate(addon_keys, 1):
                addon = ADDONS[key]
                print(f"    {i}. {addon['name']} - ${addon['price']:,}/yr")

            selections = input("  Enter numbers (comma-separated) or 'none': ").strip()
            if selections and selections.lower() != 'none':
                for num in selections.split(','):
                    try:
                        idx = int(num.strip()) - 1
                        if 0 <= idx < len(addon_keys):
                            addons.append(addon_keys[idx])
                    except ValueError:
                        pass

        # Perpetual?
        perpetual = False
        if deployment in ["airgapped", "cmmc"]:
            perpetual = input("\n  Include perpetual license option? (y/n) [n]: ").strip().lower() == 'y'

        # Calculate and display
        result = calculate_full(tier, deployment, full_users, operators, addons, perpetual=perpetual)
        print_full_estimate(result)

    except ValueError:
        print("  Invalid input")


def main():
    print("\n" + "=" * 60)
    print("  AMBACTRACKER PRICING CALCULATOR")
    print("=" * 60)

    while True:
        print("\n  Options:")
        print("    1. Interactive estimate (guided)")
        print("    2. Compare deployment models")
        print("    3. Compare all tiers")
        print("    4. Scenario builder (multiple prospects)")
        print("    5. Quick SaaS estimate")
        print("    q. Quit")

        choice = input("\n  Select: ").strip().lower()

        if choice == 'q':
            break
        elif choice == '1':
            interactive_estimate()
        elif choice == '2':
            try:
                full = int(input("\n  Full users: "))
                ops = int(input("  Operators: "))
                tier = input("  Tier (lite/standard/enterprise) [standard]: ").strip() or "standard"
                compare_deployments(tier, full, ops)
            except ValueError:
                print("  Invalid input")
        elif choice == '3':
            try:
                full = int(input("\n  Full users: "))
                ops = int(input("  Operators: "))
                dep = input("  Deployment (saas/dedicated/airgapped/cmmc) [saas]: ").strip() or "saas"

                print("\n" + "=" * 60)
                print(f"  TIER COMPARISON ({DEPLOYMENT[dep]['name']})")
                print("=" * 60)
                print(f"\n  {'Tier':<30} {'Monthly':>12} {'Annual':>12}")
                print(f"  {'-' * 54}")

                for tier_key in ["lite", "standard", "enterprise"]:
                    r = calculate_full(tier_key, dep, full, ops)
                    print(f"  {r['tier_name']:<30} ${r['total_monthly']:>10,.0f} ${r['annual']:>10,}")
                print()
            except ValueError:
                print("  Invalid input")
        elif choice == '4':
            scenario_builder()
        elif choice == '5':
            try:
                emp = int(input("\n  Total employees: "))
                ops = int(emp * 0.6)
                full = int(emp * 0.3)
                print(f"  → {full} full users, {ops} operators")

                result = calculate_full("standard", "saas", full, ops)
                print(f"\n  Standard SaaS: ${result['total_monthly']:,.0f}/mo | ${result['annual']:,.0f}/yr")
            except ValueError:
                print("  Invalid input")
        else:
            print("  Invalid option")


if __name__ == "__main__":
    main()
