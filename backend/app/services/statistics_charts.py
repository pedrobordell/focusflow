import io

import matplotlib
matplotlib.use("Agg")   # backend sin GUI (headless), obligatorio en servidor
from matplotlib.figure import Figure

# Misma paleta que la interfaz: el azul de --accent y un gris de la escala de styles.css.
_ACCENT = "#3f8ae0"
_MUTED = "#6b7480"


# Convierte una figura en PNG.
# Público (igual que empty_png) porque la gráfica del árbol de Recomendaciones reutiliza
# estas dos utilidades: son plomería de figuras, no algo propio de Estadísticas.
def to_png(fig: Figure) -> bytes:
    buffer = io.BytesIO()                                       # Crea un fichero en memoria
    fig.savefig(buffer, format="png", bbox_inches="tight")      # Guarda la figura 
    return buffer.getvalue()                                    # Devuelve un Blob

# Genera un PNG placeholder para cuando no haya datos que graficar
def empty_png(message: str = "No data for this period") -> bytes:
    fig = Figure(figsize=(6, 3.2), dpi=100)
    ax = fig.subplots()
    ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=13, color=_MUTED)
    ax.axis("off")
    return to_png(fig)

# Dibuja un gráfico de barras y lo devuelve como bytes
def _bar_png(labels, values, title, ylabel, ylim=None, value_suffix=""):
    # Figura y ejes
    fig = Figure(figsize=(6, 3.2), dpi=100)
    ax = fig.subplots()
    # Guarda las Barras
    bars = ax.bar(labels, values, color=_ACCENT)
    # Settea el título y la etiqueta
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    # Fija el límite vertical si existe
    if ylim is not None:
        ax.set_ylim(*ylim)  # * "desempaqueta" ylim llega como (0, 100), y se vería como ((0, 100))
    # Quita las líneas top y right del gráfico para mayor limpieza visual
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    # Recorre cada barra con su valor
    for bar, value in zip(bars, values):
        # Escribe el número encima de cada barra
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{value:g}{value_suffix}", ha="center", va="bottom", fontsize=8)
    return to_png(fig)

# Dibuja un gráfico de líneas y lo devuelve como bytes
def _line_png(labels, values, title, ylabel, ylim=None):
    fig = Figure(figsize=(6, 3.2), dpi=100)
    ax = fig.subplots()
    ax.plot(labels, values, marker="o", color=_ACCENT)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    if ylim is not None:
        low, high = ylim
        # Aire arriba y abajo. El marcador de un punto se dibuja CENTRADO sobre su valor, así
        # que uno en el límite exacto (p. ej. 100 %) se quedaría con media circunferencia fuera
        # del área de ejes y Matplotlib la recorta (los Line2D se recortan por defecto).
        # Las marcas se fijan a los valores reales para que el margen no parezca parte de la escala.
        margin = (high - low) * 0.05
        ax.set_ylim(low - margin, high + margin)
        ax.set_yticks([low + (high - low) * i / 4 for i in range(5)])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    # Rota las etiquetas de las fechas 45º para que no se solapen
    ax.tick_params(axis="x", rotation=45, labelsize=7)
    return to_png(fig)


# --- Gráficas concretas ------------------------------------------------------

# Weekly Stats (línea): % de cumplimiento por día del periodo.
def compliance_by_day(points: list) -> bytes:
    if not points:
        return empty_png()
    # Obtiene las etiquetas (fechas formateadas) del eje x
    labels = [p.date.strftime("%m-%d") for p in points]
    # Obtiene la altura: Multiplica el rate * 100 y lo redondea a un decimal
    values = [round(p.compliance_rate * 100, 1) for p in points]
    return _line_png(labels, values, "Compliance by day", "%", ylim=(0, 100))

# Habit Stats (barras): % de cumplimiento por hora de inicio del día.
def compliance_by_hour(points: list) -> bytes:
    if not points:
        return empty_png()
    # Obtiene las etiquetas (horas formateadas) del eje x
    labels = [f"{p.hour:02d}h" for p in points]
    values = [round(p.compliance_rate * 100, 1) for p in points]
    return _bar_png(labels, values, "Compliance by hour of day", "%", ylim=(0, 100), value_suffix="%")
