#!/usr/bin/env python3
"""
Herramienta de apoyo - Taller Modulo 1, Punto 2 (Diplomado XM - UPB)

Lee resultados exportados de PowerFactory (Plots -> clic derecho -> Export,
o ComRes "Export results" en formato CSV) y calcula los indicadores que pide
la regulacion:

  tiempos   -> Tr y Te (definiciones CREG 060 de 2019, banda del 3 %),
               sobrepaso y si la respuesta es amortiguada.
  estatismo -> estatismo medido a partir de un escalon de frecuencia.
  iq        -> factor k medido, tiempo al 90 % del delta de Iq y tiempo
               de sostenimiento despues de volver a la banda muerta.
  columnas  -> lista las columnas del CSV para saber que nombre usar.

Ejemplos:
  python3 punto2_analisis.py columnas escalon_f.csv
  python3 punto2_analisis.py tiempos escalon_f.csv --col "P" --t0 1.0 --trmax 2 --temax 15
  python3 punto2_analisis.py estatismo --df 0.2 --db 0.03 --p0 0.80 --p1 0.729 --pn 1.0
  python3 punto2_analisis.py iq hueco_05.csv --colu "u1" --coliq "iq" --t0 1.0 --tf 1.5 --banda 0.9 1.1

Solo usa la libreria estandar. Si matplotlib esta instalado, guarda una
grafica PNG junto al CSV con los tiempos marcados.
"""
import argparse
import csv
import math
import os
import sys


# ---------------------------------------------------------------- lectura
def _to_float(s):
    s = s.strip().replace('"', "")
    if s == "":
        raise ValueError
    # coma decimal (configuracion regional en espanol)
    if s.count(",") == 1 and "." not in s:
        s = s.replace(",", ".")
    return float(s)


def leer_csv(path):
    """Devuelve (nombres, columnas). La primera columna es el tiempo."""
    with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
        texto = fh.read()
    lineas = texto.splitlines()

    def _num_cols(d):
        # columnas numericas en las ultimas lineas usando el delimitador d
        n = []
        for ln in lineas[-20:]:
            try:
                n.append(len([_to_float(c) for c in next(csv.reader([ln], delimiter=d)) if c.strip()]))
            except (ValueError, StopIteration):
                n.append(0)
        return min(n) if n else 0

    delim = max([";", "\t", ","], key=_num_cols)
    filas = list(csv.reader(lineas, delimiter=delim))

    encabezado, datos = [], []
    for fila in filas:
        if not any(c.strip() for c in fila):
            continue
        try:
            datos.append([_to_float(c) for c in fila if c.strip() != ""])
        except ValueError:
            if not datos:
                encabezado.append(fila)
    if not datos:
        sys.exit("No se encontraron filas numericas en " + path)

    ncol = min(len(r) for r in datos)
    nombres = []
    for j in range(ncol):
        partes = [h[j].strip() for h in encabezado if j < len(h) and h[j].strip()]
        nombres.append(" | ".join(partes) if partes else "col%d" % j)
    columnas = [[r[j] for r in datos] for j in range(ncol)]
    return nombres, columnas


def buscar_col(nombres, patron):
    patron_l = patron.lower()
    hits = [i for i, n in enumerate(nombres) if patron_l in n.lower()]
    if not hits:
        sys.exit("No hay columna que contenga '%s'. Usa el comando 'columnas'." % patron)
    if len(hits) > 1:
        print("Aviso: varias columnas contienen '%s', uso la primera:" % patron)
        for i in hits:
            print("   [%d] %s" % (i, nombres[i]))
    return hits[0]


def promedio(t, y, a, b):
    v = [yi for ti, yi in zip(t, y) if a <= ti <= b]
    if not v:
        # punto mas cercano
        k = min(range(len(t)), key=lambda i: abs(t[i] - a))
        return y[k]
    return sum(v) / len(v)


