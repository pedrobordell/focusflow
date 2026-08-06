import matplotlib
matplotlib.use("Agg")   # backend sin GUI (headless), obligatorio en servidor
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.tree import plot_tree

from schemas.recommendation_schema import HabitContext
from services.recommendation_ml import (
    FEATURES,
    RANDOM_STATE,
    new_tree,
    train_tree,
    training_frame,
)
from services.statistics_charts import empty_png, to_png

# Particiones de la validación cruzada. Con 3 basta para dar una idea honesta sin quedarse
# sin datos en cada partición; subirlo con ~100 sesiones solo añadiría ruido.
CV_FOLDS = 3

# Nombres legibles de la etiqueta que aprende el árbol (completed 0/1).
CLASS_NAMES = ["Missed", "Completed"]


# Mide qué tal predice el árbol y lo compara con la línea base más tonta posible: acertar
# siempre la clase mayoritaria ("di que sí a todo").
#
# La comparación es lo importante. Un 70% de acierto suena bien, pero si el 70% de las
# sesiones se cumplen, ese mismo 70% lo consigue no mirar los datos. Se muestra pegada a la
# figura para que el modelo se lea siempre junto a lo que de verdad aporta.
def _evaluation_label(frame) -> str:
    labels = frame["completed"]
    baseline = labels.value_counts(normalize=True).max()

    # La validación cruzada estratificada necesita al menos CV_FOLDS ejemplos de cada clase.
    if labels.value_counts().min() < CV_FOLDS:
        return f"Majority baseline {baseline:.0%} (too few sessions to cross-validate)"

    # shuffle=True es imprescindible aquí: las filas llegan AGRUPADAS POR HÁBITO (así las
    # construye la capa de datos). Sin barajar, cada partición se llevaría hábitos distintos
    # y estaríamos midiendo si el modelo generaliza de un hábito a otro, que no es lo que
    # hace en producción. random_state fijo para que la métrica no cambie en cada recarga.
    folds = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    scores = cross_val_score(new_tree(), frame[FEATURES], labels, cv=folds)

    # Se publica la desviación junto a la media a propósito: con un centenar de sesiones la
    # diferencia entre particiones es de varios puntos, y dar un número pelado sugeriría una
    # precisión que la medida no tiene.
    return (
        f"{CV_FOLDS}-fold accuracy {scores.mean():.0%} ±{scores.std():.0%} "
        f"vs {baseline:.0%} majority baseline"
    )


# Dibuja el árbol entrenado con el histórico del usuario.
#
# Es la gráfica más importante del subsistema: enseña, rama a rama, POR QUÉ el sistema
# recomienda lo que recomienda. Un modelo que no se puede enseñar no sirve como apoyo a la
# decisión (RNF06), y por eso el árbol se mantiene a profundidad 3 aunque uno más profundo
# pudiera acertar algo más.
def decision_tree(contexts: list[HabitContext]) -> bytes:
    tree = train_tree(contexts)
    if tree is None:
        return empty_png("Not enough sessions yet to train the model")

    frame = training_frame(contexts)

    # Un árbol de profundidad 3 llega a 8 hojas y necesita sitio a lo ancho: por debajo de
    # estas pulgadas las cajas se solapan y matplotlib recorta el texto. Como en pantalla se
    # ve reducido a media columna, la plantilla ofrece además abrirlo a tamaño completo.
    fig = Figure(figsize=(12, 6.5), dpi=100)
    # plot_tree mide el texto antes de dibujarlo, y para eso pide el renderer del canvas.
    # Las figuras creadas con Figure() (sin pyplot, como en el resto del proyecto) nacen con
    # un canvas base que no lo tiene, así que hay que engancharle el de Agg a mano.
    FigureCanvasAgg(fig)

    ax = fig.subplots()
    plot_tree(
        tree,
        feature_names=FEATURES,
        class_names=CLASS_NAMES,
        filled=True,             # colorea cada nodo según la clase que predice
        rounded=True,
        impurity=False,          # el índice Gini sobra para leer el árbol
        fontsize=8,
        ax=ax,
    )
    ax.set_title(
        f"How the model decides — {_evaluation_label(frame)}",
        fontsize=10,
    )
    return to_png(fig)
