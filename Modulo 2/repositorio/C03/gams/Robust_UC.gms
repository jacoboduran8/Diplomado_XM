$include Input_Data_for_Robust_UC.gms
*******************************************************************************
parameter Price_wind(t,wf);
parameter Price_load;

*Price_wind(t,wf)=100;
Price_wind(t,wf)=0;

Price_load = 1e6;
******************************
alias (t,tt);
alias (s,sf);

set sp /sp1*sp6/;
set ny(sp);
ny(sp)=no;
******************************
scalar predict_LB /0/;
parameter Tload(t);
Tload(t)=sum(s,d(t,s));

parameter wind_c(t,wf,sp);

wind_c(t,wf,'sp1')=wind_robust(t,wf,'col2');

wind_c(t,wf,'sp2')=w_det(t,wf);

wind_c(t,wf,'sp3')=wind_robust(t,wf,'col1');

wind_c(t,wf,'sp4')=wind_robust(t,wf,'col1');
wind_c(t,wf,'sp4')$(mod(ord(t),2)=1)=wind_robust(t,wf,'col2');

wind_c(t,wf,'sp5')=wind_robust(t,wf,'col1');
wind_c(t,wf,'sp5')$(mod(ord(t),2)=0)=wind_robust(t,wf,'col2');

wind_c(t,wf,'sp6')=wind_robust(t,wf,'col1');
wind_c(t,wf,'sp6')$((TLoad(t)-TLoad(t-1))>=0 and (TLoad(t)-TLoad(t+1))>=0)=wind_robust(t,wf,'col2');


parameter MCS_wind(t,wf,sp);
MCS_wind(t,wf,sp)$(ord(sp)<=6)=wind_c(t,wf,sp);
*---------------------------------------------------------------------
* Benders Relaxed Master Problem
*---------------------------------------------------------------------

*** VARIABLES
variable master_obj  objective variable
positive variable suc_p(t,i,j) stair wise start up cost
positive variable suc(t,i) stair wise start up cost
binary variable x(t,i) binary variable equal to 1 if generator is producing, and 0 otherwise
binary variable y(t,i) binary variable equal to 1 if generator is start-up, and 0 otherwise
binary variable z(t,i) binary variable equal to 1 if generator is shut-down, and 0 otherwise

positive variable wd(t,wf)      wind realization
positive variable wg(t,wf,sp)      wind usage
positive variable ws(t,wf,sp)      wind spill

variable cost
positive variable cost_ny(sp)
variable pf(t,l,sp) power flow through lines
variable theta(t,s,sp) bus voltage angles
positive variable g_lin(t,i,b,sp)
positive variable dc1(t,s,sp)
positive variable dc2(t,s,sp)

*************************** EQUATIONS for master problem***********************************************
equations

bin_set1(t,i) setting start-up binary variables
bin_set2(t,i) setting start-up binary variables
set_y(i) generating unit cannot be started in first time period if it was running in time period 0

min_updown_1(t,i) minimum down time constraint 1
min_updown_2(t,i) minimum down time constraint 2
min_updown_3(t,i) minimum down time constraint 3

start_up_cost1(t,i,j) stairwise linear cost function - equation 1
start_up_cost2(t,i) stairwise linear cost function - equation 2
start_up_cost3(t,i)
;

bin_set1(t,i)$(ord(t) gt 1)..y(t,i) - z(t,i) =e= x(t,i) - x(t-1,i);
bin_set2(t,i)..y(t,i) + z(t,i) =l= 1;
set_y(i)..y('t1',i) - z('t1',i) =e= x('t1',i) - onoff_t0(i);

min_updown_1(t,i)$(L_up_min(i)+L_down_min(i) gt 0 and ord(t) le L_up_min(i)+L_down_min(i))..x(t,i) =e= onoff_t0(i);
min_updown_2(t,i)..sum(tt$(ord(tt) ge ord(t)-g_up(i)+1 and ord(tt) le ord(t)),y(tt,i)) =l= x(t,i);
min_updown_3(t,i)..sum(tt$(ord(tt) ge ord(t)-g_down(i)+1 and ord(tt) le ord(t)),z(tt,i)) =l= 1-x(t,i);

