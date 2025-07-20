# Aram Mikaelyan, NCSU | Streamlit App: Methane Oxidation with Gas Exchange
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint
import math
import plotly.graph_objects as go

# Constants
E_a = 50e3  # Activation energy in J/mol
R = 8.314   # Gas constant
T_ref = 298.15  # Reference temp in K

# --- ODE System ---
def methane_oxidation(C, t, C_atm, O2_atm, g_s, Vmax_ref, Km_ref, Pi, T,
                      k_L_CH4, k_L_O2, V_cell, scaling_factor):
    C_cyt, CH3OH, O2_cyt = C
    T_K = T + 273.15

    Vmax_T = Vmax_ref * scaling_factor * np.exp(-E_a / R * (1/T_K - 1/T_ref))
    Km_T = Km_ref * (1 + 0.02 * (T - 25))
    Vmax = Vmax_T * np.exp(-0.02 * (Pi / 100))_
