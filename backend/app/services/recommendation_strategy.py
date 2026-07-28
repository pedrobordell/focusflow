from abc import ABC, abstractmethod

from schemas.recommendation_schema import HabitContext, Recommendation


# Interfaz de la CAPA DE ESTRATEGIA de recomendación.
#
# ABC ("Abstract Base Class") es la forma que tiene Python de declarar un interfaz: una clase
# que no se puede instanciar y que obliga a sus hijas a implementar los métodos marcados con
# @abstractmethod. Si alguien intentara hacer RecommendationStrategy() directamente, Python
# lanzaría un TypeError.
#
# El contrato es deliberadamente estrecho: entra una lista de HabitContext (números ya
# calculados) y sale una lista de Recommendation (textos). No aparece la base de datos, ni
# SQLAlchemy, ni FastAPI. Eso tiene dos consecuencias:
#
#   1. La estrategia se prueba con objetos construidos a mano, sin levantar la aplicación.
#   2. Cambiar CÓMO se recomienda (hoy reglas, mañana un modelo entrenado con scikit-learn)
#      solo exige escribir otra clase hija; el servicio, los controladores y el frontend
#      no se enteran. Es el requisito de extensibilidad RNF04 hecho código.
class RecommendationStrategy(ABC):

    @abstractmethod
    def generate(self, contexts: list[HabitContext]) -> list[Recommendation]:
        """Analiza los hábitos del usuario y devuelve los mensajes que procedan.

        La lista puede estar vacía (usuario sin hábitos, o sin nada que señalar) y viene
        ordenada por relevancia: el primer elemento es el que se muestra en el dashboard.
        """
        raise NotImplementedError
