#!/usr/bin/env python3
"""
Herramienta de apoyo - Taller Modulo 1, Punto 3 (Diplomado XM - UPB)
Curva PQ estimada de la maquina sincronica de SINC_UPB.pfd

Dos comandos:

  final     Lee el CSV que se exporta de PowerFactory para UN caso de la
            carpeta "Curva_PQ" y muestra, para cada variable, el valor al
            inicio y al final de la simulacion. Sirve para llenar la
            tabla Resultados_PQ.csv sin leer las graficas a ojo, y marca
            las senales de limitadores que cambiaron.

  graficar  Lee Resultados_PQ.csv (la tabla ya llena) y dibuja la curva
            PQ estimada: region de sobreexcitacion (Q > 0) y de
            subexcitacion (Q < 0), con el limitador que actua en cada
            punto y las etiquetas en 30, 40 y 50 MW.
            Si se dan los datos de la maquina (--sn y --xd) dibuja ademas
            el circulo de corriente de estator (SCL) y el de corriente de
            campo (OEL) que pasan por los puntos medidos, como chequeo
            fisico de la identificacion.

Ejemplos:
  python3 punto3_curva_PQ.py final  Exportes/P30_sobre.csv
  python3 punto3_curva_PQ.py graficar Resultados_PQ.csv
  python3 punto3_curva_PQ.py graficar Resultados_PQ.csv --sn 60 --xd 1.05 --v 1.0

Requiere matplotlib (ya esta instalado en este computador).
"""
import argparse
import csv
import math
import os
import sys

LIMITADORES = {
    "OEL": "#C0392B",   # rojo
    "SCL": "#7D3C98",   # morado
    "V/HZ": "#D68910",  # ocre
    "UEL": "#1F618D",   # azul
    "MEL": "#148F77",   # verde azulado
}
P_PEDIDAS = (30.0, 40.0, 50.0)


# ------------------------------------------------------------ utilidades
def num(s):
    s = (s or "").strip().replace('"', "")
    if s == "":
        return None
    if s.count(",") == 1 and "." not in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def detectar_delim(lineas):
    def cols(d):
        n = []
        for ln in lineas[-20:]:
            fila = next(csv.reader([ln], delimiter=d), [])
            n.append(sum(1 for c in fila if num(c) is not None))
        return min(n) if n else 0
    return max([";", "\t", ","], key=cols)


# ------------------------------------------------------------ comando final
def cmd_final(a):
    with open(a.csv, "r", encoding="utf-8-sig", errors="replace") as fh:
        lineas = [l for l in fh.read().splitlines() if l.strip()]
    d = detectar_delim(lineas)
    filas = list(csv.reader(lineas, delimiter=d))
    # filas de encabezado = las que no son totalmente numericas
    ini = 0
    while ini < len(filas) and not all(num(c) is not None for c in filas[ini] if c.strip()):
        ini += 1
    enc = filas[:ini]
    datos = [[num(c) for c in f] for f in filas[ini:]]
    ncol = len(datos[0])
    nombres = []
    for j in range(ncol):
        partes = [e[j].strip() for e in enc if j < len(e) and e[j].strip()]
        nombres.append(" | ".join(partes) if partes else f"col{j}")
    t = [f[0] for f in datos]
    tf = t[-1]
    ventana = a.ventana

    def prom(j, desde, hasta):
        v = [f[j] for f in datos if f[j] is not None and desde <= f[0] <= hasta]
        return sum(v) / len(v) if v else float("nan")

    print(f"\nArchivo: {a.csv}")
    print(f"Tiempo simulado: {t[0]:.2f} s a {tf:.2f} s  (promedio final en los ultimos {ventana} s)\n")
    print(f"{'Variable':60s} {'Inicial':>12s} {'Final':>12s}  Nota")
    claves = ("oel", "uel", "scl", "mel", "vhz", "v/hz", "volt_hz", "lim")
    for j in range(1, ncol):
        v0 = prom(j, t[0], t[0] + min(ventana, 0.5))
        v1 = prom(j, tf - ventana, tf)
        nota = ""
        if any(k in nombres[j].lower() for k in claves):
            cambio = abs(v1 - v0) > max(1e-3, 0.01 * abs(v0))
            nota = "<-- LIMITADOR: cambio, revisar" if cambio else "(limitador sin cambio)"
        print(f"{nombres[j][:60]:60s} {v0:12.4f} {v1:12.4f}  {nota}")
    print("\nCopie P y Q finales (y Vt, It, Ifd si estan) en Resultados_PQ.csv.")


