from logging import getLogger, FileHandler

LOGGER = getLogger(__name__)
LOGGER.setLevel("DEBUG")
#set logger file handler
fh = FileHandler('bc_solver.log')
fh.setLevel("DEBUG")
LOGGER.addHandler(fh)

def relaxed(capacity, items, pre={}):
    # items should be sorted by density in descending order

    # Get precomputed values
    value = pre["value"]
    weight = pre["curr_weight"]
    taken = pre["taken"]
    
    enu_index = len(taken)

    # Add last taken item
    if taken[-1]:
        item = items[enu_index-1]
        weight += item["weight"]
        value += item["value"]

    # Check feasibility
    remain = capacity - weight
    if remain < 0:
        return False, value, value, weight
    
    # Compute relaxed value
    taken = taken + [0] * (len(items) - len(taken))
    curr_value = value
    curr_weight = weight

    # Try to fill the knapsack greedily
    # for idx, item in enumerate(items):
    #     if idx < enu_index:
    #         continue
    #     if weight + item["weight"] <= capacity:
    #         value += item["value"]
    #         weight += item["weight"]
    #         taken[idx] = 1
    
    # Then try the relaxed part
    for idx, item in enumerate(items):
        if idx < enu_index:
            continue
        if taken[idx]:
            continue
        remain = capacity - weight
        value += item["density"] * remain
        weight += remain
        break
    
    return True, curr_value, value, curr_weight


def branch_and_bound(capacity, items):
    
    BIN_VALUES = (0,1)
    bad_status = ("infeasible", "pruned")
    curr_id = 0
    MAX_ITER = 1e6
    new_incumbent = False

    incumbent_value = 0
    depth = len(items)

    taken = [0 for item in items if item["weight"] > capacity]
    if len(taken) == len(items) or capacity == 0:
        return 0, [0]*len(items)

    pool = [{"id": 0, "value": 0, "curr_weight": 0, "relaxed_value": 0, "taken": taken, "status": "optimal", "parents": ""}, ]
    pre_pool = []
    lazy_pool = []
    solution = None

    LOGGER.debug("---ID  |Status     |Value      |Relaxed    |Weight     |Taken")

    while True:

        for node in pool:
            
            taken = node["taken"]

            if len(taken) == depth:
                # print("Reached depth for node ID:", node["id"])
                continue

            for bin_val in BIN_VALUES:
                curr_id += 1
                new_node = {
                    "id": curr_id,
                    "value": node["value"],
                    "curr_weight": node["curr_weight"],
                    "relaxed_value": node["relaxed_value"],
                    "taken": taken.copy() + [bin_val],
                    "status": "unexplored",
                    "parents": node["parents"] + "," + str(node["id"]),
                }

                feasible, curr_value, relaxed_value, curr_weight = relaxed(capacity, items, pre=new_node)
                new_node["value"] = curr_value
                new_node["relaxed_value"] = relaxed_value
                new_node["curr_weight"] = curr_weight
                new_node["status"] = "feasible" if feasible else "infeasible"

                if feasible and len(new_node["taken"]) == depth and curr_value:
                    if curr_value > incumbent_value:
                        incumbent_value = curr_value
                        new_node["status"] = "optimal"
                        solution = new_node
                        new_incumbent = True
                        # print("New incumbent found! Node ID:", new_node["id"], "Value:", curr_value)
                    else:
                        new_node["status"] = "pruned"
                        # print("Pruned optimal node ID:", new_node["id"], "Value:", curr_value, "Incumbent Value:", incumbent_value)
                # , Parents: {new_node['parents']}
                log_entry = "^" if new_incumbent else " "
                staken = '.'.join(map(str, new_node["taken"]))
                log_entry += f"{new_node['id']:<4} |{new_node['status']:<10} |{new_node['value']:<10} |{new_node['relaxed_value']:<10.0f} |{new_node['curr_weight']:<10} |{staken} |parents: {new_node['parents']}"
                new_incumbent = False
                if new_node["status"] in bad_status or new_node["status"] == "optimal":
                    LOGGER.debug(" " + log_entry)
                    continue

                if incumbent_value > 0 and new_node["relaxed_value"] <= incumbent_value:
                    new_node["status"] = "pruned"
                    LOGGER.debug("*" + log_entry)
                    # print("Pruned by bound node ID:", new_node["id"], "Relaxed Value:", new_node["relaxed_value"], "Incumbent Value:", incumbent_value)
                    continue

                pre_pool.append(new_node)
                LOGGER.debug(" " + log_entry)
            
        if not pre_pool and lazy_pool:
            LOGGER.debug("--Refilling pre_pool from lazy_pool...")
            if incumbent_value > 0:
                lazy_pool = [node for node in lazy_pool if node["relaxed_value"] > incumbent_value]
                
            lazy_pool = sorted(lazy_pool, key=lambda x: x["relaxed_value"], reverse=True)
            p_size = min(10, len(lazy_pool))
            pre_pool = lazy_pool[:p_size]
            lazy_pool = lazy_pool[p_size:]

        if not pre_pool and not lazy_pool:
            break

        pool = sorted(pre_pool, key=lambda x: x["relaxed_value"], reverse=True)
        pre_pool = []
        lazy_pool += pool[1:]
        pool = pool[:1]

        if curr_id >= MAX_ITER:
            LOGGER.debug(f"Reached maximum iterations. {MAX_ITER} iterations done.")
            break
    # print("Solution found after", curr_id, "iterations.")
    # print("Incumbent value:", incumbent_value)
    print("Capacity:", capacity, "total_weight:", solution["curr_weight"])
    for k,v in solution.items():
        print(f"{k}: {v}")

    final_taken = [0] * len(items)
    for idx, val in enumerate(solution["taken"]):
        if not val:
            continue
        item = items[idx]
        final_taken[item["index"]] = val
    print("Final taken:", final_taken)

    return solution["value"], final_taken


"""
ks30_0
99798 0
0 0 1 0 1 0 1 0 1 0 1 0 1 0 0 0 1 0 1 0 1 0 0 0 0 0 0 0 0 0
0.0.1.0.1.0.1.0.1.0.1.0.1.0.0.0.1.0.1.0.1.0.0.0.0.0.0.0.0.0
"""