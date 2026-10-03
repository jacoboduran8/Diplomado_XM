

def default(capacity, items):
    # a trivial algorithm for filling the knapsack
    # it takes items in-order until the knapsack is full
    value = 0
    weight = 0
    taken = [0]*len(items)

    for item in items:
        if weight + item["weight"] <= capacity:
            taken[item["index"]] = 1
            value += item["value"]
            weight += item["weight"]
    
    return value, taken

def density(capacity, items):
    value = 0
    weight = 0
    taken = [0]*len(items)
    items = sorted(items, key=lambda x: x["density"], reverse=True)

    for item in items:
        if weight + item["weight"] <= capacity:
            taken[item["index"]] = 1
            value += item["value"]
            weight += item["weight"]
    
    return value, taken

def relaxed(capacity, items, relaxed=True, pre=None):
    value = 0
    weight = 0
    taken = [0]*len(items)
    items = sorted(items, key=lambda x: x["density"], reverse=True)

    fraction = not relaxed

    if pre is not None:
        for idx, val in enumerate(pre):
            if val == 0:
                continue

            taken[items[idx]["index"]] = val
            weight += items[idx]["weight"]
            value += items[idx]["value"]
            remain = capacity - weight

            if remain < 0:
                return -1, 0
    else:
        pre = []

    for idx, item in enumerate(items):

        if idx <= len(pre):
            continue

        if item["up"] == 0:
            continue

        elif item["lo"] == 1:
            weight += item["weight"]
            value += item["value"]
            remain = capacity - weight
            if remain < 0:
                return -1, 0

        if weight + item["weight"] <= capacity:
            taken[item["index"]] = 1
            value += item["value"]
            weight += item["weight"]
            item["level"] = 1

        elif not fraction:
            remain = capacity - weight
            value += item["density"] * remain
            weight += remain
            item["level"] = remain / item["weight"]
            taken[item["index"]] = item["level"]
            fraction = True
            print(f'Item {item["index"]} taken fractionally: {item["level"]*100:.2f}%')
            break
    
    return value, taken

def dynamic_programming(capacity, items):

    # Fill the knapsack table using dynamic programming approach
    n = len(items)
    K = [[0 for _ in range(capacity + 1)] for _ in range(n + 1)]

    for i in range(n + 1):
        for w in range(capacity + 1):
            if i == 0 or w == 0:
                K[i][w] = 0
            elif items[i-1].weight <= w:
                K[i][w] = max(items[i-1].value + K[i-1][w - items[i-1].weight], K[i-1][w])
            else:
                K[i][w] = K[i-1][w]

    # Backtrack to find the items to include in the knapsack
    value = K[n][capacity]
    w = capacity
    taken = [0]*n

    for i in range(n, 0, -1):
        if value <= 0:
            break
        if value == K[i-1][w]:
            continue
        else:
            taken[items[i-1].index] = 1
            value -= items[i-1].value
            w -= items[i-1].weight

    return K[n][capacity], taken

def branch_cut(capacity, items):
    solution_pool = []
    incumbent_value = 0
    incumbent_solution = None

    items = sorted(items, key=lambda x: x["density"], reverse=True)

    for depth in range(len(items)):
        pass

    return