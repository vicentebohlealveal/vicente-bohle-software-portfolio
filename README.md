# Vicente Bohle Alveal — Portafolio de software e integración electrónica

Portafolio de proyectos de software, prototipado e integración de sistemas electrónicos. El objetivo es mostrar muestras de código seleccionadas y documentar con honestidad los proyectos cuyo código original todavía no está incorporado.

**GitHub:** https://github.com/vicentebohlealveal  
**LinkedIn:** https://www.linkedin.com/in/vicente-bohle-alveal-b38317203/

## Proyectos con código incluido

|Proyecto|Qué muestra|Cómo revisarlo|
|-|-|-|
|[Arcade de Menciones](projects/arcade-menciones/)|Juego educativo web con cuatro minijuegos y entradas físicas Makey Makey|Abrir `index.html`; leer el manual del operador|
|[Inventario Kong.3d](projects/kong3d-inventario/)|Aplicación web para organizar componentes y gaveteros; sincronización opcional configurable|Abrir `index.html`; configurar Supabase solo si se desea probar sincronización|
|[Portal de admisión USM](projects/portal-admision-electronica-usm/)|Landing page responsive para acceso mediante QR|Abrir `index.html`|
|[Medidor de grosor de cabello](projects/medidor-grosor-cabello/)|Herramienta web de medición, calibración y análisis experimental|Abrir `index.html`|
|[HandTrack Pro](projects/robotic-hand-control-ml/)|Seguimiento de mano con MediaPipe y envío de estados por puerto serie; incluye dos variantes visuales|Abrir `index.html` o `handtrack-elo-usm.html`|
|[Contador Agrícola PRO — limones](projects/lemon-fruit-detection/)|Conteo de **frutos** con cámara y modelo YOLO ONNX en navegador|Abrir `index.html`; requiere añadir el archivo real `best.onnx`|
|[Calculadora Kong.3D Pro](projects/3d-print-cost-calculator/)|Cotizador web para impresión 3D, extras, historial y exportaciones|Abrir `index.html`|

## Proyectos del **currículum** documentados

Estas carpetas son fichas descriptivas; no contienen todavía todo el código o los archivos de implementación originales. No deben interpretarse como repositorios ejecutables hasta incorporar y revisar esos archivos:

* [BCI para brazo robótico asistivo](projects/bci-brain-computer-interface-arm/)
* [Automatización de carga solar doméstica](projects/solar-home-charging-automation/)
* [Plataforma robótica e IoT](projects/large-scale-robotic-platform-iot/)
* [Cargador de vehículos eléctricos y UPS](projects/ev-charger-and-ups/)

## Qué subir a GitHub después

Priorizar el código propio y compartible de los proyectos que ya incluyen código. Luego, recuperar los archivos reales de BCI y automatización solar. El detector de frutos incorporado en este paquete está configurado como contador agrícola de limones y necesita el archivo `best.onnx` real para funcionar. Para proyectos colaborativos, publicar solo las partes propias y con permiso de los colaboradores. En proyectos de electrónica de potencia, subir simulaciones o herramientas de software únicamente si existen y se pueden compartir.

## Créditos y permisos

El manual del operador del Arcade de Menciones fue desarrollado por Vicente Bohle Alveal y vendido a la Universidad Técnica Federico Santa María para uso institucional. Se incluye como muestra de portafolio con autorización de publicación y debe conservar su atribución. Su presencia aquí no concede automáticamente derechos de reutilización o redistribución; para ello deben respetarse los términos acordados con la Universidad y el autor.

El portal de admisión usa identidad gráfica institucional y enlaces públicos de la UTFSM; se conserva únicamente como muestra de trabajo en el contexto autorizado.

## Revisión antes de hacer público

* Comprobar permisos para publicar cada proyecto y recursos institucionales/de terceros.
* No incluir `.env`, contraseñas, tokens, claves privadas ni exportaciones del inventario real.
* La copia del inventario usa marcadores en lugar de las credenciales/URL de Supabase.
* Mantener explícito qué carpetas son documentación y cuáles contienen código.
* Elegir una licencia solo cuando se hayan revisado las colaboraciones y los recursos incluidos.

## English summary

A selected portfolio of web software and engineering projects by Vicente Bohle Alveal. Several projects include runnable source code; other folders remain documentation-only until their original implementation files are added and reviewed. Review permissions, dependencies and secrets before making the repository public.

