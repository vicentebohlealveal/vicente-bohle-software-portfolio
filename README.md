# HandTrack Pro — control de mano robótica

Dos variantes de interfaz de la misma aplicación de visión por computador: `index.html` con identidad visual USM/AC3E y `handtrack-elo-usm.html` con encabezado ELO/UTFSM. Ambas detectan puntos de la mano con MediaPipe en el navegador y transmiten cinco estados por puerto serie a 9600 baudios.

## Ejecución

- Abre el sitio por HTTPS o `localhost` en un navegador compatible con MediaPipe y Web Serial (por ejemplo, Chrome o Edge de escritorio).
- Concede el permiso de cámara y, cuando pulses iniciar, selecciona explícitamente el dispositivo serie.
- El firmware del microcontrolador debe entender una línea de cinco caracteres `0`/`1` por cada envío. Ese firmware no está incluido en este proyecto.

## Seguridad y dependencias

- No se han detectado credenciales o API keys en el código HTML incluido.
- MediaPipe y las fuentes se descargan desde CDNs; la variante AC3E también carga logotipos remotos. Por ello, el proyecto depende de terceros para esos recursos.
- La app solicita la cámara y el acceso al puerto serie solo mediante las APIs del navegador. La página transmite datos al dispositivo serie seleccionado; no incluye código explícito para subir las imágenes de la cámara a un backend.
- No se incluyen firmware, modelos de terceros ni datos privados.

La versión ELO utiliza un encabezado de texto en lugar de incrustar el enorme logo en base64 del HTML inicial, para evitar duplicar un recurso institucional dentro del código. Verifica permisos de uso de logos antes de hacer público el proyecto.
