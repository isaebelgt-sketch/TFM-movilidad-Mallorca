# Sesión 1 - Preparar el entorno en Windows

## Lo que ya está hecho

- Repositorio Git creado.
- Carpetas de datos y código creadas.
- Pregunta de investigación, alcance y fuentes iniciales documentados.

## Lo que debes instalar tú ahora

No hay un gestor de paquetes disponible en este ordenador, por lo que estas dos instalaciones requieren hacerlo desde sus instaladores oficiales.

### 1. Anaconda Distribution y Jupyter Notebook

1. Abre [la descarga oficial de Anaconda](https://www.anaconda.com/download).
2. Regístrate con tu correo académico si te lo solicita; el uso educativo del TFM está cubierto por su programa académico gratuito.
3. Descarga el instalador de **Windows 64-bit** y acepta los valores recomendados del instalador.
4. Abre **Anaconda Navigator** desde el menú Inicio. Si se abre correctamente, Anaconda ya está instalado.
5. Abre **Anaconda Prompt** desde el menú Inicio. Ejecuta los comandos de la siguiente sección; no los ejecutes en la consola `(base)` actual.

```powershell
cd "C:\Users\PC\Downloads\Datos NTIC UCM 2025-20260902T223204Z-1-001\TFM_Movilidad_Mallorca"
conda env create -f environment.yml
conda activate tfm-mallorca
python --version
jupyter notebook --version
python -m ipykernel install --user --name tfm-mallorca --display-name "Python (tfm-mallorca)"
```

El segundo comando crea un entorno aislado llamado `tfm-mallorca` con todas las librerías necesarias para las primeras semanas. No trabajes desde `(base)`.

### 2. Docker Desktop

No lo usaremos hasta la semana 6, pero lo instalaremos ahora para no interrumpir el trabajo después.

1. Descarga [Docker Desktop para Windows](https://www.docker.com/products/docker-desktop/).
2. Ejecuta el instalador y acepta la instalación o actualización de WSL 2 si Windows lo solicita.
3. Reinicia el ordenador si el instalador lo pide.
4. Abre Docker Desktop y espera hasta que indique que el motor está en ejecución.
5. En una PowerShell nueva, ejecuta:

```powershell
docker --version
docker info
docker run --rm hello-world
```

No instales PostGIS ni OpenTripPlanner todavía. Docker Desktop es gratuito para educación, aunque la aplicación no es en sí misma software de código abierto; el motor, PostGIS, OpenTripPlanner y las librerías de tu TFM sí podrán ser libres.

## Cuando termines

Vuelve a esta conversación y pega exactamente la salida de estos comandos. Los dos primeros se ejecutan en **Anaconda Prompt**; el último, en PowerShell:

```powershell
conda --version
python --version
docker --version
```

Si aparece un error, pégalo tal cual. Lo resolveremos antes de crear el entorno del proyecto.
