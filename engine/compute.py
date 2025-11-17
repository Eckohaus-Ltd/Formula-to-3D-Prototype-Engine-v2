import json

def compute_formula_a():
    # Placeholder: E = mc² (Page 1)
    data = []
    for x in range(10):
        for y in range(10):
            z = (x * y) ** 0.5   # keep lightweight
            data.append({"x": x, "y": y, "z": z})
    return data

def compute_formula_b():
    # Placeholder variant: E = m c² + (x+y)
    data = []
    for x in range(10):
        for y in range(10):
            z = (x * y) ** 0.5 + (x + y) / 4
            data.append({"x": x, "y": y, "z": z})
    return data

def save_json(path, payload):
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)

if __name__ == "__main__":
    save_json("docs/volumetric/formula_a.json", compute_formula_a())
    save_json("docs/volumetric/formula_b.json", compute_formula_b())

