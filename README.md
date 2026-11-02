# Vicente Bohle Alveal — Portafolio de software e integración electrónica

Portafolio de proyectos de software, prototipado e integración de sistemas electrónicos. El objetivo es mostrar muestras de código seleccionadas y documentar con honestidad los proyectos cuyo código original todavía no está incorporado.

**GitHub:** https://github.com/vicentebohlealveal  
**LinkedIn:** https://www.linkedin.com/in/vicente-bohle-alveal-b38317203/

## Proyectos con código incluido

|Proyecto|Qué muestra|Cómo revisarlo|
|-|-|-|
|[BCI para brazo robótico asistivo](projects/bci-brain-computer-interface-arm/)|EEG con Muse S en Python: parpadeo como embrague, índice beta/alfa como acelerador, lógica de seguridad y gemelo digital; comandos UDP a un ESP32|`pixi install`; ejecutar `main_bci.py --dry-run` o `bci_gui.py`|
|[Estación de carga solar](projects/solar-home-charging-automation/)|Firmware ESP32 con máquina de estados, encoder por interrupciones, OLED y relé|Abrir el `.ino` en Arduino IDE|
|[Arcade de Menciones](projects/arcade-menciones/)|Juego educativo web con cuatro minijuegos y entradas físicas Makey Makey|Abrir `index.html`; leer el manual del operador|
|[Inventario Kong.3d](projects/kong3d-inventario/)|Aplicación web para organizar componentes y gaveteros; sincronización opcional configurable|Abrir `index.html`; configurar Supabase solo si se desea probar sincronización|
|[Portal de admisión USM](projects/portal-admision-electronica-usm/)|Landing page responsive para acceso mediante QR|Abrir `index.html`|
|[Medidor de grosor de cabello](projects/medidor-grosor-cabello/)|Herramienta web de medición, calibración y análisis experimental|Abrir `index.html`|
|[HandTrack Pro](projects/robotic-hand-control-ml/)|Seguimiento de mano con MediaPipe y envío de estados por puerto serie; incluye dos variantes visuales|Abrir `index.html` o `handtrack-elo-usm.html`|
|[Contador Agrícola PRO — limones](projects/lemon-fruit-detection/)|Conteo de **frutos** con cámara y modelo YOLO ONNX en navegador|Abrir `index.html`; requiere añadir el archivo real `best.onnx`|
|[Calculadora Kong.3D Pro](projects/3d-print-cost-calculator/)|Cotizador web para impresión 3D, extras, historial y exportaciones|Abrir `index.html`|

## Proyectos del currículum documentados

Estas carpetas son fichas descriptivas y todavía no contienen el código ni los archivos de implementación originales:

* [Plataforma robótica e IoT](projects/large-scale-robotic-platform-iot/)
* [Cargador de vehículos eléctricos y UPS](projects/ev-charger-and-ups/)

## Créditos y permisos

El manual del operador del Arcade de Menciones fue desarrollado por Vicente Bohle Alveal y vendido a la Universidad Técnica Federico Santa María para uso institucional. Se incluye como muestra de portafolio con autorización de publicación y debe conservar su atribución. Su presencia aquí no concede automáticamente derechos de reutilización o redistribución; para ello deben respetarse los términos acordados con la Universidad y el autor.

El portal de admisión usa identidad gráfica institucional y enlaces públicos de la UTFSM; se conserva únicamente como muestra de trabajo en el contexto autorizado.

## English summary

A selected portfolio of software and engineering projects by Vicente Bohle Alveal, including an EEG-based brain–computer interface (Python) that controls a robotic arm, ESP32 firmware for a solar charging station, and several browser-based tools (an educational arcade, workshop inventory, computer-vision fruit counter, hand tracking, and lab instruments). Two folders are documentation-only until their original implementation files are added.
