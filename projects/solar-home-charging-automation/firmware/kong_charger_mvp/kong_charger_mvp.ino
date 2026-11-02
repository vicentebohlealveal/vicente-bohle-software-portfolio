#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#include <Fonts/FreeSansBold9pt7b.h>
#include <Fonts/FreeSans9pt7b.h> 

#define ANCHO_PANTALLA 128
#define ALTO_PANTALLA 64
// La pantalla usa los pines I2C por defecto del ESP32: SDA = 21, SCL = 22
Adafruit_SSD1306 display(ANCHO_PANTALLA, ALTO_PANTALLA, &Wire, -1);

// --- PINES (Solo para el MVP con 1 Relé) ---
#define PIN_CLK 18
#define PIN_DT 19
#define PIN_SW 5
const int pinesRele[1] = {25}; // Usamos solo el pin 25 para IN1

// --- CONFIGURACIÓN DE TIEMPO ---
// ¡MODO PRUEBA ACTIVADO! (1 hora = 1 segundo real)
const bool MODO_PRUEBA = true; 
const unsigned long MULTIPLICADOR_MS = MODO_PRUEBA ? 1000UL : 3600000UL; 

// --- VARIABLES DEL SISTEMA ---
int estadoSistema = 0;       // 0=AUTO PB1, 1=FORZAR PB1, 2=ESPERA
volatile int horasDeCarga = 8; 
volatile bool actualizarPantalla = true; 

unsigned long tiempoInicioEstado = 0;

int ultimoEstadoCLK;
unsigned long ultimoDebounceBoton = 0;
const int tiempoDebounce = 300; 

// --- INTERRUPCIÓN DEL ENCODER ---
void IRAM_ATTR ISR_leerEncoder() {
  int estadoCLK = digitalRead(PIN_CLK);
  if (estadoCLK != ultimoEstadoCLK) {
    if (digitalRead(PIN_DT) != estadoCLK) {
      horasDeCarga++; 
      if (horasDeCarga > 24) horasDeCarga = 24; 
    } else {
      horasDeCarga--; 
      if (horasDeCarga < 1) horasDeCarga = 1;   
    }
    actualizarPantalla = true;
  }
  ultimoEstadoCLK = estadoCLK;
}

// Función auxiliar para centrar texto en la pantalla OLED
void escribirCentrado(const char* texto, int y, const GFXfont* fuente, int tamano = 1) {
  display.setFont(fuente); 
  display.setTextSize(tamano); 
  int16_t x1, y1;
  uint16_t anchoText, altoText;
  display.getTextBounds(texto, 0, 0, &x1, &y1, &anchoText, &altoText);
  display.setCursor((ANCHO_PANTALLA - anchoText) / 2, y);
  display.print(texto);
}

// Apaga el relé por seguridad (Lógica Inversa: HIGH es apagado)
void apagarTodosLosReles() {
  digitalWrite(pinesRele[0], HIGH);
}

// --- INTERFAZ GRÁFICA ---
void dibujarInterfaz(int estado, int horas, bool enReposo) {
  display.clearDisplay(); 
  display.setTextColor(SSD1306_WHITE); 
  
  display.setFont(NULL); 
  display.setTextSize(1);
  const char* titulo = "SISTEMA SOLAR PB";
  int16_t x1, y1; uint16_t w, h;
  display.getTextBounds(titulo, 0, 0, &x1, &y1, &w, &h);
  display.setCursor((ANCHO_PANTALLA - w) / 2, 2);
  display.print(titulo);
  display.drawFastHLine(0, 13, ANCHO_PANTALLA, SSD1306_WHITE);
  
  char bufferEstado[20];
  
  if (estado == 0) { // MODO AUTO
    if (enReposo) {
      snprintf(bufferEstado, sizeof(bufferEstado), "PAUSA AUTO");
    } else {
      snprintf(bufferEstado, sizeof(bufferEstado), "AUTO PB1"); 
    }
  } else if (estado == 1) {
    snprintf(bufferEstado, sizeof(bufferEstado), "FORZAR PB1"); 
  } else {
    snprintf(bufferEstado, sizeof(bufferEstado), "EN ESPERA"); 
  }
  
  escribirCentrado(bufferEstado, 37, &FreeSansBold9pt7b);
  
  display.drawFastHLine(0, 47, ANCHO_PANTALLA, SSD1306_WHITE);
  char bufferTiempo[20];
  snprintf(bufferTiempo, sizeof(bufferTiempo), "Ajuste: %d Hrs", horas);
  escribirCentrado(bufferTiempo, 61, &FreeSans9pt7b);
  
  display.display(); 
}

