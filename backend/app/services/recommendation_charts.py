import matplotlib
matplotlib.use("Agg")   # Para renderizar una gráfica en memoria sin abrir una ventana gráfica
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

CV_FOLDS = 3                                # Mínimo de particiones de la validación cruzada.
CLASS_NAMES = ["Missed", "Completed"]       # Nombres legibles de la etiqueta


# Mide qué tal predice el árbol comparándolo con línea base más básica.
def _evaluation_label(frame) -> str:
    labels = frame["completed"]
    baseline = labels.value_counts(normalize=True).max()

    # Comprueba que haya un mínimo de particiones para la validación cruzada
    if labels.value_counts().min() < CV_FOLDS:
        return f"Majority baseline {baseline:.0%} (too few sessions to cross-validate)"

    # shuffle=True para mezclar las filas porque vienen agrupadas por hábito
    # random_state fijo para que la métrica no cambie en cada recarga.
    folds = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    scores = cross_val_score(new_tree(), frame[FEATURES], labels, cv=folds)

    # Se escribe la precisón media junto a la desviación
    return (
        f"{CV_FOLDS}-fold accuracy {scores.mean():.0%} ±{scores.std():.0%} "
        f"vs {baseline:.0%} majority baseline"
    )


# Dibuja el árbol binario entrenado con el histórico del usuario.
def decision_tree(contexts: list[HabitContext]) -> bytes:
    tree = train_tree(contexts)
    if tree is None:
        return empty_png("Not enough sessions yet to train the model")

    frame = training_frame(contexts)

    # Crea la figura con el ancho para que no se solapen las cajas y la asocia 
    # al Canvas
    fig = Figure(figsize=(12, 6.5), dpi=100)

    FigureCanvasAgg(fig)

    ax = fig.subplots()
    plot_tree(
        tree,
        feature_names=FEATURES,     # variables
        class_names=CLASS_NAMES,
        filled=True,                # colorea cada nodo según la clase que predice
        rounded=True,
        impurity=False,             # el índice Gini (desigualdad) sobra
        fontsize=8,
        ax=ax,
    )
    ax.set_title(
        f"How the model decides - {_evaluation_label(frame)}",
        fontsize=10,
    )
    return to_png(fig)
