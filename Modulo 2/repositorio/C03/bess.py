uninodal: bool = False
use_saeb: bool = False

from digestor import Data
from pyomo.environ import (
    ConcreteModel, Set, Param, Var, Objective, Constraint, 
    NonNegativeReals, Binary, Reals, minimize, SolverFactory,
    SolverStatus, TerminationCondition
    )
from math import pi
from pandas import DataFrame

data = Data()
m = ConcreteModel(name="deterministic_model")

# Sets
m.s_buses = Set(initialize=data.s_bus)
m.s_periods = Set(initialize=data.s_periods, ordered=True)

m.s_generators = Set(initialize=data.s_generators)
m.s_blocks = Set(initialize=data.s_blocks)
m.s_segments = Set(initialize=data.s_segments)

m.s_lines = Set(initialize=data.s_lines)

m.s_wind = Set(initialize=data.s_wind)

m.s_bess = Set(initialize=data.s_bess)

# Preprocesos
ws_penalty = 10000
voll = 500000
sBase = 100
tval = lambda t: int(t.replace('t', ''))

# Parameters
m.p_cen = Param(m.s_generators, initialize=data.generators['Cap'].to_dict())
m.p_count_on = Param(m.s_generators, initialize=data.generators['cON'].to_dict())
m.p_count_off = Param(m.s_generators, initialize=data.generators['cOFF'].to_dict())
m.p_gen_ur = Param(m.s_generators, initialize=data.generators['UR'].to_dict())
m.p_gen_dr = Param(m.s_generators, initialize=data.generators['DR'].to_dict())
m.p_tmfl = Param(m.s_generators, initialize=data.generators['TMFL'].to_dict())
m.p_tmg = Param(m.s_generators, initialize=data.generators['TMG'].to_dict())
m.p_mt = Param(m.s_generators, initialize=data.generators['MT'].to_dict())
m.p_g_init = Param(m.s_generators, initialize=data.generators['G0'].to_dict())
m.p_init_onoff = Param(m.s_generators, initialize=lambda mo, g : 1 if (mo.p_count_on[g] > 0 and mo.p_g_init[g] > 0) else 0)
m.p_suc_sl = Param(m.s_generators, m.s_segments, initialize=lambda _, g, j : data.generators.loc[g, j])

# Warm about inconsistent initial on/off status
for g in m.s_generators:
    if m.p_init_onoff[g] and not m.p_g_init[g]:
        print(f"Warning: Generator {g} is initially on but its initial generation {m.p_g_init[g]} is zero.")
    if not m.p_init_onoff[g] and m.p_g_init[g] >= m.p_mt[g]:
        print(f"Warning: Generator {g} is initially off but its initial generation {m.p_g_init[g]} is greater than 0.")

#parameter L_up_min(i) used for minimum up time constraints
m.p_l_up_min = Param(m.s_generators, initialize=lambda mo, g : min(len(mo.s_periods), max(0, mo.p_tmg[g] - mo.p_count_on[g]) if mo.p_init_onoff[g] else 0))

#parameter L_down_min(i) used for minimum up time constraints
m.p_l_down_min = Param(m.s_generators, initialize=lambda mo, g : min(len(mo.s_periods), max(0, mo.p_tmfl[g] + mo.p_count_off[g]) if not mo.p_init_onoff[g] else 0))

m.t_gen_map = Param(m.s_generators, m.s_buses, initialize=lambda _, g, s : 1 if data.generators.loc[g, 'bus'] == s else 0)
m.p_block_cap = Param(m.s_generators, m.s_blocks, initialize=lambda _, g, b : data.generators.loc[g, b])

m.p_co_cost = Param(m.s_generators, initialize=lambda _, g : data.generators.loc[g, 'C0'])
m.p_c1_cost = Param(m.s_generators, m.s_blocks, initialize=lambda _, g, b : data.gen_cost.query("gen == @g and block == @b").loc[g,'Cost'])
m.p_su_cost = Param(m.s_generators, m.s_segments, initialize=lambda _, g, j : data.gen_su_cost.query("gen == @g and segment == @j").loc[g,'Cost'])

