# Import Libraries
from pymo.environ import Param, Set, ConcreteModel, Var, Constraint

# Definicion del modelo
m = ConcreteModel()

# Definicion de los conjuntos
m.GENERATORS = Set(initialize=["Hydro", "Coal", "Gas"])
m.DEMAND_BLOCKS = Set(initialize=["D1", "D2", "D3", "D4"])

generator_capacity = {
    "Hydro": 100,
    "Coal": 80,
    "Gas": 120,
}