start_up_cost1(t,i,j)..
         suc_p(t,i,j) =l= sum(tt$(ord(tt) lt ord(t) and ord(tt) ge suc_sl(i,j) and ord(tt) le suc_sl(i,j+1)-1),z(t-ord(j),i))+
         1$(ord(j) lt card(j) and count_off_init(i)+ord(t)-1 ge suc_sl(i,j) and count_off_init(i)+ord(t)-1 lt suc_sl(i,j+1))+
         1$(ord(j) = card(j) and count_off_init(i)+ord(t)-1 ge suc_sl(i,j));

start_up_cost2(t,i)..sum(j,suc_p(t,i,j)) =e= y(t,i);

start_up_cost3(t,i)..suc(t,i)=e=sum(j,suc_sw(i,j)*suc_p(t,i,j));

***********************************************************************************************

equations
total_cost
total_cost_ny(sp)
gen_min(t,i,sp) genertor minimum output
block_output(t,i,b,sp) limiting the output of each generator block
ramp_limit_min(t,i,sp) ramp-down limit
ramp_limit_max(t,i,sp) ramp-up limit
ramp_limit_min_1(i,sp) ramp-down limit for the first time period
ramp_limit_max_1(i,sp) ramp-up limit for the first time period

power_balance(t,s,sp) power balance for each bus
line_flow(t,l,sp) defining power flow through lines
line_capacity_min(t,l,sp) line capacitiy negative limit
line_capacity_max(t,l,sp) line capacitiy positive limit
voltage_angles_min(t,s,sp) voltage angles negative limit
voltage_angles_max(t,s,sp) voltage angles positive limit
wind_sp(t,wf,sp)
excut(t,sp)
excut2(t,sp)
;
***************************************************************
theta.fx (t,'s101',sp) = 0;
***************************************************************
total_cost..cost=e=sum(ny,cost_ny(ny));

total_cost_ny(ny)..cost_ny(ny)=e=sum((t,i),sum(b,g_lin(t,i,b,ny)*k(i,b))+x(t,i)*a(i))*1+sum((t,wf),Price_wind(t,wf)*(wind_c(t,wf,ny)-wg(t,wf,ny)))+ sum((t,i),suc(t,i));
*u1(t,i)
gen_min(t,i,ny)..sum(b,g_lin(t,i,b,ny)) =g= g_min(i)*x(t,i);
*u2(t,i,b)
block_output(t,i,b,ny)..-g_lin(t,i,b,ny) =g= -g_max(i,b)*x(t,i);
*u3(t,l)
line_flow(t,l,ny)..pf(t,l,ny) - admitance(l)*sum(s,theta(t,s,ny)*line_map(l,s))=e= 0;
*u4(t,i)
ramp_limit_min(t,i,ny)$(ord(t)>1).. sum(b,g_lin(t,i,b,ny)) - sum(b,g_lin(t-1,i,b,ny))=g= -ramp_down(i);

ramp_limit_min_1(i,ny)..sum(b,g_lin('t1',i,b,ny))=g= g_0(i)- ramp_down(i);
*u5(t,i)
ramp_limit_max(t,i,ny)$(ord(t)>1).. sum(b,g_lin(t-1,i,b,ny))- sum(b,g_lin(t,i,b,ny))=g= -ramp_up(i) ;

ramp_limit_max_1(i,ny).. -sum(b,g_lin('t1',i,b,ny)) =g= -(ramp_up(i)+g_0(i));
*u6(t,s)
power_balance(t,s,ny)..sum(i,sum(b,g_lin(t,i,b,ny))*gen_map(i,s)) - sum(l,admitance(l)*sum(sf,theta(t,sf,ny)*line_map(l,sf))*line_map(l,s)) + sum(wf,wg(t,wf,ny)*wind_map(wf,s))=e= d(t,s);
*u9(t,s)
line_capacity_min(t,l,ny)..admitance(l)*sum(s,theta(t,s,ny)*line_map(l,s)) =g= -l_max(l)*line_capacity;
*u10(t,s)
line_capacity_max(t,l,ny)..-admitance(l)*sum(s,theta(t,s,ny)*line_map(l,s)) =g= -l_max(l)*line_capacity;
*u7(t,s)
voltage_angles_min(t,s,ny)$(ord(s)>1)..theta(t,s,ny) =g= -pi;
*u8(t,s)
voltage_angles_max(t,s,ny)$(ord(s)>1)..-theta(t,s,ny) =g= -pi;