m.line_capacity = Param(m.s_lines, initialize=lambda _, l : data.lines.loc[l, 'cap'])
m.line_y = Param(m.s_lines, initialize=lambda _, l : data.lines.loc[l, 'admittance'])
m.line_map = Param(m.s_lines, m.s_buses, initialize=lambda _, l, s : 1 if data.lines.loc[l, 'from'] == s else -1 if data.lines.loc[l, 'to'] == s else 0)

m.load_profile = Param(m.s_buses, m.s_periods, initialize=lambda _, s, t : data.loads.loc[t, s], default = 0)
m.wind_profile = Param(m.s_wind, m.s_periods, initialize=lambda _, w, t : data.wind.loc[t, w])
m.t_wind_map = Param(m.s_wind, m.s_buses, initialize=lambda _, w, s : 1 if data.wind.loc['bus id', w] == s else 0)

m.p_bess_cap = Param(m.s_bess, initialize=lambda _, b : data.bess.loc[b, 'Cap'])
m.p_soc_mt = Param(m.s_bess, initialize=lambda _, b : data.bess.loc[b, 'socmt'])
m.p_bess_pd = Param(m.s_bess, initialize=lambda _, b : data.bess.loc[b, 'pd'])
m.p_bess_pc = Param(m.s_bess, initialize=lambda _, b : data.bess.loc[b, 'pc'])
m.p_bess_soc_ini = Param(m.s_bess, initialize=lambda _, b : data.bess.loc[b, 'soc0'])
m.p_bess_efic = Param(m.s_bess, initialize=lambda _, b : data.bess.loc[b, 'efic'])
m.p_bess_Cefid = Param(m.s_bess, initialize=lambda _, b : 1 / data.bess.loc[b, 'efid'])
m.p_bess_loss = Param(m.s_bess, initialize=lambda _, b : data.bess.loc[b, 'loss'])
m.t_bess_map = Param(m.s_bess, m.s_buses, initialize=lambda _, b, s : 1 if data.bess.loc[b, 'bus'] == s else 0)

# Variables

m.v_c_aux = Var(m.s_periods, within=NonNegativeReals, doc="Auxilliary variable")
m.v_c = Var(m.s_periods, m.s_generators, within=NonNegativeReals, doc="Operation cost in each time period")
m.v_g = Var(m.s_periods, m.s_generators, within=NonNegativeReals, doc="Generator outputs")

m.v_suc = Var(m.s_periods, m.s_generators, m.s_segments, within=Binary, doc="Start up cost")
m.v_x = Var(m.s_periods, m.s_generators, within=Binary, doc="Binary variable equal to 1 if generator is producing, and 0 otherwise")
m.v_y = Var(m.s_periods, m.s_generators, within=Binary, doc="Binary variable equal to 1 if generator is start-up, and 0 otherwise")
m.v_z = Var(m.s_periods, m.s_generators, within=Binary, doc="Binary variable equal to 1 if generator is shut-down, and 0 otherwise")

m.v_pf = Var(m.s_periods, m.s_lines, within=Reals, doc="Power flow through lines")
m.v_theta = Var(m.s_periods, m.s_buses, within=Reals, doc="Bus voltage angles")
m.v_curt = Var(m.s_periods, m.s_wind, within=NonNegativeReals, doc="Wind curtailment")
m.v_ll = Var(m.s_periods, m.s_buses, within=NonNegativeReals, doc="Unserved load")
m.v_sl = Var(m.s_periods, m.s_buses, within=NonNegativeReals, doc="Slack load")

m.v_bess_soc = Var(m.s_periods, m.s_bess, within=NonNegativeReals, doc="State of charge of BESS")
m.v_bess_pd = Var(m.s_periods, m.s_bess, within=NonNegativeReals, doc="BESS discharging power")
m.v_bess_pc = Var(m.s_periods, m.s_bess, within=NonNegativeReals, doc="BESS charging power")

