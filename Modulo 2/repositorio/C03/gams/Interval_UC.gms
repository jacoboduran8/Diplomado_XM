

***************************************************************
*** PARAMETERS
***************************************************************

$include Input_Data.gms

parameter g_wind(t,w,u);

*BEST GUESS
g_wind(t,w,'u1')=w_det(t,w);
*UPPER LIMIT
*g_wind(t,w,'u2')=wind_robust(t,w,'col1')$(mod(ord(t),2) = 1)+(wind_robust(t,w,'col2'))$(mod(ord(t),2) = 0);
g_wind(t,w,'u2')=wind_robust(t,w,'col1');
*LOWER LIMIT
*g_wind(t,w,'u3')=wind_robust(t,w,'col1')$(mod(ord(t),2) = 0)+(wind_robust(t,w,'col2'))$(mod(ord(t),2) = 1);
g_wind(t,w,'u3')=wind_robust(t,w,'col2');


***************************************************************
*** VARIABLES
***************************************************************

variable obj objective function variable

variable c_aux(t) auxilliary variable

variable c(t,u,i) operation cost in each time period

positive variable g(t,u,i) generator outputs

positive variable g_lin(t,u,i,b) generator block outputs

binary variable suc(t,i,j) start up cost

variable pf(t,u,l) power flow through lines

binary variable x(t,i) binary variable equal to 1 if generator is producing, and 0 otherwise

binary variable y(t,i) binary variable equal to 1 if generator is start-up, and 0 otherwise

binary variable z(t,i) binary variable equal to 1 if generator is shut-down, and 0 otherwise

variable theta(t,u,s) bus voltage angles

positive variable curt(t,w,u) wind curtailment

positive variable ll(t,u,s) unserved load

***************************************************************
*** EQUATION DECLARATION
***************************************************************

equations

cost objective function
cost_aux(t) auxilliary equation
bin_set1(t,i) setting start-up binary variables
bin_set10(t,i) setting start-up binary variables
bin_set2(t,i) setting start-up binary variables
cost_sum(t,u,i) generation cost summation
gen_sum(t,u,i) summing the generation of blocks per generator
gen_min(t,u,i) genertor minimum output
block_output(t,u,i,b) limiting the output of each generator block
min_updown_1(t,i) minimum updown time constraint 1
min_updown_2(t,i) minimum updown time constraint 2
min_updown_3(t,i) minimum updown time constraint 3
ramp_limit_min(t,u,i) ramp-down limit
ramp_limit_max(t,u,i) ramp-up limit
ramp_limit_min_1(u,i) ramp-down limit for the first time period
ramp_limit_max_1(u,i) ramp-up limit for the first time period
ramp_det_dn(t,u,i)
ramp_det_up(t,u,i)
ramp_lower_up(t,i)
ramp_upper_dn(t,u,i)
start_up_cost1(t,i,j) stairwise linear cost function - equation 1
start_up_cost2(t,i) stairwise linear cost function - equation 2
power_balance(t,u,s) power balance for each bus
line_flow(t,u,l) defining power flow through lines
line_capacity_min(t,u,l) line capacitiy negative limit
line_capacity_max(t,u,l) line capacitiy positive limit
voltage_angles_min(t,u,s) voltage angles negative limit
voltage_angles_max(t,u,s) voltage angles positive limit
curt_cons(t,w,u) wind curtailment constraint
;

***************************************************************
*** SETTINGS
***************************************************************

*setting the reference bus
theta.fx (t,u,'s101') = 0;

*needed for running twice through the same set in a single equation
alias (t,tt);
alias (u,uu);

***************************************************************
*** EQUATIONS
***************************************************************

cost..
         obj =e= sum(t,c_aux(t));

cost_aux(t)..
         c_aux(t) =e= sum((i,u)$(ord(u)=1),c(t,u,i))+sum((w,u)$(ord(u)=1),curt(t,w,u))*ws_penalty
*+sum((s,u)$(ord(u)=1),ll(t,u,s))*voll;
         ;

bin_set1(t,i)$(ord(t) gt 1)..
         y(t,i) - z(t,i) =e= x(t,i) - x(t-1,i);

bin_set10(t,i)$(ord(t) = 1)..
         y(t,i) - z(t,i) =e= x(t,i) - onoff_t0(i);

bin_set2(t,i)..
         y(t,i) + z(t,i) =l= 1;

cost_sum(t,u,i)$(ord(u)=1)..
         c(t,u,i) =e= a(i)*x(t,i) + sum(b,g_lin(t,u,i,b)*k(i,b)) + sum(j,suc_sw(i,j)*suc(t,i,j));

gen_sum(t,u,i)..
         g(t,u,i) =e= sum(b,g_lin(t,u,i,b));