*wind_sp(t,wf,ny)..wg(t,wf,ny)+ws(t,wf,ny)=e=wind_c(t,wf,ny);

wind_sp(t,wf,ny)..wg(t,wf,ny)=l=wind_c(t,wf,ny);

excut(t,ny).. -sum(s,d(t,s))+ sum(wf,wg(t,wf,ny))=g= -sum(i,sum(b,g_max(i,b)*x(t,i)));

excut2(t,ny).. sum(s,d(t,s))- sum(wf,wg(t,wf,ny))=g= sum(i,g_min(i)*x(t,i));

*********************************************************************************
*****model predict economic
*******************************************************************************
equations
P_total_cost
P_total_cost_ny(sp)
P_gen_min(t,i,sp) genertor minimum output
P_block_output(t,i,b,sp) limiting the output of each generator block
P_ramp_limit_min(t,i,sp) ramp-down limit
P_ramp_limit_max(t,i,sp) ramp-up limit
P_ramp_limit_min_1(i,sp) ramp-down limit for the first time period
P_ramp_limit_max_1(i,sp) ramp-up limit for the first time period

P_power_balance(t,s,sp)
P_line_flow(t,l,sp)
P_voltage_angles_min(t,s,sp)
P_voltage_angles_max(t,s,sp)
P_line_capacity_min(t,l,sp)
P_line_capacity_max(t,l,sp)
P_wind_sp(t,wf,sp)
;

P_total_cost..cost=e=sum(ny,cost_ny(ny));

P_total_cost_ny(ny)..cost_ny(ny)=e=sum((t,i),sum(b,g_lin(t,i,b,ny)*k(i,b))+x.l(t,i)*a(i))*1+sum((t,wf),Price_wind(t,wf)*ws(t,wf,ny))
                                 +Price_load*sum((t,s),(dc1(t,s,ny)+dc2(t,s,ny))) + sum((t,i),suc.l(t,i));
*u1(t,i)
P_gen_min(t,i,ny)..sum(b,g_lin(t,i,b,ny)) =g= g_min(i)*x.l(t,i);
*u2(t,i,b)
P_block_output(t,i,b,ny)..-g_lin(t,i,b,ny) =g= -g_max(i,b)*x.l(t,i);
*u3(t,l)
P_line_flow(t,l,ny)..pf(t,l,ny) - admitance(l)*sum(s,theta(t,s,ny)*line_map(l,s))=e= 0;
*u4(t,i)
P_ramp_limit_min(t,i,ny)$(ord(t)>1).. sum(b,g_lin(t,i,b,ny)) - sum(b,g_lin(t-1,i,b,ny))=g= -ramp_down(i);

P_ramp_limit_min_1(i,ny)..sum(b,g_lin('t1',i,b,ny))=g= g_0(i)- ramp_down(i);
*u5(t,i)
P_ramp_limit_max(t,i,ny)$(ord(t)>1).. sum(b,g_lin(t-1,i,b,ny))- sum(b,g_lin(t,i,b,ny))=g= -ramp_up(i) ;

P_ramp_limit_max_1(i,ny).. -sum(b,g_lin('t1',i,b,ny))=g= -(ramp_up(i)+g_0(i));
*u6(t,s)
P_power_balance(t,s,ny)..sum(i,sum(b,g_lin(t,i,b,ny))*gen_map(i,s)) - sum(l,pf(t,l,ny)*line_map(l,s)) + sum(wf,wg(t,wf,ny)*wind_map(wf,s))+dc1(t,s,ny)-dc2(t,s,ny)=e= d(t,s);
*u7(t,s)
P_voltage_angles_min(t,s,ny)$(ord(s)>1)..theta(t,s,ny) =g= -pi;
*u8(t,s)
P_voltage_angles_max(t,s,ny)$(ord(s)>1)..-theta(t,s,ny) =g= -pi;
*u9(t,s)
P_line_capacity_min(t,l,ny)..pf(t,l,ny) =g= -l_max(l)*line_capacity;
*u10(t,s)
P_line_capacity_max(t,l,ny)..-pf(t,l,ny) =g= -l_max(l)*line_capacity;
*u11(t,wf)
P_wind_sp(t,wf,ny)..wg(t,wf,ny)+ws(t,wf,ny) =e= MCS_wind(t,wf,ny);

*******************************************************************************
*************equations for cut generating**************************************
*******************************************************************************

set iter /iter1*iter3000/;

