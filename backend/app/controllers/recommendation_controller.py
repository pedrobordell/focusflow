from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from controllers.auth_controller import get_current_user
from db.database import get_db
from models.user import User
from repositories.habit_repository import HabitRepository
from repositories.message_repository import MessageRepository
from repositories.statistics_repository import StatisticsRepository
from services import recommendation_charts
from services.recommendation_ml import MLRecommendationStrategy
from services.recommendation_rules import RulesRecommendationStrategy
from services.recommendation_service import RecommendationService
from services.statistics_service import StatisticsService
from schemas.message_schema import MessageResponse
from schemas.recommendation_schema import HabitInsight

# DEPENDENCIAS

# ÚNICO punto del backend donde se nombra la estrategia concreta: cambiar de estrategia
# (p. ej. a una basada en otro modelo) es cambiar esta función y nada más.
#
# La estrategia con modelo (RF16) recibe la de reglas como fallback y le da dos usos: es el
# plan B cuando no hay histórico suficiente para entrenar, y es quien sigue redactando las
# notificaciones de hábito olvidado y de racha (RF15).
def build_strategy() -> MLRecommendationStrategy:
    return MLRecommendationStrategy(fallback=RulesRecommendationStrategy())


# Pide una Session (de la BD), monta los repos, el servicio de estadísticas (capa de datos)
# y le inyecta la estrategia.
def get_recommendation_service(db: Session = Depends(get_db)) -> RecommendationService:
    return RecommendationService(
        stats_service=StatisticsService(
            stats_repo=StatisticsRepository(session=db),
            habit_repo=HabitRepository(session=db),
        ),
        habit_repo=HabitRepository(session=db),
        message_repo=MessageRepository(session=db),
        strategy=build_strategy(),
    )


# Las pantallas del modelo (RF16) necesitan la estrategia suelta, sin el orquestador: no
# generan mensajes, solo diagnostican. Se tipa como MLRecommendationStrategy a propósito,
# porque "explicarse" es algo que solo sabe hacer una estrategia con modelo.
def get_ml_strategy() -> MLRecommendationStrategy:
    return build_strategy()

# CONTROLLER

recommendation_controller = APIRouter(prefix="/recommendations", tags=["Recommendations"])


# Genera las recomendaciones del usuario y devuelve los mensajes de hoy.
#
# Es POST y no GET porque escribe en la base de datos, y un GET no debe tener efectos.
# Lo llama el frontend al abrir el dashboard: es el "el sistema genera al abrir la app" de
# los requisitos, sin tareas programadas ni scheduler.
@recommendation_controller.post("/generate", response_model=list[MessageResponse], status_code=status.HTTP_200_OK)
def generate_recommendations(
    current_user: User = Depends(get_current_user),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
):
    return recommendation_service.generate_and_store(current_user.id)


# Diagnóstico de cada hábito del usuario: estado, probabilidad y tendencia (RF16).
#
# Es GET porque NO escribe: a diferencia de /generate, aquí solo se mira. Lo consume la
# pantalla "Model". Sin hábitos devuelve una lista vacía; sin datos para entrenar, todos los
# hábitos salen con estado "unknown" en lugar de con cifras inventadas.
@recommendation_controller.get("/insights", response_model=list[HabitInsight], status_code=status.HTTP_200_OK)
def get_insights(
    current_user: User = Depends(get_current_user),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
    strategy: MLRecommendationStrategy = Depends(get_ml_strategy),
):
    contexts = recommendation_service.build_contexts(current_user.id)
    return strategy.insights(contexts)


# Gráfica PNG del árbol entrenado con el histórico del usuario.
#
# Como el resto de gráficas de la app, cuando no hay datos devuelve una imagen con el aviso
# en lugar de un error: así el frontend pinta siempre lo mismo, sin ramas de error.
@recommendation_controller.get("/tree-chart")
def get_tree_chart(
    current_user: User = Depends(get_current_user),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
):
    contexts = recommendation_service.build_contexts(current_user.id)
    return Response(
        content=recommendation_charts.decision_tree(contexts),
        media_type="image/png",
    )
