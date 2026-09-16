import pandas as pd
import matplotlib.pyplot as plt

def simular_modulo_bess(ruta_perfil_csv, ruta_salida_csv="resultados_bess_completos.csv"):
    print(f"Cargando perfil de ensayo: {ruta_perfil_csv}...")
    df = pd.read_csv(ruta_perfil_csv) 
    
    # ==========================================
    # CONFIGURACIÓN TÉCNICA (Celda 21700)
    # ==========================================
    # Parámetros Eléctricos
    capacidad_Ah = 5.0       
    capacidad_As = capacidad_Ah * 3600  # Capacidad en Coulombs
    R_interna = 0.015        # Ohmios
    soc_inicial = 0.10       # 10%
    
    # Parámetros Térmicos
    masa_celda = 0.068       # kg
    Cp = 830                 # J/(kg*K)
    temp_inicial = 25.0      # °C
    
    # Parámetros de Refrigeración Líquida
    h = 150.0                # W/(m^2*K) - Coef. de convección
    area_contacto = 0.0015   # m^2
    temp_fluido = 20.0       # °C
    
    # ==========================================
    # INICIALIZACIÓN DE VARIABLES DE ESTADO
    # ==========================================
    temperaturas = [temp_inicial]
    soc = [soc_inicial]
    
    # Cálculo del voltaje inicial en t=0
    corriente_inicial = df['Corriente_A'].iloc[0]
    ocv_inicial = 3.0 + (1.2 * soc_inicial)
    voltaje_inicial = ocv_inicial + (corriente_inicial * R_interna)
    voltajes = [voltaje_inicial]
    
    print("Iniciando simulación transitoria...")
    
    # ==========================================
    # BUCLE ITERATIVO (TIME-STEPPING)
    # ==========================================
    for i in range(1, len(df)):
        dt = df['Tiempo_s'].iloc[i] - df['Tiempo_s'].iloc[i-1]
        I = df['Corriente_A'].iloc[i] 
        
        T_actual = temperaturas[-1]
        soc_actual = soc[-1]
        
        # --- 1. MODELO ELÉCTRICO ---
        delta_soc = (I * dt) / capacidad_As
        soc_nuevo = max(0.0, min(1.0, soc_actual + delta_soc)) # Límite de seguridad
        
        ocv = 3.0 + (1.2 * soc_nuevo)
        voltaje_terminal = ocv + (I * R_interna)
        
        # --- 2. MODELO TÉRMICO ---
        Q_gen = (I**2) * R_interna
        Q_disipado = h * area_contacto * (T_actual - temp_fluido)
        delta_T = ((Q_gen - Q_disipado) / (masa_celda * Cp)) * dt
        T_nueva = T_actual + delta_T
        
        # --- 3. GUARDAR ESTADO ---
        soc.append(soc_nuevo)
        voltajes.append(voltaje_terminal)
        temperaturas.append(T_nueva)
        
    # ==========================================
    # AÑADIR RESULTADOS AL DATAFRAME
    # ==========================================
    df['SoC'] = soc
    df['Voltaje_V'] = voltajes
    df['Temperatura_C'] = temperaturas
    
    # --- COLUMNAS TÉCNICAS ADICIONALES ---
    df['Potencia_W'] = df['Voltaje_V'] * df['Corriente_A']
    df['C_rate'] = df['Corriente_A'] / capacidad_Ah
    df['Calor_Generado_W'] = (df['Corriente_A']**2) * R_interna
    
    # Energía acumulada en Wh (integrando Potencia respecto al tiempo en segundos / 3600)
    dt_series = df['Tiempo_s'].diff().fillna(0)
    df['Energia_Wh'] = (df['Potencia_W'] * dt_series / 3600).cumsum()

    # Guardar el DataFrame completo en un nuevo archivo CSV
    df.to_csv(ruta_salida_csv, index=False)
    print(f"Resultados completos exportados exitosamente a: {ruta_salida_csv}")
    
    print(f"Simulación finalizada. Temperatura máxima alcanzada: {max(temperaturas):.2f} °C")
    return df

def graficar_dashboard(df):
    """Genera un dashboard visual estilo Test Engineering"""
    plt.style.use('bmh') # Estilo limpio y técnico para las gráficas
    fig, axs = plt.subplots(3, 1, figsize=(10, 12), sharex=True)
    
    # Gráfica 1: Perfil de Corriente (El estímulo)
    axs[0].plot(df['Tiempo_s'], df['Corriente_A'], color='orange', linewidth=2)
    axs[0].set_ylabel('Corriente (A)')
    axs[0].set_title('Perfil de Carga (Protocolo CC-CV)')
    axs[0].grid(True)
    
    # Gráfica 2: Respuesta Eléctrica (SoC y Voltaje)
    ax2 = axs[1].twinx() # Eje Y secundario
    axs[1].plot(df['Tiempo_s'], df['Voltaje_V'], color='blue', label='Voltaje (V)')
    ax2.plot(df['Tiempo_s'], df['SoC'] * 100, color='green', linestyle='--', label='SoC (%)')
    axs[1].set_ylabel('Voltaje (V)', color='blue')
    ax2.set_ylabel('SoC (%)', color='green')
    axs[1].set_title('Respuesta Eléctrica: Voltaje y Estado de Carga')
    
    # Gráfica 3: Respuesta Térmica
    axs[2].plot(df['Tiempo_s'], df['Temperatura_C'], color='red', linewidth=2)
    axs[2].axhline(y=45, color='darkred', linestyle=':', label='Límite de Seguridad (45°C)')
    axs[2].set_xlabel('Tiempo (s)')
    axs[2].set_ylabel('Temperatura (°C)')
    axs[2].set_title('Evolución Térmica con Refrigeración Líquida')
    axs[2].legend()
    axs[2].grid(True)
    
    plt.tight_layout()
    plt.savefig('dashboard_bess.png', dpi=300)
    plt.show()

if __name__ == "__main__":
    # Ejecutar simulación
    archivo_csv = "perfil_carga_rapida.csv"
    df_resultados = simular_modulo_bess(archivo_csv)
    
    # Mostrar resultados en pantalla / generar dashboard
    graficar_dashboard(df_resultados)