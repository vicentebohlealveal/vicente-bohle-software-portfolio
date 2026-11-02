import time
import numpy as np
import matplotlib.pyplot as plt
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds

def main():
    BoardShim.enable_dev_board_logger()
    params = BrainFlowInputParams()
    board_id = BoardIds.MUSE_S_BOARD.value 
    board = BoardShim(board_id, params)

    try:
        print("Conectando al Muse S...")
        board.prepare_session()
        board.start_stream()
        
        print("--- ¡PARPADEA FUERTE AHORA! (tienes 5 segundos) ---")
        time.sleep(5)
        
        data = board.get_board_data()
        
    finally:
        if board.is_prepared():
            board.stop_stream()
            board.release_session()
            print("Bluetooth liberado.")

    # --- SECCIÓN DE PROCESAMIENTO Y GRÁFICO ---
    # 1. Obtener qué filas corresponden a los canales EEG
    eeg_channels = BoardShim.get_eeg_channels(board_id)
    
    # 2. El canal AF7 (frontal izquierdo) suele ser el segundo en la lista de EEG del Muse
    canal_af7 = data[eeg_channels[1]] 
    
    # 3. Crear un eje de tiempo (en segundos)
    t = np.arange(len(canal_af7)) / BoardShim.get_sampling_rate(board_id)

    # 4. Graficar
    plt.figure(figsize=(10, 4))
    plt.plot(t, canal_af7, color='b')
    plt.title('Señal Cruda - Electrodo Frontal (AF7)')
    plt.xlabel('Tiempo (Segundos)')
    plt.ylabel('Amplitud (Microvoltios)')
    plt.grid(True)
    plt.show()

if __name__ == "__main__":
    main()