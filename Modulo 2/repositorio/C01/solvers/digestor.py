def digest(input_data:str) -> list:

    lines = input_data.split('\n')

    firstLine = lines[0].split()
    item_count = int(firstLine[0])
    capacity = int(firstLine[1])

    items = []
    
    for i in range(1, item_count+1):
        line = lines[i]
        parts = line.split()
        items.append(
            {
                "index" : i-1,
                "value" : int(parts[0]),
                "weight" : int(parts[1]),
                "density" : int(parts[0]) / int(parts[1]),
            }
        )

    items = sorted(items, key=lambda x: x["density"], reverse=True)

    return capacity, items