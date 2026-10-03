# Conjuntos
$i: \text{conjunto de los elementos que pueden ir en la mochila}$

# Variables

```math
X_{i}: \text{Vale 1 si el objeto va en la mochila, de lo contraio vale 0}
```

# Parametros
$W_{i}: \text{Peso de cada elemento i}$
$P_{i}: \text{Peso de cada elemento i}$
$W^{max}: \text{Peso máximo}$

# Función objetivo

```math
\max \sum_{i} X_{i} \cdot P{i} \\
\text{s.t.:} \\
\sum_{i} X_{i} \cdot W_{i} \le W^{max} \\
X_{i} \in {0,1}
```