# ------------------------------------------------------------ comando graficar
def leer_tabla(path):
    with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
        lineas = [l for l in fh.read().splitlines() if l.strip() and not l.startswith("#")]
    d = ";" if lineas[0].count(";") >= lineas[0].count(",") else ","
    rd = csv.DictReader(lineas, delimiter=d)
    pts = []
    for r in rd:
        r = {k.strip(): (v or "").strip() for k, v in r.items() if k}
        p, q = num(r.get("P_MW")), num(r.get("Q_Mvar"))
        if p is None or q is None:
            continue
        reg = r.get("Region", "").lower()
        reg = "sobre" if reg.startswith("sobre") or (not reg and q >= 0) else "sub"
        lim = r.get("Limitador", "").upper().replace(" ", "").replace("VHZ", "V/HZ")
        pts.append(dict(caso=r.get("Caso", ""), reg=reg, p=p, q=q, lim=lim,
                        vt=num(r.get("Vt_pu")), it=num(r.get("It_pu")), ifd=num(r.get("Ifd_pu"))))
    return pts


def cmd_graficar(a):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    pts = leer_tabla(a.tabla)
    if not pts:
        sys.exit("La tabla no tiene filas con P y Q llenos.")
    sobre = sorted([x for x in pts if x["reg"] == "sobre"], key=lambda x: x["p"])
    sub = sorted([x for x in pts if x["reg"] == "sub"], key=lambda x: x["p"])

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    fig, ax = plt.subplots(figsize=(8.2, 7.2))

    # contorno estimado (une los puntos de cada region)
    for grupo, ls in ((sobre, "-"), (sub, "-")):
        if len(grupo) > 1:
            ax.plot([x["q"] for x in grupo], [x["p"] for x in grupo], ls, color="#2C3E50",
                    lw=1.6, zorder=2)

    # circulos teoricos que pasan por los puntos (opcional)
    if a.sn and a.xd:
        th = [math.radians(g) for g in range(0, 181)]
        scl = [x for x in pts if x["lim"] == "SCL"]
        if scl:
            r = sum(math.hypot(x["p"], x["q"]) for x in scl) / len(scl)
            ax.plot([r * math.cos(t) for t in th], [r * math.sin(t) for t in th], ":",
                    color=LIMITADORES["SCL"], lw=1.2,
                    label=f"Circulo corriente de estator |S| = {r:.1f} MVA")
        oel = [x for x in pts if x["lim"] == "OEL"]
        if oel:
            qc = -(a.v ** 2) * a.sn / a.xd
            r = sum(math.hypot(x["p"], x["q"] - qc) for x in oel) / len(oel)
            ax.plot([qc + r * math.cos(t) for t in th], [r * math.sin(t) for t in th], ":",
                    color=LIMITADORES["OEL"], lw=1.2,
                    label=f"Circulo corriente de campo (centro Q = {qc:.1f} Mvar)")

    # puntos por limitador
    vistos = set()
    for x in pts:
        c = LIMITADORES.get(x["lim"], "#7F8C8D")
        lab = x["lim"] if x["lim"] and x["lim"] not in vistos else None
        if lab:
            vistos.add(x["lim"])
        ax.scatter(x["q"], x["p"], s=48, color=c, edgecolor="white", linewidth=0.8,
                   zorder=4, label=lab)

    # etiquetas en 30, 40 y 50 MW
    for pp in P_PEDIDAS:
        ax.axhline(pp, color="#BDC3C7", lw=0.8, ls="--", zorder=1)
        for x in pts:
            if abs(x["p"] - pp) <= a.tol and x["lim"]:
                dx = 6 if x["reg"] == "sobre" else -6
                ax.annotate(f"{x['lim']}\n({x['q']:.1f} Mvar)", (x["q"], x["p"]),
                            textcoords="offset points", xytext=(dx, 4),
                            ha="left" if dx > 0 else "right", fontsize=8.5,
                            color=LIMITADORES.get(x["lim"], "#2C3E50"), weight="bold")

    ax.axvline(0, color="#2C3E50", lw=0.9)
    ax.set_xlabel("Potencia reactiva Q (Mvar)")
    ax.set_ylabel("Potencia activa P (MW)")
    ax.set_title(a.titulo, fontsize=12, color="#0F4761", weight="bold")
    ymax = max(x["p"] for x in pts) * 1.12
    ax.set_ylim(0, ymax)
    qmin, qmax = min(x["q"] for x in pts), max(x["q"] for x in pts)
    m = 0.18 * (qmax - qmin)
    ax.set_xlim(qmin - m, qmax + m)
    ax.text(0.02, 0.98, "Subexcitacion\n(absorbe Q)", transform=ax.transAxes, va="top",
            fontsize=9, color="#566573")
    ax.text(0.98, 0.98, "Sobreexcitacion\n(entrega Q)", transform=ax.transAxes, va="top",
            ha="right", fontsize=9, color="#566573")
    ax.grid(alpha=0.25)
    ax.legend(loc="lower center", fontsize=8.5, frameon=False, ncol=3,
              bbox_to_anchor=(0.5, -0.22))
    fig.tight_layout()

    base = os.path.splitext(a.salida)[0]
    fig.savefig(base + ".png", dpi=200, bbox_inches="tight")
    fig.savefig(base + ".svg", bbox_inches="tight")
    print(f"Grafica guardada: {base}.png y {base}.svg\n")

    # resumen en texto para el informe
    print(f"{'Region':16s} {'P (MW)':>8s} {'Q (Mvar)':>10s} {'|S| (MVA)':>10s}  Limitador")
    for x in sobre + sub:
        s = math.hypot(x["p"], x["q"])
        reg = "Sobreexcitacion" if x["reg"] == "sobre" else "Subexcitacion"
        print(f"{reg:16s} {x['p']:8.2f} {x['q']:10.2f} {s:10.2f}  {x['lim'] or '-'}")
    if a.sn:
        print(f"\n|S| / Sn con Sn = {a.sn} MVA: los puntos SCL deben quedar con |S| casi igual"
              " en ambas regiones (mismo circulo).")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    f = sp.add_parser("final", help="valores inicial/final de un CSV exportado de PowerFactory")
    f.add_argument("csv")
    f.add_argument("--ventana", type=float, default=2.0, help="segundos finales a promediar")
    g = sp.add_parser("graficar", help="dibujar la curva PQ desde Resultados_PQ.csv")
    g.add_argument("tabla")
    g.add_argument("--salida", default="Curva_PQ_SINC_UPB.png")
    g.add_argument("--titulo", default="Curva PQ estimada - Unidad sincronica SINC_UPB")
    g.add_argument("--sn", type=float, help="potencia aparente nominal (MVA)")
    g.add_argument("--xd", type=float, help="reactancia sincronica xd (p.u.)")
    g.add_argument("--v", type=float, default=1.0, help="tension en bornes (p.u.)")
    g.add_argument("--tol", type=float, default=1.5, help="tolerancia en MW para 30/40/50")
    a = ap.parse_args()
    {"final": cmd_final, "graficar": cmd_graficar}[a.cmd](a)


if __name__ == "__main__":
    main()