# Bounds
#setting the reference bus
m.v_theta[:, 's101'].fix(0)  # Assuming 's101' is the reference bus

# Objective

def obj(m):
    return sum(m.v_c_aux[t] for t in m.s_periods)
m.e_obj = Objective(rule=obj, sense=minimize)

# Constraints
def cost_aux(m, t):
    return m.v_c_aux[t] == sum(m.v_c[t, i] for i in m.s_generators) + sum(m.v_curt[t, w] for w in m.s_wind) * ws_penalty + sum(m.v_ll[t, s] + m.v_sl[t, s] for s in m.s_buses) * voll
m.e_cost_aux = Constraint(m.s_periods, rule=cost_aux)

def cost_sum(m, t, i):
    return m.v_c[t, i] == m.p_co_cost[i] * m.v_x[t, i] + m.v_g[t, i] * m.p_c1_cost[i, "b1"] + m.p_su_cost[i, "j1"] * m.v_y[t, i]
m.e_cost_sum = Constraint(m.s_periods, m.s_generators, rule=cost_sum)

def startup_shutdown(m, t, i):
    return m.v_y[t, i] - m.v_z[t, i] == m.v_x[t, i] - (m.v_x[m.s_periods.prev(t), i] if t > m.s_periods.first() else m.p_init_onoff[i])
m.e_startup_shutdown = Constraint(m.s_periods, m.s_generators, rule=startup_shutdown)

def no_sumil_susd(m, t, i):
    return m.v_y[t, i] + m.v_z[t, i] <= 1
m.e_no_sumil_susd = Constraint(m.s_periods, m.s_generators, rule=no_sumil_susd)

def gen_min(m, t, i):
    return m.v_g[t, i] >= m.p_mt[i] * m.v_x[t, i]
m.e_gen_min = Constraint(m.s_periods, m.s_generators, rule=gen_min)

def block_output(m, t, i):
    return m.v_g[t, i] <= sum(m.p_block_cap[i, b] for b in m.s_blocks) * m.v_x[t, i]
m.e_block_output = Constraint(m.s_periods, m.s_generators, rule=block_output)

def min_updown_1(m, t, i):
    return m.v_x[t, i] == m.p_init_onoff[i] if tval(t) <= m.p_l_up_min[i] + m.p_l_down_min[i] else Constraint.Skip
m.e_min_updown_1 = Constraint(m.s_periods, m.s_generators, rule=min_updown_1)

def min_updown_2(m, t, i):
    return sum(m.v_y[tt, i] for tt in m.s_periods if tval(tt) >= tval(t) - m.p_tmg[i] + 1 and tval(tt) <= tval(t)) <= m.v_x[t, i]
m.e_min_updown_2 = Constraint(m.s_periods, m.s_generators, rule=min_updown_2)

def min_updown_3(m, t, i):
    return sum(m.v_z[tt, i] for tt in m.s_periods if tval(tt) >= tval(t) - m.p_tmfl[i] + 1 and tval(tt) <= tval(t)) <= 1 - m.v_x[t, i]
m.e_min_updown_3 = Constraint(m.s_periods, m.s_generators, rule=min_updown_3)

def ramp_limit_min(m, t, i):
    if t > m.s_periods.first():
        return m.v_g[t, i] - m.v_g[m.s_periods.prev(t), i] >= - m.p_gen_dr[i] * m.v_x[m.s_periods.prev(t), i] - m.p_mt[i] * m.v_z[t, i]
    else:
        return m.v_g[t, i] - m.p_g_init[i] >= - (m.p_gen_dr[i] if m.p_g_init[i] else m.p_mt[i])
m.e_ramp_limit_min = Constraint(m.s_periods, m.s_generators, rule=ramp_limit_min)

def ramp_limit_max(m, t, i):
    if t > m.s_periods.first():
        return m.v_g[t, i] - m.v_g[m.s_periods.prev(t), i] <= m.p_gen_ur[i] * m.v_x[t, i] + m.p_mt[i] * m.v_y[t, i]
    else:
        return m.v_g[t, i] - m.p_g_init[i] <= m.p_gen_ur[i] * m.v_x[t, i] + m.p_mt[i] * m.v_y[t, i]