set cutset(iter) 'optimal cut';
cutset(iter)=no;

set unbcutset(iter) 'feasibility cut';
unbcutset(iter)=no;

parameters
   cutconst1(iter)     'constant term in cuts'
   cutconst2(iter)     'constant term in cuts'
   cutcoeff3(iter,t,i)
   cutcoeff5(iter)
;
   cutconst1(iter)=0;
   cutconst2(iter)=0;
   cutcoeff3(iter,t,i)=0;
   cutcoeff5(iter)=0;

parameter xiter(iter,t,i);
          xiter(iter,t,i)=0;

equations
   cut(iter)           'Benders cut for optimal check'
   unboundedcut(iter)  'Benders cut for feasible check'
   cut0
;

cut(cutset).. master_obj =g=sum((t,i),suc(t,i))+cutconst2(cutset) + sum((t,i), cutcoeff3(cutset,t,i)*(x(t,i)-xiter(cutset,t,i)))
                                                                   +cutcoeff5(cutset)*sum((t,i),a(i)*(x(t,i)-xiter(cutset,t,i)));

cut0.. master_obj =g=sum((t,i),suc(t,i))+ sum(ny,sum((t,i),sum(b,g_lin(t,i,b,ny)*k(i,b))+x(t,i)*a(i))*1+sum((t,wf),Price_wind(t,wf)*ws(t,wf,ny)));

unboundedcut(cutset)..cutconst1(cutset) + sum((i,t), cutcoeff3(cutset,t,i)*(x(t,i)-xiter(cutset,t,i)))=l= 0;
*---------------------------------------------------------------------
* Benders optimality Subproblem (dual)
*---------------------------------------------------------------------

set iter2/oaiter1*oaiter500/;
set iter_cut(iter2);
iter_cut(iter2)=no;

parameter wind_iter(iter2,t,wf)
          u11_iter(iter2,t,wf);

wind_iter(iter2,t,wf)=0;
u11_iter(iter2,t,wf)=0;

*** VARIABLES
variable sub_obj_m sub objective value of the master OA
         sub_obj_s sub objective value of the sub OA

positive variables
u1(t,i)   dual variable for min output constrain
u2(t,i,b) dual variable for piece-wise max output constrains

u4(t,i)   dual variable for transit ramp down constrain
u5(t,i)   dual variable for transit ramp up constrain

u7(t,s)   dual variable for voltage angle constrain1
u8(t,s)   dual variable for voltage angle constrain2
u9(t,l)   dual variable for transmission constrain1
u10(t,l)   dual variable for transmission constrain2

variables
u3(t,l)   dual variable for power flow equation
u6(t,s)   dual variable for power balance constrain
u7_8(t)   dual variable for swing bus voltage angle constrain
u11(t,wf) dual variable for wind spill
beta
NL_value(iter2,t)

equations
d_obj_m master problem objective function1
d_obj_s master problem objective function2

dual1(t,i,b)
dual2(t,i,b)
dual3(t,l)
dual4(t,s)
dual4_1(t)
dual5_1(t,wf)
dual5_2(t,wf)
dual6_1(t,s)
dual6_2(t,s)
NL_part(iter2)
;

d_obj_m..sub_obj_m =l= sum((i,t),u1(t,i)*g_min(i)*x.l(t,i)) + sum(b,sum((i,t),-u2(t,i,b)*g_max(i,b)*x.l(t,i)))

            +sum((i,t),-u4(t,i)*ramp_down(i))+sum(i,u4('t1',i)*g_0(i))
            +sum((i,t),-u5(t,i)*ramp_up(i))+sum(i,u5('t1',i)*(-g_0(i)))

            +sum((t,s),u6(t,s)*d(t,s))
            +sum((t,i),a(i)*x.l(t,i))

            -pi*sum((t,s)$(ord(s)>1),u7(t,s)+u8(t,s))
            -sum((t,l),l_max(l)*line_capacity*(u9(t,l)+u10(t,l)))
            +beta
            + sum((t,i),suc.l(t,i));

