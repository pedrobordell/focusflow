from abc import ABC, abstractmethod

from schemas.recommendation_schema import HabitContext, Recommendation


# Interfaz de la CAPA DE ESTRATEGIA de recomendación.
#
# ABC ("Abstract Base Class") es la forma que tiene Python de declarar una interfaz (no se puede instanciar)
#
# Propone el siguiente contrato: entra una lista de HabitContext y sale una lista de Recommendation (textos).
# Esto nos permite cambiar la estrategia de recomendación tan solo escribiendo otra clase hija; 
# el servicio, los controladores y el frontend son los mismos.
class RecommendationStrategy(ABC):

    @abstractmethod
    def generate(self, contexts: list[HabitContext]) -> list[Recommendation]:
        """Recibe lista de HabitContext y devuelve una lista de Recommendation
        """
        raise NotImplementedError