m.e_ramp_limit_max = Constraint(m.s_periods, m.s_generators, rule=ramp_limit_max)

def power_balance(m, t, s):
    return (sum(m.v_g[t, i] for i in m.s_generators if m.t_gen_map[i, s]) 
            + sum(m.wind_profile[w, t] - m.v_curt[t, w] for w in m.s_wind if m.t_wind_map[w, s])
            - sum(m.v_pf[t, l] * m.line_map[l, s] for l in m.s_lines if m.line_map[l, s] != 0)
            + sum(m.v_bess_pd[t, b] - m.v_bess_pc[t, b] for b in m.s_bess if m.t_bess_map[b, s])
            == m.load_profile[s, t] - m.v_ll[t, s] + m.v_sl[t, s])
m.e_power_balance = Constraint(m.s_periods, m.s_buses, rule=power_balance)

def uninodal_balance(m, t):
    return (
        sum(m.v_g[t, i] for i in m.s_generators) 
        + sum(m.wind_profile[w, t] - m.v_curt[t, w] for w in m.s_wind)
        + sum(m.v_bess_pd[t, b] - m.v_bess_pc[t, b] for b in m.s_bess)
        == sum(m.load_profile[s, t] - m.v_ll[t, s] + m.v_sl[t, s] for s in m.s_buses)
    )
m.e_uninodal_balance = Constraint(m.s_periods, rule=uninodal_balance)

def bess_storage(m, t, b):
    if t > m.s_periods.first():
        return (
            m.v_bess_soc[t, b] == m.v_bess_soc[m.s_periods.prev(t), b] * (1 - m.p_bess_loss[b]) 
            + m.p_bess_efic[b] * m.v_bess_pc[t, b] / m.p_bess_cap[b]
            - m.p_bess_Cefid[b] * m.v_bess_pd[t, b] / m.p_bess_cap[b]
        )
    else:
        return (
            m.v_bess_soc[t, b] == m.p_bess_soc_ini[b] * (1 - m.p_bess_loss[b])
            + m.p_bess_efic[b] * m.v_bess_pc[t, b] / m.p_bess_cap[b]
            - m.p_bess_Cefid[b] * m.v_bess_pd[t, b] / m.p_bess_cap[b]
        )
m.e_bess_storage = Constraint(m.s_periods, m.s_bess, rule=bess_storage)

def min_bess_soc(m, t, b):
    return m.v_bess_soc[t, b] >= m.p_soc_mt[b]
m.e_min_bess_soc = Constraint(m.s_periods, m.s_bess, rule=min_bess_soc)

def max_bess_soc(m, t, b):
    return m.v_bess_soc[t, b] <= 1
m.e_max_bess_soc = Constraint(m.s_periods, m.s_bess, rule=max_bess_soc)

def max_bess_charge(m, t, b):
    return m.v_bess_pc[t, b] <= m.p_bess_pd[b]
m.e_max_bess_charge = Constraint(m.s_periods, m.s_bess, rule=max_bess_charge)

def max_bess_discharge(m, t, b):
    return m.v_bess_pd[t, b] <= m.p_bess_pd[b]
m.e_max_bess_discharge = Constraint(m.s_periods, m.s_bess, rule=max_bess_discharge)

def curt_cons(m, t, w):
    return m.v_curt[t, w] <= m.wind_profile[w, t]
m.e_curt_cons = Constraint(m.s_periods, m.s_wind, rule=curt_cons)

def line_flow(m, t, l):
    return m.v_pf[t, l] == m.line_y[l] * sum(m.v_theta[t, s] * m.line_map[l, s] for s in m.s_buses if m.line_map[l, s] != 0)
m.e_line_flow = Constraint(m.s_periods, m.s_lines, rule=line_flow)

def line_capacity_min(m, t, l):
    return m.v_pf[t, l] >= -m.line_capacity[l]
