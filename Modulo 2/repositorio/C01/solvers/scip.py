# Create a scip instance for the knapsack problem
from pyscipopt import Model


def optimize_knapsack(capacity, items):
    
    m = Model("knapsack")
    # Add variables
    x = {}
    for i, item in enumerate(items):
        x[i] = m.addVar(vtype="B", name=f"x_{i}")

    # Set objective
    m.setObjective(
        sum(item["value"] * x[i] for i, item in enumerate(items)),
        "maximize"
    )

    # Add capacity constraint
    m.addCons(
        sum(item["weight"] * x[i] for i, item in enumerate(items)) <= capacity,
        "capacity_constraint"
    )

    # Supress output
    m.hideOutput()
    # Optimize the model
    m.optimize()

    # Retrieve solution
    taken = [0] * len(items)
    pre_taken = [0] * len(items)
    for i in range(len(items)):
        if m.getVal(x[i]) > 0.5:
            item = items[i]
            taken[item["index"]] = 1
            pre_taken[i] = 1

    # print("Pre taken:", pre_taken)
    # print("taken:", taken)
    total_value = m.getObjVal()

    # total_weight = sum(items[i]["weight"] * pre_taken[i] for i in range(len(items)))
    # print("Total weight:", total_weight)
    return int(total_value), taken

"""
ks30_0
99798 0
0 0 1 0 1 0 1 0 1 0 1 0 1 0 0 0 1 0 1 0 1 0 0 0 0 0 0 0 0 0
"""