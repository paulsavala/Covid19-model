import numpy as np
from scipy.integrate import odeint, solve_ivp

from datetime import timedelta

from models.params import GenericParam


class SeirCovidModel:
    def __init__(self, pop_size, num_weeks, start_date=None, static_sd=True, dynamic_sd=False):
        self.pop_size = pop_size
        self.num_weeks = num_weeks
        self.start_date = start_date
        self.static_sd = static_sd
        self.dynamic_sd = dynamic_sd

        p_R_desc = 'Proportion of exposed individuals who enter the infected recovery state I_R'
        p_H_desc = 'Proportion of exposed individuals who enter the hospitalization state I_H ' \
                   '(excluding critical care)'
        p_C_desc = 'Proportion of exposed individuals who enter the critical care state I_C'
        nu_desc = 'Rate at which exposed individuals become infected'
        gamma_desc = '1/gamma is the duration in weeks a person is infected before they enter ' \
                     'hospitalization'
        delta_H_desc = '1/delta_H is the duration in weeks hospitalization cases which do not receive ' \
                       'critical care'
        delta_C_desc = '1/delta_C is the duration in weeks of hospitalization cases prior to receiving ' \
                       'critical care'
        xi_C_desc = '1/xi_C is the duration in weeks of critical care'
        max_R0_desc = 'Maximum of the basic reproduction number'
        delta_desc = 'Proportional decline in R0 in the summer'
        phi_desc = 'Phase shift of the seasonal forcing'
        start_sd_desc = 'Start of social distancing (weeks after initial case)'
        sd_duration_desc = 'Duration of social distancing (weeks)'
        sd_reduction_desc = 'Percentage to reduce weekly contact by'
        dynamic_sd_cutoff_desc = 'Number of cases per 10,000 required to trigger social distancing'

        self.p_R_param = GenericParam(name='p_R', min_value=0.956, desc=p_R_desc)
        self.p_H_param = GenericParam(name='p_H', min_value=0.0308, desc=p_H_desc)
        self.p_C_param = GenericParam(name='p_C', min_value=0.0132, desc=p_C_desc)
        self.nu_param = GenericParam(name='nu', min_value=7/4.6, desc=nu_desc)
        self.gamma_param = GenericParam(name='gamma', min_value=7/5, desc=gamma_desc)
        self.delta_H_param = GenericParam(name='delta_H', min_value=7/8, desc=delta_H_desc)
        self.delta_C_param = GenericParam(name='delta_C', min_value=7/6, desc=delta_C_desc)
        self.xi_C_param = GenericParam(name='xi_C', min_value=7/10, desc=xi_C_desc)
        self.max_R0_param = GenericParam(name='max_R0', min_value=2, max_value=2.5, desc=max_R0_desc, group='advanced',
                                         show_label=True)
        self.delta_param = GenericParam(name='delta', min_value=0, max_value=0.3, desc=delta_desc, group='advanced',
                                        show_label=True, is_pct=True)
        self.phi_param = GenericParam(name='phi', min_value=-3.8, desc=phi_desc)
        self.start_sd_param = GenericParam(name='start_sd', min_value=0, max_value=20, default_value=2,
                                           is_int=True, desc=start_sd_desc, group='static_social_distancing')
        self.sd_duration_param = GenericParam(name='sd_duration', min_value=0, max_value=40, default_value=4,
                                              is_int=True, desc=sd_duration_desc, group='static_social_distancing')
        self.sd_reduction_param = GenericParam(name='sd_reduction', min_value=0, max_value=1, default_value=0.4,
                                               desc=sd_reduction_desc, group='static_social_distancing', is_pct=True)
        self.dynamic_sd_cutoff_param = GenericParam(name='dynamic_sd_cutoff', min_value=20, max_value=100,
                                                    is_int=True, default_value=38, desc=dynamic_sd_cutoff_desc,
                                                    group='dynamic_social_distancing')

        self.params = [self.p_R_param, self.p_H_param, self.p_C_param, self.nu_param, self.gamma_param,
                       self.delta_H_param, self.delta_C_param, self.xi_C_param, self.max_R0_param,
                       self.delta_param, self.phi_param,
                       self.start_sd_param, self.sd_duration_param, self.sd_reduction_param,
                       self.dynamic_sd_cutoff_param]

        self.p_R = self.p_R_param.default_value
        self.p_H = self.p_H_param.default_value
        self.p_C = self.p_C_param.default_value
        self.nu = self.nu_param.default_value
        self.gamma = self.gamma_param.default_value
        self.delta_H = self.delta_H_param.default_value
        self.delta_C = self.delta_C_param.default_value
        self.xi_C = self.xi_C_param.default_value
        self.max_R0 = self.max_R0_param.default_value
        self.phi = self.phi_param.default_value
        self.delta = self.delta_param.default_value
        self.start_sd = int(self.start_sd_param.default_value)
        self.sd_duration = int(self.sd_duration_param.default_value)
        self.sd_reduction = self.sd_reduction_param.default_value
        self.dynamic_sd_cutoff = self.dynamic_sd_cutoff_param.default_value

        self.t = range(0, self.num_weeks + 1)
        self.t_weeks = [self.start_date + timedelta(weeks=t_i) for t_i in self.t]

    def _adjust_R0(self, R0):
        return (1 - self.sd_reduction) * R0

    def _R0(self, t):
        amp = (self.max_R0 - (1 - self.delta) * self.max_R0) / 2
        vert_shift = (self.max_R0 + (1 - self.delta) * self.max_R0) / 2
        period = 52
        R0 = amp * np.cos((2 * np.pi / period) * (t + self.phi)) + vert_shift
        return R0

    def _beta(self, t):
        return self.gamma * self._R0(t)

    def _diff_eqn(self, t, y, p_R, p_H, p_C, nu, gamma, delta_H, delta_C, xi_C):
        """
        Differential equation for the modified SEIR model
        :param y: Values of S, E, I_R, I_H, I_C, H_H, H_C, R_H, R_C. Used by scipy.integrate.odeint
        :param t: Time, also used by odeint
        :param p_R: Proportion of exposed individuals who enter the infected recovery state I_R
        :param p_H: Proportion of exposed individuals who enter the hospitalization state I_H (excluding critical care)
        :param p_C: Proportion of exposed individuals who enter the critical care state I_C
        :param nu: Rate at which exposed individuals become infected
        :param gamma: 1/gamma is the number of weeks (duration) a person is infected before they enter hospitalization
        :param delta_H: 1/delta_H is the duration in weeks of hospitalization cases which do not receive critical care
        :param delta_C: 1/delta_C is the duration in weeks of hospitalization cases prior to receiving critical care
        :param xi_C: 1/xi_C is the duration in weeks of critical care
        :return: derivatives of S, E, I_R, I_H, I_C, H_H, H_C, R_H, R_C with respect to t
        """
        S, E, I_R, I_H, I_C, R_R, H_H, H_C, R_H, C_C, R_C = y
        infected = I_R + I_H + I_C

        beta_t = self._beta(t)

        if self.static_sd and self.start_sd < t < self.start_sd + self.sd_duration:
            beta_t = self._adjust_R0(beta_t)
        if self.dynamic_sd and infected:
            # If social distancing should be triggered...
            if infected > self.dynamic_sd_cutoff and (t < self.start_sd or t > self.start_sd + self.sd_duration):
                # Update R0
                beta_t = self._adjust_R0(beta_t)

        dSdt = -beta_t * (I_R + I_H + I_C) * S / self.pop_size
        dEdt = -dSdt - nu*E
        dI_Rdt = nu*p_R*E - gamma*I_R
        dI_Hdt = nu*p_H*E - gamma*I_H
        dI_Cdt = nu*p_C*E - gamma*I_C
        dR_Rdt = gamma*I_R
        dH_Hdt = gamma*I_H - delta_H*H_H
        dH_Cdt = gamma*I_C - delta_C*H_C
        dR_Hdt = delta_H*H_H
        dC_Cdt = delta_C*H_C - xi_C*C_C
        dR_Cdt = xi_C*C_C
        return dSdt, dEdt, dI_Rdt, dI_Hdt, dI_Cdt, dR_Rdt, dH_Hdt, dH_Cdt, dR_Hdt, dC_Cdt, dR_Cdt

    def solve(self):
        E0 = 1
        I_R0 = 0
        I_H0 = 0
        I_C0 = 0
        R_R0 = 0
        H_H0 = 0
        H_C0 = 0
        R_H0 = 0
        C_C0 = 0
        R_C0 = 0
        S0 = self.pop_size - (E0 + I_R0 + I_H0 + I_C0 + R_R0 + H_H0 + H_C0 + R_H0 + C_C0 + R_C0)
        y0 = (S0, E0, I_R0, I_H0, I_C0, R_R0, H_H0, H_C0, R_H0, C_C0, R_C0)

        sol = solve_ivp(self._diff_eqn, (self.t[0], self.t[-1]), y0,
                        args=(self.p_R, self.p_H, self.p_C, self.nu, self.gamma, self.delta_H, self.delta_C, self.xi_C))

        S, E, I_R, I_H, I_C, R_R, H_H, H_C, R_H, C_C, R_C = sol.y

        return S, E, I_R, I_H, I_C, R_R, H_H, H_C, R_H, C_C, R_C
