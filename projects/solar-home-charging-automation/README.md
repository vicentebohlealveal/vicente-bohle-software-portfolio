# Estación de carga solar — Kong Charger (MVP)

Prototipo con **ESP32** para programar la carga de baterías externas (power banks) desde un sistema solar mediante un relé. El usuario ajusta las horas de carga con un encoder rotatorio y ve el estado en una pantalla OLED.

## Hardware

| Componente | Conexión ESP32 |
|-|-|
| Pantalla OLED SSD1306 128×64 (I2C, 0x3C) | SDA = GPIO 21, SCL = GPIO 22 |
| Encoder rotatorio (CLK / DT / botón) | GPIO 18 / 19 / 5 |
| Módulo relé (lógica inversa: `LOW` = encendido) | GPIO 25 (IN1) |

## Funcionamiento

Máquina de estados de tres modos; el botón del encoder pasa de uno a otro:

1. **AUTO PB1**: carga durante las horas configuradas (1–24) y descansa hasta completar un ciclo de 48 h; luego repite.
2. **FORZAR PB1**: carga una vez durante las horas configuradas y pasa a espera.
3. **EN ESPERA**: relé apagado.

El encoder se lee por interrupciones y el botón tiene antirrebote. Cada vez que cambia el modo, el relé se apaga por seguridad.

## Compilar

Arduino IDE con el core ESP32 y las librerías **Adafruit SSD1306** y **Adafruit GFX**. Abrir `firmware/kong_charger_mvp/kong_charger_mvp.ino`.

> `MODO_PRUEBA = true` hace que 1 hora equivalga a 1 segundo para validar el ciclo en el banco. Para usar el equipo de verdad, cambiarlo a `false`.

## Estado

MVP con un solo relé (PB1). Pendiente: más canales, medición de tensión y corriente del panel y la batería, y fotos o diagrama del montaje.
