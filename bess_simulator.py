import pandas as pd
import matplotlib.pyplot as plt

def simulate_bess_module(profile_csv_path, output_csv_path="bess_complete_results.csv"):
    print(f"Loading test profile: {profile_csv_path}...")
    df = pd.read_csv(profile_csv_path) 
    
    # ==========================================
    # TECHNICAL CONFIGURATION (21700 Cell)
    # ==========================================
    # Electrical Parameters
    capacity_Ah = 5.0       
    capacity_As = capacity_Ah * 3600  # Capacity in Coulombs
    internal_resistance = 0.015       # Ohms
    initial_soc = 0.10                # 10%
    
    # Thermal Parameters
    cell_mass = 0.068                 # kg
    Cp = 830                          # J/(kg*K)
    initial_temp = 25.0               # °C
    
    # Liquid Cooling Parameters
    h = 150.0                         # W/(m^2*K) - Convection coefficient
    contact_area = 0.0015             # m^2
    fluid_temp = 20.0                 # °C
    
    # ==========================================
    # STATE VARIABLES INITIALIZATION
    # ==========================================
    temperatures = [initial_temp]
    soc = [initial_soc]
    
    # Calculate initial voltage at t=0
    initial_current = df['Current_A'].iloc[0]
    initial_ocv = 3.0 + (1.2 * initial_soc)
    initial_voltage = initial_ocv + (initial_current * internal_resistance)
    voltages = [initial_voltage]
    
    print("Starting transient simulation...")
    
    # ==========================================
    # ITERATIVE LOOP (TIME-STEPPING)
    # ==========================================
    for i in range(1, len(df)):
        dt = df['Time_s'].iloc[i] - df['Time_s'].iloc[i-1]
        I = df['Current_A'].iloc[i] 
        
        current_temp = temperatures[-1]
        current_soc = soc[-1]
        
        # --- 1. ELECTRICAL MODEL ---
        delta_soc = (I * dt) / capacity_As
        new_soc = max(0.0, min(1.0, current_soc + delta_soc)) # Safety limit
        
        ocv = 3.0 + (1.2 * new_soc)
        terminal_voltage = ocv + (I * internal_resistance)
        
        # --- 2. THERMAL MODEL ---
        heat_gen = (I**2) * internal_resistance
        heat_dissipated = h * contact_area * (current_temp - fluid_temp)
        delta_temp = ((heat_gen - heat_dissipated) / (cell_mass * Cp)) * dt
        new_temp = current_temp + delta_temp
        
        # --- 3. SAVE STATE ---
        soc.append(new_soc)
        voltages.append(terminal_voltage)
        temperatures.append(new_temp)
        
    # ==========================================
    # ADD RESULTS TO DATAFRAME
    # ==========================================
    df['SoC'] = soc
    df['Voltage_V'] = voltages
    df['Temperature_C'] = temperatures
    
    # --- ADDITIONAL TECHNICAL COLUMNS ---
    df['Power_W'] = df['Voltage_V'] * df['Current_A']
    df['C_rate'] = df['Current_A'] / capacity_Ah
    df['Heat_Generated_W'] = (df['Current_A']**2) * internal_resistance
    
    # Accumulated energy in Wh (integrating Power with respect to time in seconds / 3600)
    dt_series = df['Time_s'].diff().fillna(0)
    df['Energy_Wh'] = (df['Power_W'] * dt_series / 3600).cumsum()

    # Save the complete DataFrame to a new CSV file
    df.to_csv(output_csv_path, index=False)
    print(f"Complete results successfully exported to: {output_csv_path}")
    
    print(f"Simulation finished. Maximum temperature reached: {max(temperatures):.2f} °C")
    return df

def plot_dashboard(df):
    """Generates a Test Engineering style visual dashboard"""
    plt.style.use('bmh') # Clean, technical style for plots
    fig, axs = plt.subplots(3, 1, figsize=(10, 12), sharex=True)
    
    # Plot 1: Current Profile (The stimulus)
    axs[0].plot(df['Time_s'], df['Current_A'], color='orange', linewidth=2)
    axs[0].set_ylabel('Current (A)')
    axs[0].set_title('Charging Profile (CC-CV Protocol)')
    axs[0].grid(True)
    
    # Plot 2: Electrical Response (SoC and Voltage)
    ax2 = axs[1].twinx() # Secondary Y-axis
    axs[1].plot(df['Time_s'], df['Voltage_V'], color='blue', label='Voltage (V)')
    ax2.plot(df['Time_s'], df['SoC'] * 100, color='green', linestyle='--', label='SoC (%)')
    axs[1].set_ylabel('Voltage (V)', color='blue')
    ax2.set_ylabel('SoC (%)', color='green')
    axs[1].set_title('Electrical Response: Voltage and State of Charge')
    
    # Plot 3: Thermal Response
    axs[2].plot(df['Time_s'], df['Temperature_C'], color='red', linewidth=2)
    axs[2].axhline(y=45, color='darkred', linestyle=':', label='Safety Limit (45°C)')
    axs[2].set_xlabel('Time (s)')
    axs[2].set_ylabel('Temperature (°C)')
    axs[2].set_title('Thermal Evolution with Liquid Cooling')
    axs[2].legend()
    axs[2].grid(True)
    
    plt.tight_layout()
    plt.savefig('dashboard_bess.png', dpi=300)
    plt.show()

if __name__ == "__main__":
    # Run simulation
    input_csv = "fast_charging_profile.csv"
    df_results = simulate_bess_module(input_csv)
    
    # Show results / generate dashboard
    plot_dashboard(df_results)