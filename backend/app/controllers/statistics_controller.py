from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from controllers.auth_controller import get_current_user
from db.database import get_db
from models.user import User
from repositories.statistics_repository import StatisticsRepository
from repositories.habit_repository import HabitRepository
from services.statistics_service import StatisticsService
from services import statistics_charts
from schemas.statistics_schema import ComplianceSummary, WeeklyHighlights, HabitDetail

# DEPENDENCIAS

# Pide una Session (de la BD), monta los repos y crea el servicio de estadísticas.
def get_statistics_service(db: Session = Depends(get_db)) -> StatisticsService:
    return StatisticsService(
        stats_repo=StatisticsRepository(session=db),
        habit_repo=HabitRepository(session=db),
    )

# CONTROLLER

statistics_controller = APIRouter(prefix="/statistics", tags=["Statistics"])


# Resumen de cumplimiento propio [from, to] (dashboard)
@statistics_controller.get("/summary", response_model=ComplianceSummary, status_code=status.HTTP_200_OK)
def get_summary(
    date_from: date = Query(..., alias="from"),
    date_to: date = Query(..., alias="to"),
    current_user: User = Depends(get_current_user),
    statistics_service: StatisticsService = Depends(get_statistics_service),
):
    return statistics_service.compliance_summary(current_user.id, date_from, date_to)


# Weekly Stats: gráfica PNG de % de cumplimiento por día en [from, to].
@statistics_controller.get("/daily-chart")
def get_daily_chart(
    date_from: date = Query(..., alias="from"),
    date_to: date = Query(..., alias="to"),
    current_user: User = Depends(get_current_user),
    statistics_service: StatisticsService = Depends(get_statistics_service),
):
    points = statistics_service.daily_compliance(current_user.id, date_from, date_to)
    return Response(content=statistics_charts.compliance_by_day(points), media_type="image/png")


# Weekly Stats: destacados de la semana (actual vs anterior). 'ref' opcional (default hoy).
@statistics_controller.get("/weekly", response_model=WeeklyHighlights, status_code=status.HTTP_200_OK)
def get_weekly(
    ref: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    statistics_service: StatisticsService = Depends(get_statistics_service),
):
    return statistics_service.get_weekly_highlights(current_user.id, ref)


# Habit Stats: gráfica PNG de % de cumplimiento por hora del día de un hábito.
@statistics_controller.get("/habit/{habit_id}/hourly-chart")
def get_hourly_chart(
    habit_id: int,
    date_from: date = Query(..., alias="from"),
    date_to: date = Query(..., alias="to"),
    current_user: User = Depends(get_current_user),
    statistics_service: StatisticsService = Depends(get_statistics_service),
):
    try:
        points = statistics_service.hourly_compliance(current_user.id, habit_id, date_from, date_to)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return Response(content=statistics_charts.compliance_by_hour(points), media_type="image/png")


# Habit Stats: detalle de un hábito propio (info, últimas 10, mejor franja).
@statistics_controller.get("/habit/{habit_id}", response_model=HabitDetail, status_code=status.HTTP_200_OK)
def get_habit_detail(
    habit_id: int,
    date_from: date = Query(..., alias="from"),
    date_to: date = Query(..., alias="to"),
    current_user: User = Depends(get_current_user),
    statistics_service: StatisticsService = Depends(get_statistics_service),
):
    try:
        return statistics_service.get_habit_detail(current_user.id, habit_id, date_from, date_to)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

