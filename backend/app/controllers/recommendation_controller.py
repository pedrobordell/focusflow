from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from controllers.auth_controller import get_current_user
from db.database import get_db
from models.user import User
from repositories.habit_repository import HabitRepository
from repositories.message_repository import MessageRepository
from repositories.statistics_repository import StatisticsRepository
from services.recommendation_rules import RulesRecommendationStrategy
from services.recommendation_service import RecommendationService
from services.statistics_service import StatisticsService
from schemas.message_schema import MessageResponse

# DEPENDENCIAS

# Pide una Session (de la BD), monta los repos, el servicio de estadísticas (capa de datos)
# y le inyecta la estrategia concreta. Este es el ÚNICO punto del backend donde se nombra
# RulesRecommendationStrategy: cambiar de estrategia es cambiar esta línea.
def get_recommendation_service(db: Session = Depends(get_db)) -> RecommendationService:
    return RecommendationService(
        stats_service=StatisticsService(
            stats_repo=StatisticsRepository(session=db),
            habit_repo=HabitRepository(session=db),
        ),
        habit_repo=HabitRepository(session=db),
        message_repo=MessageRepository(session=db),
        strategy=RulesRecommendationStrategy(),
    )

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
