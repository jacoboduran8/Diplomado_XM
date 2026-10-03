from digestor import Data
from pyomo.environ import Set
from pyomo.environ import ConcreteModel, Param, Var, Objective, Constraint, NonNegativeReals, Binary, Reals, minimize, SolverFactory
from math import pi

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
m.p_init_onoff = Param(m.s_generators, initialize=lambda _, g : 1 if data.generators.loc[g, 'cON'] else 0)
m.p_suc_sl = Param(m.s_generators, m.s_segments, initialize=lambda _, g, j : data.generators.loc[g, j])

#parameter L_up_min(i) used for minimum up time constraints
m.p_l_up_min = Param(m.s_generators, initialize=lambda mo, g : min(len(data.s_periods), (mo.p_tmg[g] - mo.p_count_on[g]) if mo.p_init_onoff[g] else 0))

#parameter L_down_min(i) used for minimum up time constraints
m.p_l_down_min = Param(m.s_generators, initialize=lambda mo, g : min(len(data.s_periods), (mo.p_tmfl[g] + mo.p_count_off[g]) if not mo.p_init_onoff[g] else 0))

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

# Variables

m.v_c_aux = Var(m.s_periods, within=NonNegativeReals, doc="Auxilliary variable")
m.v_c = Var(m.s_periods, m.s_generators, within=NonNegativeReals, doc="Operation cost in each time period")
m.v_g = Var(m.s_periods, m.s_generators, within=NonNegativeReals, doc="Generator outputs")
m.v_g_lin = Var(m.s_periods, m.s_generators, m.s_blocks, within=NonNegativeReals, doc="Generator block outputs")

m.v_suc = Var(m.s_periods, m.s_generators, m.s_segments, within=Binary, doc="Start up cost")
m.v_x = Var(m.s_periods, m.s_generators, within=Binary, doc="Binary variable equal to 1 if generator is producing, and 0 otherwise")
m.v_y = Var(m.s_periods, m.s_generators, within=Binary, doc="Binary variable equal to 1 if generator is start-up, and 0 otherwise")
m.v_z = Var(m.s_periods, m.s_generators, within=Binary, doc="Binary variable equal to 1 if generator is shut-down, and 0 otherwise")

m.v_pf = Var(m.s_periods, m.s_lines, within=NonNegativeReals, doc="Power flow through lines")
m.v_theta = Var(m.s_periods, m.s_buses, within=Reals, doc="Bus voltage angles")
m.v_curt = Var(m.s_periods, m.s_wind, within=NonNegativeReals, doc="Wind curtailment")
m.v_ll = Var(m.s_periods, m.s_buses, within=NonNegativeReals, doc="Unserved load")

# Bounds
#setting the reference bus
m.v_theta[:, 's101'].fix(0)  # Assuming 's101' is the reference bus

# Objective

def obj(m):
    return sum(m.v_c_aux[t] for t in m.s_periods)
m.e_obj = Objective(rule=obj, sense=minimize)

# Constraints
def cost_aux(m, t):
    return m.v_c_aux[t] == sum(m.v_c[t, i] for i in m.s_generators) + sum(m.v_curt[t, w] for w in m.s_wind) * ws_penalty + sum(m.v_ll[t, s] for s in m.s_buses) * voll
m.e_cost_aux = Constraint(m.s_periods, rule=cost_aux)

def cost_sum(m, t, i):
    return m.v_c[t, i] == m.p_co_cost[i] * m.v_x[t, i] + sum(m.v_g_lin[t, i, b] * m.p_c1_cost[i, b] for b in m.s_blocks) + sum(m.p_su_cost[i, j] * m.v_suc[t, i, j] for j in m.s_segments)
m.e_cost_sum = Constraint(m.s_periods, m.s_generators, rule=cost_sum)

def startup_shutdown(m, t, i):
    return m.v_y[t, i] - m.v_z[t, i] == m.v_x[t, i] - (m.v_x[m.s_periods.prev(t), i] if t > m.s_periods.first() else m.p_init_onoff[i])
m.e_startup_shutdown = Constraint(m.s_periods, m.s_generators, rule=startup_shutdown)