d_obj_s..sub_obj_s =l= sum((i,t),u1(t,i)*g_min(i)*x.l(t,i)) + sum(b,sum((i,t),-u2(t,i,b)*g_max(i,b)*x.l(t,i)))

            +sum((i,t),-u4(t,i)*ramp_down(i))+sum(i,u4('t1',i)*g_0(i))
            +sum((i,t),-u5(t,i)*ramp_up(i))+sum(i,u5('t1',i)*(-g_0(i)))

            +sum((t,s),u6(t,s)*d(t,s))
            +sum((t,i),a(i)*x.l(t,i))

            -pi*sum((t,s)$(ord(s)>1),u7(t,s)+u8(t,s))
            -sum((t,l),l_max(l)*line_capacity*(u9(t,l)+u10(t,l)))
            +sum((t,wf),u11(t,wf)*wd.l(t,wf))
            + sum((t,i),suc.l(t,i));
*------------------------------------------------------------------------------
*g(t,i,b)
dual1(t,i,b)..u1(t,i)-u2(t,i,b)+ u4(t,i)-u5(t,i)-u4(t+1,i)+u5(t+1,i)+sum(s,u6(t,s)*gen_map(i,s))=l=k(i,b);
*p(T,i,b)
dual2(t,i,b)$(ord(t)=card(t))..u1(t,i)-u2(t,i,b)+ u4(t,i)-u5(t,i)+sum(s,u6(t,s)*gen_map(i,s))=l=k(i,b);
*pf(t,l)
dual3(t,l)..u3(t,l)-sum(s,u6(t,s)*line_map(l,s))+u9(t,l)-u10(t,l)=e=0;
*theta(c,s)
dual4(t,s)$(ord(s)>1)..-sum(l,admitance(l)*line_map(l,s)*u3(t,l))+ u7(t,s)-u8(t,s)=e=0;
*theta(t,s1)
dual4_1(t)..-sum(l,admitance(l)*line_map(l,'s101')*u3(t,l))+ u7_8(t)=e=0;
*wg
dual5_1(t,wf)..sum(s,u6(t,s)*wind_map(wf,s))+u11(t,wf)=l=0;
*ws
dual5_2(t,wf)..u11(t,wf)=l=Price_wind(t,wf);
*dc1(t,s)
dual6_1(t,s)..u6(t,s)=l=Price_load;
*dc2(t,s)
dual6_2(t,s)..-u6(t,s)=l=Price_load;

NL_part(iter_cut).. beta=l=sum((wf,t),-u11_iter(iter_cut,t,wf)*wind_iter(iter_cut,t,wf)+u11_iter(iter_cut,t,wf)*wd(t,wf)+u11(t,wf)*wind_iter(iter_cut,t,wf));

equations uncertainty_range_l(t,wf)
          uncertainty_range_u(t,wf)
;
uncertainty_range_l(t,wf)..wd(t,wf)=l=wind_robust(t,wf,'col1');
uncertainty_range_u(t,wf)..wd(t,wf)=g=wind_robust(t,wf,'col2');

************************models****************************************
model predict /
P_total_cost,
P_total_cost_ny,
P_gen_min,
P_block_output,
P_ramp_limit_min,
P_ramp_limit_max,
P_ramp_limit_min_1,
P_ramp_limit_max_1,

P_power_balance,
P_line_flow,
P_voltage_angles_min,
P_voltage_angles_max,
P_line_capacity_min,
P_line_capacity_max,
P_wind_sp
/;
predict.solprint=2;
predict.solvelink=2;
predict.reslim=86400;
predict.OptFile = 1;

model master /
bin_set1,
bin_set2,
set_y,
min_updown_1,
min_updown_2,
min_updown_3,
start_up_cost1,
start_up_cost2,
start_up_cost3,

cut,
cut0,
unboundedcut,

*$ontext
gen_min,
block_output,
ramp_limit_min,
ramp_limit_max,
ramp_limit_min_1,
ramp_limit_max_1,
power_balance,
wind_sp,
line_flow,
voltage_angles_min,
voltage_angles_max,
line_capacity_min,
line_capacity_max,
*$offtext

excut,
excut2
/;

master.solprint=2;
master.solvelink=2;
master.reslim=36000;
master.OptFile = 1;

model subproblem_m /
d_obj_m,
dual1,
dual2,
dual3,
dual4,
dual4_1,
dual5_1,
dual5_2,
dual6_1,
dual6_2,

uncertainty_range_l,
uncertainty_range_u,
NL_part
/;
subproblem_m.solprint=2;
subproblem_m.solvelink=2;
subproblem_m.OptFile = 1;