# ---------------------------------------------------------------- tiempos
def calc_tiempos(t, y, t0, delta_esperado=None, banda=0.03, ventana_final=1.0):
    y0 = promedio(t, y, t0 - 0.5, t0 - 1e-6)
    yf = promedio(t, y, t[-1] - ventana_final, t[-1])
    d = delta_esperado if delta_esperado is not None else (yf - y0)
    if abs(d) < 1e-12:
        return dict(y0=y0, yf=yf, delta=d, tr=None, te=None, sobrepaso=None)

    tr = None
    for ti, yi in zip(t, y):
        if ti >= t0 and abs(yi - y0) >= banda * abs(d):
            tr = ti - t0
            break

    y_obj = y0 + d
    te = 0.0
    for ti, yi in zip(t, y):
        if ti >= t0 and abs(yi - y_obj) > banda * abs(d):
            te = ti - t0
    # pico en la direccion del cambio
    tramo = [yi for ti, yi in zip(t, y) if ti >= t0]
    pico = max(tramo) if d > 0 else min(tramo)
    sobrepaso = (pico - y_obj) / d * 100.0
    # conteo de cruces del valor final (indicador de oscilacion)
    signos = [1 if (yi - y_obj) > 0 else -1 for yi in tramo]
    cruces = sum(1 for a, b in zip(signos, signos[1:]) if a != b)
    return dict(y0=y0, yf=yf, delta=d, tr=tr, te=te,
                sobrepaso=max(sobrepaso, 0.0), cruces=cruces,
                y_obj=y_obj)


def cmd_tiempos(a):
    nombres, cols = leer_csv(a.csv)
    t = cols[0]
    j = buscar_col(nombres, a.col)
    r = calc_tiempos(t, cols[j], a.t0, a.delta)
    print("\nSenal:", nombres[j])
    print("  Valor inicial           : %.5f" % r["y0"])
    print("  Valor final             : %.5f" % r["yf"])
    print("  Delta usado (100 %%)     : %.5f" % r["delta"])
    if r["tr"] is None:
        print("  No se detecto respuesta (dentro de banda muerta o sin cambio).")
        return
    print("  Tr (3 %% del delta)      : %.3f s" % r["tr"])
    print("  Te (banda +/-3 %%)       : %.3f s" % r["te"])
    print("  Sobrepaso               : %.1f %%" % r["sobrepaso"])
    print("  Cruces del valor final  : %d (pocos cruces = amortiguada)" % r["cruces"])
    if a.trmax is not None:
        print("  Tr <= %.1f s ? %s" % (a.trmax, "CUMPLE" if r["tr"] <= a.trmax else "NO CUMPLE"))
    if a.temax is not None:
        print("  Te <= %.1f s ? %s" % (a.temax, "CUMPLE" if r["te"] <= a.temax else "NO CUMPLE"))
    if r["te"] > t[-1] - a.t0 - 1.0:
        print("  Aviso: Te queda cerca del final de la simulacion. Alarga el tiempo simulado.")
    graficar(a.csv, t, cols[j], nombres[j], a.t0, r)


# ---------------------------------------------------------------- estatismo
def cmd_estatismo(a):
    fn = a.fn
    df_ef = abs(a.df) - a.db
    if df_ef <= 0:
        print("El escalon (%.3f Hz) esta dentro de la banda muerta (%.3f Hz): no debe haber respuesta." % (a.df, a.db))
        return
    dp = abs(a.p1 - a.p0) / a.pn
    if dp == 0:
        print("No hubo cambio de potencia.")
        return
    r = (df_ef / fn) / dp * 100.0
    print("\nDelta f efectivo (fuera de banda): %.4f Hz" % df_ef)
    print("Delta P / Pn                     : %.4f p.u." % dp)
    print("Estatismo medido                 : %.2f %%" % r)
    if a.r:
        dp_esp = (df_ef / fn) / (a.r / 100.0)
        print("Delta P esperado con R=%.1f %%    : %.4f p.u. de Pn" % (a.r, dp_esp))