m.e_line_capacity_min = Constraint(m.s_periods, m.s_lines, rule=line_capacity_min)

def line_capacity_max(m, t, l):
    return m.v_pf[t, l] <= m.line_capacity[l]
m.e_line_capacity_max = Constraint(m.s_periods, m.s_lines, rule=line_capacity_max)

def voltage_angles_min(m, t, s):
    return m.v_theta[t, s] >= -pi
m.e_voltage_angles_min = Constraint(m.s_periods, m.s_buses, rule=voltage_angles_min)

def voltage_angles_max(m, t, s):
    return m.v_theta[t, s] <= pi
m.e_voltage_angles_max = Constraint(m.s_periods, m.s_buses, rule=voltage_angles_max)

# Controls
# Disable by default
m.e_uninodal_balance.deactivate()

if not use_saeb:
    m.e_bess_storage.deactivate()
    m.e_min_bess_soc.deactivate()
    m.e_max_bess_soc.deactivate()
    m.e_max_bess_charge.deactivate()
    m.e_max_bess_discharge.deactivate()

    m.v_bess_soc.fix(0)
    m.v_bess_pd.fix(0)
    m.v_bess_pc.fix(0)

# disable flow constraints
if uninodal:
    m.e_line_flow.deactivate()
    m.e_line_capacity_min.deactivate()
    m.e_line_capacity_max.deactivate()
    m.e_voltage_angles_min.deactivate()
    m.e_voltage_angles_max.deactivate()
    # set angles to 0
    m.v_theta.fix(0)

    m.e_power_balance.deactivate()
    m.e_uninodal_balance.activate()

## Solve
m.write("UC_UW.lp", io_options={'symbolic_solver_labels': True})
solver = SolverFactory("highs")
# options = {"time_limit": 3600, "write_iis_model_file": "iUC_UW.lp"}
options = {"time_limit": 3600}

try:
    results = solver.solve(m, options=options, tee=True)
except Exception as e:
    print(f"Solver encountered an error: {e}")
    exit()
# m.write("UC_UW.sol", io_options={'symbolic_solver_labels': True})

if (results.solver.status == SolverStatus.ok) and (results.solver.termination_condition == TerminationCondition.optimal):
    print("Optimal solution found")
    print(f"Objective value: {m.e_obj.expr():10.2f}")
else:
    print("Solver did not find an optimal solution")
    exit()

# generation report (to excel)
gen_report = DataFrame(
    index=m.s_periods,
    columns=m.s_generators,
    data=[[m.v_g[t, i].value for i in m.s_generators] for t in m.s_periods]
)
gen_report.to_excel("generation_report.xlsx")

status_report = DataFrame(
    index=m.s_periods,
    columns=m.s_generators,
    data=[[m.v_x[t, i].value for i in m.s_generators] for t in m.s_periods]
)
status_report.to_excel("status_report.xlsx")

ll_report = DataFrame(
    index=m.s_periods,
    columns=m.s_buses,
    data=[[- m.v_ll[t, s].value + m.v_sl[t, s].value for s in m.s_buses] for t in m.s_periods]
)
ll_report.to_excel("unserved_load.xlsx")

if not uninodal:
    flow_report = DataFrame(
        index=m.s_periods,
        columns=m.s_lines,
        data=[[m.v_pf[t, l].value for l in m.s_lines] for t in m.s_periods]
    )
    flow_report.to_excel("flow_report.xlsx")

bess_report = DataFrame(
    index=m.s_periods,
    columns=m.s_bess,
    data=[[m.v_bess_soc[t, b].value for b in m.s_bess] for t in m.s_periods]
)
bess_report.to_excel("bess_report.xlsx")

bess_power_report = DataFrame(
    index=m.s_periods,
    columns=m.s_bess,
    data=[[m.v_bess_pc[t, b].value - m.v_bess_pd[t, b].value for b in m.s_bess] for t in m.s_periods]
)
bess_power_report.to_excel("bess_power_report.xlsx")