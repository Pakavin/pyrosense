import numpy as np
import matplotlib.pyplot as plt
from pgmpy.models import BayesianNetwork
from pgmpy.factors.discrete import TabularCPD
from pgmpy.inference import VariableElimination

class FireModel:
    def __init__(self, A_o, H_o, C, rho, Cp, T_ambient, fire_load_density, compartment_area, compartment_height):
        # Initialize parameters
        self.A_o = A_o
        self.H_o = H_o
        self.C = C
        self.rho = rho
        self.Cp = Cp
        self.T_ambient = T_ambient
        self.fire_load_density = fire_load_density
        self.compartment_area = compartment_area
        self.compartment_height = compartment_height
        self.ventilation_factor = A_o * np.sqrt(H_o)
        self.fire_load = fire_load_density * compartment_area * 1e6  # convert to J
        self.dt = 1  # time step (s)
        self.T_total = 3600  # total simulation time (s)
        self.time_steps = int(self.T_total / self.dt)

        # Initialize arrays to store results
        self.time = np.linspace(0, self.T_total, self.time_steps)
        self.heat_release_rate = np.zeros(self.time_steps)
        self.compartment_temp = np.zeros(self.time_steps)
        self.oxygen_concentration = np.full(self.time_steps, 0.21)  # initial O2 concentration (21%)

        # Define the initial conditions
        self.compartment_temp[0] = T_ambient

        # Bayesian Network setup
        self.setup_bayesian_network()

    def setup_bayesian_network(self):
        # Define the structure of the Bayesian Network
        self.model = BayesianNetwork([
            ('Ventilation', 'HeatReleaseRate'),
            ('FireLoad', 'HeatReleaseRate'),
            ('HeatReleaseRate', 'CompartmentTemperature'),
            ('HeatReleaseRate', 'OxygenConcentration')
        ])

        # Define CPDs (for simplicity, using hypothetical distributions)
        cpd_ventilation = TabularCPD(variable='Ventilation', variable_card=2, values=[[0.5], [0.5]])
        cpd_fireload = TabularCPD(variable='FireLoad', variable_card=2, values=[[0.5], [0.5]])
        cpd_hrr = TabularCPD(variable='HeatReleaseRate', variable_card=2,
                             values=[[0.8, 0.4, 0.6, 0.1],
                                     [0.2, 0.6, 0.4, 0.9]],
                             evidence=['Ventilation', 'FireLoad'],
                             evidence_card=[2, 2])
        cpd_temp = TabularCPD(variable='CompartmentTemperature', variable_card=2,
                              values=[[0.7, 0.2],
                                      [0.3, 0.8]],
                              evidence=['HeatReleaseRate'],
                              evidence_card=[2])
        cpd_oxygen = TabularCPD(variable='OxygenConcentration', variable_card=2,
                                values=[[0.9, 0.3],
                                        [0.1, 0.7]],
                                evidence=['HeatReleaseRate'],
                                evidence_card=[2])

        self.model.add_cpds(cpd_ventilation, cpd_fireload, cpd_hrr, cpd_temp, cpd_oxygen)
        self.infer = VariableElimination(self.model)

    def run_simulation(self):
        for t in range(1, self.time_steps):
            # Step 1: Bayesian Network inference
            query = self.infer.map_query(variables=['HeatReleaseRate', 'CompartmentTemperature', 'OxygenConcentration'],
                                         evidence={'Ventilation': 1, 'FireLoad': 1})
            heat_release_rate_state = query['HeatReleaseRate']
            compartment_temp_state = query['CompartmentTemperature']
            oxygen_concentration_state = query['OxygenConcentration']

            # Convert states to values for plotting
            self.heat_release_rate[t] = 1e6 if heat_release_rate_state == 1 else 5e5
            self.compartment_temp[t] = 350 if compartment_temp_state == 1 else 300
            self.oxygen_concentration[t] = 0.15 if oxygen_concentration_state == 1 else 0.21

    def plot_results(self):
        # Plot Heat Release Rate (HRR)
        plt.figure(figsize=(12, 6))

        plt.subplot(3, 1, 1)
        plt.plot(self.time, self.heat_release_rate / 1e6, color='r')  # Convert HRR to MW for better visualization
        plt.title('Heat Release Rate (HRR) Over Time')
        plt.xlabel('Time (s)')
        plt.ylabel('HRR (MW)')
        plt.grid(True)

        # Plot Compartment Temperature
        plt.subplot(3, 1, 2)
        plt.plot(self.time, self.compartment_temp - 273.15, color='b')  # Convert temperature to Celsius
        plt.title('Compartment Temperature Over Time')
        plt.xlabel('Time (s)')
        plt.ylabel('Temperature (°C)')
        plt.grid(True)

        # Plot Oxygen Concentration
        plt.subplot(3, 1, 3)
        plt.plot(self.time, self.oxygen_concentration * 100, color='g')  # Convert concentration to percentage
        plt.title('Oxygen Concentration Over Time')
        plt.xlabel('Time (s)')
        plt.ylabel('Oxygen Concentration (%)')
        plt.grid(True)

        # Adjust layout to prevent overlap
        plt.tight_layout()

        # Show the plots
        plt.show()

# Instantiate and run the fire model
fire_model = FireModel(
    A_o=1.0,
    H_o=2.0,
    C=0.001,
    rho=1.2,
    Cp=1005,
    T_ambient=293,
    fire_load_density=800,
    compartment_area=50,
    compartment_height=3
)

fire_model.run_simulation()
fire_model.plot_results()
