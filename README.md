# Tablero de Gestión IT · OCA

Indicadores del Comité IT calculados con los datos de GLPI, publicados con GitHub Pages.
Los datos se publican **cifrados** (`data.enc`, AES-256-GCM): la página pide una contraseña
y los descifra en el navegador. Sin la contraseña el archivo no se puede leer.

## Cómo se actualiza

GLPI no es accesible desde internet, así que la actualización corre en una PC o servidor
**dentro de la red de OCA**:

```
PC interna (cada 30 min) ── API GLPI ──► publicar.py ── cifra ──► data.enc en GitHub ──► GitHub Pages
```

## Puesta en marcha (una sola vez)

1. **Python 3.10+** en la PC interna y las librerías: `pip install requests cryptography`
2. Copiar `publicar.py`, `collector.py`, `publicar.bat` y `publicar.env.ejemplo` a una carpeta, por ejemplo `C:\TableroIT`.
3. **Token de GitHub**: GitHub → Settings → Developer settings → Personal access tokens →
   *Fine-grained tokens* → Generate new token.
   - Repository access: *Only select repositories* → este repositorio.
   - Permissions → Repository permissions → **Contents: Read and write**.
   - Vencimiento: el máximo que permita tu política (renovarlo cuando venza).
4. Renombrar `publicar.env.ejemplo` a `publicar.env` y completar:
   - `GLPI_APP_TOKEN` y `GLPI_USER_TOKEN` (cliente API y usuario `tablero.it`).
   - `TABLERO_PASSWORD`: la contraseña que vas a compartir (12 caracteres o más).
   - `GITHUB_TOKEN` y `GITHUB_REPO` (`usuario/tablero-it-oca`).
5. Probar a mano: `python publicar.py` → debe decir `Publicado: N tickets…`.
6. **Programador de tareas de Windows** → Crear tarea:
   - Desencadenador: diariamente, repetir cada 30 minutos durante 1 día.
   - Acción: iniciar `C:\TableroIT\publicar.bat`.
   - Marcar *Ejecutar tanto si el usuario inició sesión como si no*.

`publicar.env` tiene los tokens: no se sube nunca a GitHub (está en `.gitignore`).

## Cambiar la contraseña

Cambiar `TABLERO_PASSWORD` en `publicar.env` y correr `publicar.py`. Desde ese momento la
contraseña anterior deja de servir; quien la tenía recordada en el navegador la vuelve a pedir.
