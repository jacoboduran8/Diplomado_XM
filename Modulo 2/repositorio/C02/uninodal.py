# ============================================================
# INSTALLATION (uncomment if needed)
# ============================================================
# pip install pyomo
# pip install highspy
#
# Verify solver:
# python -c "from pyomo.environ import *; print(SolverFactory('highs').available())"
# ============================================================

from pyomo.environ import (
    Param, Set, ConcreteModel, Var, Constraint, Objective, Suffix, 
    value,
    NonNegativeReals, maximize, minimize, SolverFactory)
import matplotlib.pyplot as plt
import numpy as np

# ============================================================
# ECONOMIC DISPATCH WITH SOCIAL WELFARE
# ============================================================
#
# Social Welfare:
#
# Maximize:
#
#     Consumer Benefit - Generation Cost
#
#     max  Σ Benefit(d) - Σ Cost(g)
#
# Demand is modeled as elastic using demand blocks.
#
# Each demand block represents a willingness-to-pay.
#
# ============================================================

model = ConcreteModel()

# ============================================================
# SETS
# ============================================================

model.GENERATORS = Set(initialize=["Hydro", "Coal", "Gas"])

model.DEMAND_BLOCKS = Set(
    initialize=["D1", "D2", "D3", "D4"]
)

# ============================================================
# GENERATOR DATA
# ============================================================

generator_capacity = {
    "Hydro": 100,
    "Coal": 80,
    "Gas": 120,
}

generator_cost = {
    "Hydro": 20,
    "Coal": 40,
    "Gas": 90,
}

# ============================================================
# DEMAND CURVE
# ============================================================
#
# Price-Quantity demand blocks
#
# Example:
#
# Consumers are willing to buy:
#
# first 50 MW at $150/MWh
# next 50 MW at $110/MWh
# next 50 MW at $70/MWh
# next 50 MW at $30/MWh
#
# ============================================================

demand_capacity = {
    "D1": 50,
    "D2": 50,
    "D3": 50,
    "D4": 50,
}

demand_price = {
    "D1": 150,
    "D2": 110,
    "D3": 70,
    "D4": 30,
}

# ============================================================
# PARAMETERS
# ============================================================

model.GenMax = Param(
    model.GENERATORS,
    initialize=generator_capacity
)

model.GenCost = Param(
    model.GENERATORS,
    initialize=generator_cost
)

model.DemandMax = Param(
    model.DEMAND_BLOCKS,
    initialize=demand_capacity
)

model.DemandPrice = Param(
    model.DEMAND_BLOCKS,
    initialize=demand_price
)

# ============================================================
# DECISION VARIABLES
# ============================================================

# Generation dispatch

model.pg = Var(
    model.GENERATORS,
    domain=NonNegativeReals
)

# Accepted demand

model.pd = Var(
    model.DEMAND_BLOCKS,
    domain=NonNegativeReals
)

# ============================================================
# OBJECTIVE:
# MAXIMIZE SOCIAL WELFARE
# ============================================================

def social_welfare_rule(m):

    generation_cost = sum(
        m.GenCost[g] * m.pg[g]
        for g in m.GENERATORS
    )

    return generation_cost


model.SocialWelfare = Objective(
    rule=social_welfare_rule,
    sense=minimize
)

# ============================================================
# GENERATOR LIMITS
# ============================================================

def generator_limit_rule(m, g):
    return m.pg[g] <= m.GenMax[g]

model.GeneratorLimits = Constraint(
    model.GENERATORS,
    rule=generator_limit_rule
)

# ============================================================
# DEMAND BLOCK LIMITS
# ============================================================

def demand_limit_rule(m, d):
    return m.pd[d] == m.DemandMax[d]

model.DemandLimits = Constraint(
    model.DEMAND_BLOCKS,
    rule=demand_limit_rule
)

# ============================================================
# ENERGY BALANCE
# ============================================================

def balance_rule(m):

    return (
        sum(m.pg[g] for g in m.GENERATORS)
        ==
        sum(m.pd[d] for d in m.DEMAND_BLOCKS)
    )

model.Balance = Constraint(rule=balance_rule)

# ============================================================
# DUALS
# ============================================================

model.dual = Suffix(direction=Suffix.IMPORT)

# ============================================================
# SOLVE
# ============================================================

solver = SolverFactory("highs")

results = solver.solve(model)

# ============================================================
# RESULTS
# ============================================================

print("\n")
print("=" * 60)
print("SOCIAL WELFARE ECONOMIC DISPATCH")
print("=" * 60)

print("\nGENERATION")

for g in model.GENERATORS:
    print(
        f"{g:10s}: "
        f"{value(model.pg[g]):8.2f} MW"
    )

print("\nACCEPTED DEMAND")

for d in model.DEMAND_BLOCKS:
    print(
        f"{d:10s}: "
        f"{value(model.pd[d]):8.2f} MW"
    )

total_generation = sum(
    value(model.pg[g])
    for g in model.GENERATORS
)

print(f"\nTotal Generation = {total_generation:.2f} MW")

social_welfare = value(model.SocialWelfare)

print(f"Social Welfare    = {social_welfare:.2f}")

# ============================================================
# MARKET CLEARING PRICE
# ============================================================

mcp = model.dual[model.Balance]

print(f"Market Price      = {mcp:.2f} $/MWh")

# ============================================================
# BUILD SUPPLY CURVE
# ============================================================

supply_blocks = []

for g in model.GENERATORS:
    supply_blocks.append(
        (
            value(model.GenCost[g]),
            value(model.GenMax[g]),
            g
        )
    )

supply_blocks.sort(key=lambda x: x[0])

supply_x = [0]
supply_y = []

cum = 0

for cost, qty, name in supply_blocks:

    supply_y.append(cost)

    cum += qty

    supply_x.append(cum)

# ============================================================
# BUILD DEMAND CURVE
# ============================================================

demand_blocks_sorted = []

for d in model.DEMAND_BLOCKS:
    demand_blocks_sorted.append(
        (
            value(model.DemandPrice[d]),
            value(model.DemandMax[d]),
            d
        )
    )

# descending willingness-to-pay
demand_blocks_sorted.sort(
    key=lambda x: x[0],
    reverse=True
)

demand_x = [0]
demand_y = []

cum = 0

for price, qty, name in demand_blocks_sorted:

    demand_y.append(price)

    cum += qty

    demand_x.append(cum)

# ============================================================
# MARKET RESULT
# ============================================================

cleared_quantity = sum(
    value(model.pg[g])
    for g in model.GENERATORS
)

market_price = model.dual[model.Balance]

# ============================================================
# MERIT ORDER CURVE
# ============================================================

gen_sorted = sorted(
    model.GENERATORS,
    key=lambda g: value(model.GenCost[g])
)

cum = 0

plt.figure(figsize=(10,6))

for g in gen_sorted:

    q = value(model.GenMax[g])
    c = value(model.GenCost[g])

    plt.bar(
        cum + q/2,
        c,
        width=q,
        edgecolor='black',
        alpha=0.7,
        label=g
    )

    cum += q

plt.axvline(
    cleared_quantity,
    color='black',
    linestyle='--',
    linewidth=2
)

plt.axhline(
    market_price,
    color='green',
    linestyle='--',
    linewidth=2
)

plt.xlabel("Accumulated Capacity (MW)")
plt.ylabel("Marginal Cost ($/MWh)")

plt.title("Merit Order Curve")

plt.legend()

plt.grid(alpha=0.3)

plt.tight_layout()

plt.show()