gen_min(t,u,i)..
         g(t,u,i) =g= g_min(i)*x(t,i);

block_output(t,u,i,b)..
         g_lin(t,u,i,b) =l= g_max(i,b)*x(t,i);

min_updown_1(t,i)$(L_up_min(i)+L_down_min(i) gt 0 and ord(t) le L_up_min(i)+L_down_min(i))..
         x(t,i) =e= onoff_t0(i);

min_updown_2(t,i)..
         sum(tt$(ord(tt) ge ord(t)-g_up(i)+1 and ord(tt) le ord(t)),y(tt,i)) =l= x(t,i);

min_updown_3(t,i)..
         sum(tt$(ord(tt) ge ord(t)-g_down(i)+1 and ord(tt) le ord(t)),z(tt,i)) =l= 1-x(t,i);

ramp_limit_min(t,u,i)$(ord(t) gt 1)..
         -ramp_down(i) =l= g(t,u,i) - g(t-1,u,i);

ramp_limit_max(t,u,i)$(ord(t) gt 1)..
         ramp_up(i) =g= g(t,u,i) - g(t-1,u,i);

ramp_limit_min_1(u,i)..
         -ramp_down(i) =l= g('t1',u,i) - g_0(i);

ramp_limit_max_1(u,i)..
         ramp_up(i) =g= g('t1',u,i) - g_0(i);

ramp_det_dn(t,u,i)$(ord(t) lt card(t))..
         g(t,'u1',i) - g(t+1,'u3',i) =l= ramp_down(i);

ramp_det_up(t,u,i)$(ord(t) lt card(t))..
         -g(t,'u1',i) + g(t+1,'u2',i) =l= ramp_up(i);

ramp_lower_up(t,i)$(ord(t) lt card(t))..
         -g(t,'u3',i) + g(t+1,'u2',i) =l= ramp_up(i);

ramp_upper_dn(t,u,i)$(ord(t) lt card(t))..
         g(t,'u2',i) - g(t+1,'u3',i) =l= ramp_down(i);

start_up_cost1(t,i,j)..
         suc(t,i,j) =l= sum(tt$(ord(tt) lt ord(t) and ord(tt) ge suc_sl(i,j) and ord(tt) le suc_sl(i,j+1)-1),z(t-ord(j),i))+
         1$(ord(j) lt card(j) and count_off_init(i)+ord(t)-1 ge suc_sl(i,j) and count_off_init(i)+ord(t)-1 lt suc_sl(i,j+1))+
         1$(ord(j) = card(j) and count_off_init(i)+ord(t)-1 ge suc_sl(i,j));

start_up_cost2(t,i)..
         sum(j,suc(t,i,j)) =e= y(t,i);

power_balance(t,u,s)..
         sum(i$(gen_map(i,s)),g(t,u,i))
         +sum(w$(w_map(w,s)),g_wind(t,w,u)-curt(t,w,u))
         -sum(l$(line_map(l,s) <> 0),pf(t,u,l)*line_map(l,s)) =e= d(t,s)
*-ll(t,u,s)
         ;

line_flow(t,u,l)..
         pf(t,u,l) =e= admitance(l)*sum(s$(line_map(l,s) <> 0),theta(t,u,s)*line_map(l,s));

line_capacity_min(t,u,l)..
         pf(t,u,l) =g= -l_max(l)*line_capacity;

line_capacity_max(t,u,l)..
         pf(t,u,l) =l= l_max(l)*line_capacity;

voltage_angles_min(t,u,s)..
         theta(t,u,s) =g= -pi;

voltage_angles_max(t,u,s)..
         theta(t,u,s) =l= pi;

curt_cons(t,w,u)..
         curt(t,w,u) =l= g_wind(t,w,u);

***************************************************************
*** SOLVE
***************************************************************

model ep /all/;

option reslim = 18000;
option Savepoint=1;
option optcr=0.005;
ep.optfile = 1;

ep.limrow =0;
ep.limcol =0;

file opt cplex option file /cplex.opt/;
put opt;
put 'threads 4'/;
put 'miptrace _UC_original_interval_4_04_0.csv'/;
putclose;

solve ep using mip minimizing obj;

parameter overall_suc, output_cost,time_elapsed;

overall_suc=sum((t,i,j), suc_sw(i,j)*suc.l(t,i,j));
output_cost=sum((t,u,i)$(ord(u)=1), a(i)*x.l(t,i) + sum(b,g_lin.l(t,u,i,b)*k(i,b)));
time_elapsed = ep.etSolver;

Execute_Unload '_UC_original_interval_4_04_0', obj, c_aux, c, g,x, y, z, curt, overall_suc,output_cost,time_elapsed;