def no_sumil_susd(m, t, i):
    return m.v_y[t, i] + m.v_z[t, i] <= 1
m.e_no_sumil_susd = Constraint(m.s_periods, m.s_generators, rule=no_sumil_susd)

def gen_sum(m, t, i):
    return m.v_g[t, i] == sum(m.v_g_lin[t, i, b] for b in m.s_blocks)
m.e_gen_sum = Constraint(m.s_periods, m.s_generators, rule=gen_sum)

def gen_min(m, t, i):
    return m.v_g[t, i] >= m.p_mt[i] * m.v_x[t, i]
m.e_gen_min = Constraint(m.s_periods, m.s_generators, rule=gen_min)

def block_output(m, t, i, b):
    return m.v_g_lin[t, i, b] <= m.p_block_cap[i, b] * m.v_x[t, i]
m.e_block_output = Constraint(m.s_periods, m.s_generators, m.s_blocks, rule=block_output)

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
        return m.v_g[t, i] - m.v_g[m.s_periods.prev(t), i] >= -m.p_gen_dr[i]
    else:
        return m.v_g[t, i] - m.p_g_init[i] >= -m.p_gen_dr[i]
m.e_ramp_limit_min = Constraint(m.s_periods, m.s_generators, rule=ramp_limit_min)

def ramp_limit_max(m, t, i):
    if t > m.s_periods.first():
        return m.v_g[t, i] - m.v_g[m.s_periods.prev(t), i] <= m.p_gen_ur[i]
    else:
        return m.v_g[t, i] - m.p_g_init[i] <= m.p_gen_ur[i]
m.e_ramp_limit_max = Constraint(m.s_periods, m.s_generators, rule=ramp_limit_max)

def start_up_cost1(m, t, i, j):
    return (m.v_suc[t, i, j] <= 
            sum(m.v_z[tt, i] for tt in m.s_periods if tval(tt) >= tval(t) - m.p_suc_sl[i, j] + 1 and tval(tt) <= tval(t))
            + (1 if m.s_segments.ord(j) < len(m.s_segments) and m.p_count_off[i] + tval(t) - 1 >= m.p_suc_sl[i, j] and m.p_count_off[i] + tval(t) - 1 < m.p_suc_sl[i, m.s_segments.next(j)] else 0)
            + (1 if m.s_segments.ord(j) == len(m.s_segments) and m.p_count_off[i] + tval(t) - 1 >= m.p_suc_sl[i, j] else 0)
            )
m.e_start_up_cost1 = Constraint(m.s_periods, m.s_generators, m.s_segments, rule=start_up_cost1)

def start_up_cost2(m, t, i):
    return sum(m.v_suc[t, i, j] for j in m.s_segments) == m.v_y[t, i]
m.e_start_up_cost2 = Constraint(m.s_periods, m.s_generators, rule=start_up_cost2)

def power_balance(m, t, s):
    return (sum(m.v_g[t, i] for i in m.s_generators if m.t_gen_map[i, s]) 
            + sum(m.wind_profile[w, t] - m.v_curt[t, w] for w in m.s_wind if m.t_wind_map[w, s])
            - sum(m.v_pf[t, l] * m.line_map[l, s] for l in m.s_lines if m.line_map[l, s] != 0)
            == m.load_profile[s, t] - m.v_ll[t, s])
m.e_power_balance = Constraint(m.s_periods, m.s_buses, rule=power_balance)

def curt_cons(m, t, w):
    return m.v_curt[t, w] <= m.wind_profile[w, t]
m.e_curt_cons = Constraint(m.s_periods, m.s_wind, rule=curt_cons)

def line_flow(m, t, l, s):
    return m.v_pf[t, l] == sBase *m.line_y[l] * sum(m.v_theta[t, s] * m.line_map[l, s] for s in m.s_buses if m.line_map[l, s] != 0)
m.e_line_flow = Constraint(m.s_periods, m.s_lines, m.s_buses, rule=line_flow)

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

## Solve
m.write("UC_UW.lp")
solver = SolverFactory("highs")
solver_options = {}
# solver.set_options(solver_options)

results = solver.solve(m, tee=True)
m.write("UC_UW.sol")