model subproblem_s /
d_obj_s,
dual1,
dual2,
dual3,
dual4,
dual4_1,
dual5_1,
dual5_2,
dual6_1,
dual6_2
/;
subproblem_s.solprint=2;
subproblem_s.solvelink=2;
subproblem_s.OptFile = 1;
*---------------------------------------------------------------------
* Benders Decomposition Initialization
*---------------------------------------------------------------------

display "------- BENDERS ALGORITHM ------";
scalar converged /0/;
scalar converged2 /0/;
scalar iteration;

scalar UB 'upperbound' /INF/;
scalar LB 'lowerbound' /0/;


parameter log(iter,*) 'logging info';
parameter log2(iter2,*) 'OA logging info';
parameter suc_iter(iter);
suc_iter(iter)=0;

parameter wind_integration(t,wf)
          wind_spill(t,wf)
          worst_wind_sce(t,wf)
          generation(t,i)
          power_flow(t,l)
          G_cost(t,i)
          W_cost(t,wf)
          Commitment(t,i);
wind_integration(t,wf)=0;
wind_spill(t,wf)=0;
worst_wind_sce(t,wf)=0;
generation(t,i)=Eps;
power_flow(t,l)=0;
G_cost(t,i)=0;
W_cost(t,wf)=0;
Commitment(t,i)=Eps;

scalar penalty_cost_wind /0/;
scalar penalty_cost_load /0/;
scalar penalty_cost_ramp /0/;
scalar penalty_cost_transmission /0/;
scalar operation_cost /0/;
parameter start_cost(t,i);

