from pathlib import Path
from random import randint

# extraer los datos de precio y peso de cada objeto.

data_path = Path(__file__).parent / "data" / "mochila.txt"

def extraer_datos(objetos):
    data = {}
    idx = 0
    
    with open(data_path, "r") as f:
        for linea in f:
            precio, peso = map(int, linea.split(','))
            data[idx] = [precio, peso, precio / peso]
            idx += 1
    return data

## Parámetros
PESO = 2680
data = extraer_datos(data_path)
precios, pesos, densidad = zip(*[(v[0], v[1], v[2]) for v in data.values()])

def solver_densidad(capacidad, precios, pesos, densidad):
    indices_ordenados = sorted(range(len(densidad)), key=lambda i: densidad[i], reverse=True)
    X = [0 for _ in range(len(precios))]
    peso_acumulado = 0
    fun_obj = 0
    for item, (precio, peso, dens) in enumerate(zip(precios, pesos, densidad)):
        if peso_acumulado + peso <= capacidad:
            X[indices_ordenados[item]] = 1
            peso_acumulado += peso
            fun_obj += precio
        else:
            X[indices_ordenados[item]] = 0
    return X, peso_acumulado, fun_obj

sol, peso_acumulado, fun_obj = solver_densidad(PESO, precios, pesos, densidad)

print("Variación de la mochila:", sol)
print("Valor de la función objetivo:", fun_obj)
print("Peso acumulado en la mochila:", peso_acumulado)