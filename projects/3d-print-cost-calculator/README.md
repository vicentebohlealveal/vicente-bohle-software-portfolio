# Kong.3D Pro — calculadora de costos de impresión 3D

Versión web basada en el HTML compartido por el autor. Calcula precio al contado y con recargo de pago, opción prioritaria, lote de piezas, material y purga, tiempo de máquina, mano de obra, diseño, post-proceso, pintura, hardware, envío e IVA. También incluye configuración local, historial, exportación CSV, copia de texto y generación de PDF.

## Seguridad y privacidad

- No utiliza claves de API ni contraseñas en el código proporcionado.
- La configuración y las cotizaciones se almacenan en `localStorage` del navegador; no se envían automáticamente a un servidor. No uses este navegador compartido para guardar información comercial sensible.
- El nombre de cotización se escapa al representar el historial y al generar el PDF. Los valores de texto se protegen frente a fórmulas en la exportación CSV.
- Carga `html2pdf.js` y fuentes externas mediante CDN. Para su uso se necesita conexión a internet y confiar en esos proveedores.
- Los valores por defecto y el apartado de mercado son referencias proporcionadas por el autor, no precios actuales verificados. Actualízalos antes de tomar decisiones comerciales.

## Ejecución

Abre `index.html` o sírvelo desde un host estático. Para portafolio se sustituyó el gran logo en base64 por texto, reduciendo tamaño y evitando duplicar recursos incrustados.