option optcr=0.005;
loop(iter$(not converged),

   iteration = ord(iter);
   ny(sp)=no;
   ny('sp1')=yes;

   solve master minimizing master_obj using mip;
   abort$(master.modelstat>=2 and master.modelstat<>8) "Masterproblem not solved to optimality";

   loop((t,i),
        if(x.l(t,i)>=0.5,
           x.l(t,i)=1;
         else
           x.l(t,i)=0;
         );
    );
   LB=master_obj.l;
         display LB;
   xiter(iter,t,i)=x.l(t,i);
   suc_iter(iter)=sum((t,i),suc.l(t,i));
******************************************************
   ny(sp)=no;
   predict_LB=0;

   wd.l(t,wf)=wind_robust(t,wf,'col2');

$ontext
   loop(sp$(ord(sp)<7),
       ny(sp)=yes;
       solve predict minimizing cost using LP;
       ny(sp)=no;
   );
    predict_LB=smax(sp,cost_ny.l(sp));

    display cost_ny.l,predict_LB;
    wd.l(t,wf)=smax(sp,MCS_wind(t,wf,sp)*(cost_ny.l(sp)=predict_LB));
$offtext

     converged2=0;
     iter_cut(iter2)=no;
     loop(iter2$(not converged2),

          solve subproblem_s maximizing sub_obj_s using lp;
          abort$(subproblem_s.modelstat>=2) "subproblem_s not solved to optimality";
          iter_cut(iter2)=yes;
          wind_iter(iter2,t,wf)=wd.l(t,wf);
          u11_iter(iter2,t,wf)=u11.l(t,wf);

          solve subproblem_m maximizing sub_obj_m using lp;
          abort$(subproblem_m.modelstat>=2) "subproblem_m not solved to optimality";

          converged2$( 2*((sub_obj_m.l-sub_obj_s.l)/(sub_obj_m.l+sub_obj_s.l))<1e-5) = 1;

          log2(iter2,'LB') = sub_obj_m.l;
          log2(iter2,'UB') = sub_obj_s.l;

          wind_iter(iter2,t,wf)=wd.l(t,wf);

         if(converged2 ,
            iter_cut(iter2)=no;
            UB=sub_obj_m.l;
                 display UB;
            cutcoeff3(iter,t,i) = u1.l(t,i)*g_min(i)-sum(b,u2.l(t,i,b)*g_max(i,b));

            display u1.l,u2.l,cutcoeff3;
            cutcoeff5(iter) = 1;
            cutconst2(iter)=  sub_obj_m.l;
            cutset(iter) = yes;
            log(iter,'LB') = LB;
            log(iter,'UB') = UB;
          );
     );
         cutconst1(iter)=  sum((t,s),dual6_1.m(t,s)+dual6_2.m(t,s))*Price_load;
***********************************************************************

     converged$( 2*((UB-LB)/(UB+LB))<1e-4) = 1;
     display$converged "Converged";

            display '----------------------start display: oa converged-----------------------------';
            display '---------cost master and sub----------';
            worst_wind_sce(t,wf)$(wd.l(t,wf)=wind_robust(t,wf,'col1'))=1;
            worst_wind_sce(t,wf)$(wd.l(t,wf)=wind_robust(t,wf,'col2'))=0;
            display worst_wind_sce;
            worst_wind_sce(t,wf)=wd.l(t,wf);
            wind_integration(t,wf)=dual5_1.m(t,wf);
            wind_spill(t,wf)= dual5_2.m(t,wf);
            penalty_cost_wind = sum((t,wf), wind_spill(t,wf)*Price_wind(t,wf));
            penalty_cost_load = sum((t,s),dual6_1.m(t,s)+dual6_2.m(t,s))*Price_load;
            operation_cost=UB- penalty_cost_wind-penalty_cost_load;
            display sub_obj_m.l, sub_obj_s.l,penalty_cost_wind,penalty_cost_load,operation_cost;
            display wind_robust,worst_wind_sce,wind_integration, wind_spill;

            generation(t,i)$(ord(t)<card(t))=sum(b,dual1.m(t,i,b));
            generation(t,i)$(ord(t)=card(t))=sum(b,dual2.m(t,i,b));
            Commitment(t,i)=Eps;
            Commitment(t,i)$(x.l(t,i)>=0.5)=1;
            power_flow(t,l)= dual3.m(t,l)+0.00000001;
            start_cost(t,i)=suc.l(t,i)+0.00000001;
            G_cost(t,i)$(ord(t)<card(t))=sum(b,dual1.m(t,i,b)*k(i,b))+x.l(t,i)*a(i)+0.00000001;
            G_cost(t,i)$(ord(t)=card(t))=sum(b,dual2.m(t,i,b)*k(i,b))+x.l(t,i)*a(i)+0.00000001;
            W_cost(t,wf)=Price_wind(t,wf)*wind_spill(t,wf)+0.00000001;

            display generation,power_flow;
            display '----------------------end display: oa converged-----------------------------';

     if(converged,
     display '----------------------start displapy: final results-----------------------------';

*$ontext
     execute_unload "result_case73_robust.gdx" wind_robust worst_wind_sce wind_integration wind_spill Commitment generation operation_cost start_cost,G_cost,W_cost,power_flow;
     execute 'gdxxrw.exe result_case73_robust.gdx par=wind_bound_u rng=wind_bound_u!a1:zz28000'
     execute 'gdxxrw.exe result_case73_robust.gdx par=worst_wind_sce rng=worst_wind_se!a1:zz28000'
     execute 'gdxxrw.exe result_case73_robust.gdx par=wind_integration rng=wind_integration!a1:zz28000'
     execute 'gdxxrw.exe result_case73_robust.gdx par=wind_spill rng=wind_spill!a1:zz28000'
*     execute 'gdxxrw.exe result_case73_robust.gdx par=wind_bound_l rng=wind_bound_l!a1:zz28000'
     execute 'gdxxrw.exe result_case73_robust.gdx par=Commitment rng=Commitment!a1:zz28000'
     execute 'gdxxrw.exe result_case73_robust.gdx par=generation rng=power_generation!a1:zz28000'
     execute 'gdxxrw.exe result_case73_robust.gdx par=operation_cost rng=operation!a1:zz28000'
     execute 'gdxxrw.exe result_case73_robust.gdx par=start_cost rng=start_up!a1:zz28000'
     execute 'gdxxrw.exe result_case73_robust.gdx par=G_cost rng=generation_cost_ti!a1:zz28000'
     execute 'gdxxrw.exe result_case73_robust.gdx par=W_cost rng=wind_cost_ti!a1:zz28000'
     execute 'gdxxrw.exe result_case73_robust.gdx par=power_flow rng=power_flow!a1:zz28000'
*$offtext
     display '----------------------end displapy: final results-----------------------------';
     );
     display log,log2;
     abort$( 2*((UB-LB)/(UB+LB))<1e-4) "Converged";
     x.l(t,i)= xiter(iter,t,i);
     log2(iter2,'LB') = 0;
     log2(iter2,'UB') = 0;
);

abort$(not converged) "Maximum iteration and No convergence";