# ---------------------------------------------------------------- iq
def cmd_iq(a):
    nombres, cols = leer_csv(a.csv)
    t = cols[0]
    ju = buscar_col(nombres, a.colu)
    ji = buscar_col(nombres, a.coliq)
    u, iq = cols[ju], cols[ji]
    u0 = promedio(t, u, a.t0 - 0.2, a.t0 - 1e-6)
    i0 = promedio(t, iq, a.t0 - 0.2, a.t0 - 1e-6)
    # ventana de regimen durante el evento: ultimo 40 % del hueco
    w0 = a.t0 + 0.6 * (a.tf - a.t0)
    u1 = promedio(t, u, w0, a.tf - 1e-3)
    i1 = promedio(t, iq, w0, a.tf - 1e-3)
    du, di = u1 - u0, i1 - i0
    k = di / du if abs(du) > 1e-9 else float("nan")
    print("\nTension: %s" % nombres[ju])
    print("Iq     : %s" % nombres[ji])
    print("  U pre-evento   : %.4f p.u.   U durante: %.4f p.u.   dU = %.4f" % (u0, u1, du))
    print("  Iq pre-evento  : %.4f p.u.   Iq durante: %.4f p.u.  dIq = %.4f" % (i0, i1, di))
    print("  k medido = |dIq/dU| = %.3f   (criterio guia XM: 2 +/- 0.1)" % abs(k))
    if a.k:
        esp = a.k * abs(du)
        print("  dIq esperado con k=%.2f : %.4f p.u. (limitado a %.2f p.u.)" % (a.k, esp, a.imax))

    # tiempo al 90 %
    t90 = None
    for ti, ii in zip(t, iq):
        if ti >= a.t0 and abs(ii - i0) >= 0.9 * abs(di):
            t90 = ti - a.t0
            break
    if t90 is not None:
        ok = "CUMPLE" if t90 <= 0.05 * 1.2 else "NO CUMPLE"
        print("  t90 (90 %% del delta): %.1f ms  -> criterio 50 ms (+20 %% = 60 ms): %s" % (t90 * 1000, ok))

    # sostenimiento tras volver a la banda
    if a.banda:
        lo, hi = a.banda
        t_reg = None
        for ti, ui in zip(t, u):
            if ti > a.tf and lo <= ui <= hi:
                t_reg = ti
                break
        if t_reg is not None:
            t_fin = None
            for ti, ii in zip(t, iq):
                if ti >= t_reg and abs(ii - i0) <= 0.1 * abs(di):
                    t_fin = ti
                    break
            if t_fin is not None:
                print("  La tension vuelve a la banda en t = %.3f s; el aporte adicional"
                      " se retira en t = %.3f s -> sostenimiento ~ %.0f ms (requisito 500 ms)"
                      % (t_reg, t_fin, (t_fin - t_reg) * 1000))


# ---------------------------------------------------------------- grafica
def graficar(path, t, y, nombre, t0, r):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(t, y, lw=1.6, color="#0F4761", label=nombre[:60])
    ax.axhline(r["y_obj"], color="0.4", lw=0.8, ls="--", label="valor esperado")
    for s in (+1, -1):
        ax.axhline(r["y_obj"] + s * 0.03 * abs(r["delta"]), color="0.6", lw=0.6, ls=":")
    ax.axvline(t0 + r["tr"], color="#C0504D", lw=0.9, label="Tr = %.2f s" % r["tr"])
    ax.axvline(t0 + r["te"], color="#4F8A3C", lw=0.9, label="Te = %.2f s" % r["te"])
    ax.set_xlabel("Tiempo (s)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    out = os.path.splitext(path)[0] + "_tiempos.png"
    fig.savefig(out, dpi=150)
    print("  Grafica guardada en:", out)


# ---------------------------------------------------------------- main
def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)

    c = sp.add_parser("columnas")
    c.add_argument("csv")
    c.set_defaults(f=lambda a: [print("[%d] %s" % (i, n)) for i, n in enumerate(leer_csv(a.csv)[0])])

    c = sp.add_parser("tiempos")
    c.add_argument("csv")
    c.add_argument("--col", required=True, help="texto contenido en el nombre de la columna")
    c.add_argument("--t0", type=float, required=True, help="instante del escalon (s)")
    c.add_argument("--delta", type=float, help="delta esperado (si no, se usa final - inicial)")
    c.add_argument("--trmax", type=float)
    c.add_argument("--temax", type=float)
    c.set_defaults(f=cmd_tiempos)

    c = sp.add_parser("estatismo")
    c.add_argument("--df", type=float, required=True, help="escalon de frecuencia (Hz)")
    c.add_argument("--db", type=float, default=0.03, help="banda muerta (Hz)")
    c.add_argument("--p0", type=float, required=True)
    c.add_argument("--p1", type=float, required=True)
    c.add_argument("--pn", type=float, required=True)
    c.add_argument("--fn", type=float, default=60.0)
    c.add_argument("--r", type=float, help="estatismo ajustado en el modelo (%%)")
    c.set_defaults(f=cmd_estatismo)

    c = sp.add_parser("iq")
    c.add_argument("csv")
    c.add_argument("--colu", required=True)
    c.add_argument("--coliq", required=True)
    c.add_argument("--t0", type=float, required=True, help="inicio del hueco (s)")
    c.add_argument("--tf", type=float, required=True, help="fin del hueco (s)")
    c.add_argument("--k", type=float, default=2.0)
    c.add_argument("--imax", type=float, default=1.0)
    c.add_argument("--banda", type=float, nargs=2, metavar=("UMIN", "UMAX"))
    c.set_defaults(f=cmd_iq)

    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