void setup() {
  Serial.begin(115200);

  // Configuración de pines
  pinMode(PIN_CLK, INPUT_PULLUP);
  pinMode(PIN_DT, INPUT_PULLUP);
  pinMode(PIN_SW, INPUT_PULLUP); 

  pinMode(pinesRele[0], OUTPUT);
  digitalWrite(pinesRele[0], HIGH); // Iniciar apagado (relé desactivado)

  // Configuración de interrupciones para el Encoder
  ultimoEstadoCLK = digitalRead(PIN_CLK);
  attachInterrupt(digitalPinToInterrupt(PIN_CLK), ISR_leerEncoder, CHANGE);
  attachInterrupt(digitalPinToInterrupt(PIN_DT), ISR_leerEncoder, CHANGE);

  // Iniciar la pantalla OLED
  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("Fallo OLED. Revisa los cables SDA(21) y SCL(22)."));
    for(;;); 
  }

  // Pantalla de inicio
  display.clearDisplay();
  escribirCentrado("KONG CHARGER", 25, &FreeSansBold9pt7b);
  escribirCentrado("Prueba MVP...", 50, &FreeSans9pt7b);
  display.display();
  delay(2000);
  
  tiempoInicioEstado = millis();
}

void loop() {
  unsigned long tiempoActual = millis();
  unsigned long tiempoTranscurrido = tiempoActual - tiempoInicioEstado;
  
  unsigned long duracionCargaMs = horasDeCarga * MULTIPLICADOR_MS;
  unsigned long cicloTotalMs = 48UL * MULTIPLICADOR_MS; // El ciclo total del sistema
  
  bool enReposo = false;

  // 1. LÓGICA DEL RELÉ SEGÚN EL ESTADO
  switch(estadoSistema) {
    case 0: // MODO AUTOMÁTICO PB1
      if (tiempoTranscurrido < duracionCargaMs) {
        // Fase de carga: Enciende el relé (LOW)
        digitalWrite(pinesRele[0], LOW); 
        enReposo = false;
      } else if (tiempoTranscurrido >= duracionCargaMs && tiempoTranscurrido < cicloTotalMs) {
        // Fase de reposo: Apaga el relé (HIGH)
        apagarTodosLosReles();
        enReposo = true;
      } else if (tiempoTranscurrido >= cicloTotalMs) {
        // Pasaron las 48 "horas". Reinicia el ciclo para PB1.
        tiempoInicioEstado = tiempoActual; 
        actualizarPantalla = true;
      }
      break;

    case 1: // FORZAR PB1
      if (tiempoTranscurrido < duracionCargaMs) {
        digitalWrite(pinesRele[0], LOW); 
      } else {
        // Terminó el tiempo forzado, vuelve a ESPERA
        estadoSistema = 2;
        tiempoInicioEstado = tiempoActual;
        actualizarPantalla = true;
      }
      break;

    case 2: // EN ESPERA ABSOLUTA
      apagarTodosLosReles();
      break;
  }

  // 2. LEER EL BOTÓN PARA CAMBIAR DE MODO
  if (digitalRead(PIN_SW) == LOW && (tiempoActual - ultimoDebounceBoton > tiempoDebounce)) {
    ultimoDebounceBoton = tiempoActual;
    
    estadoSistema++; 
    if (estadoSistema > 2) estadoSistema = 0; 
    
    apagarTodosLosReles();
    tiempoInicioEstado = tiempoActual; 
    actualizarPantalla = true;
  }

  // 3. ACTUALIZAR PANTALLA
  static bool estadoReposoAnterior = false;
  if (estadoSistema == 0 && enReposo != estadoReposoAnterior) {
    estadoReposoAnterior = enReposo;
    actualizarPantalla = true;
  }

  if (actualizarPantalla) {
    dibujarInterfaz(estadoSistema, horasDeCarga, enReposo);
    actualizarPantalla = false;
  }
}
