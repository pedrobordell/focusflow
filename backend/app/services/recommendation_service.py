from datetime import date, datetime, timedelta

import pandas as pd

from models.message import Message
from repositories.habit_repository import HabitRepository
from repositories.message_repository import MessageRepository
from schemas.recommendation_schema import HabitContext, SessionFeature
from services.recommendation_strategy import RecommendationStrategy
from services.statistics_service import StatisticsService

# Ventana sobre la que se mide el cumplimiento (últimos 30 días)
ANALYSIS_DAYS = 30

# Para pedir todo el histórico del usuario en una sola consulta, sin filtrar por fechas. 
FAR_PAST = date(1970, 1, 1)
FAR_FUTURE = date(9999, 12, 31)


# Orquestador del subsistema de Recomendaciones. Une las tres capas sin implementar ninguna
#   1. StatisticsService (capa de datos),
#   2. La estrategia inyectada (capa de estrategia),
#   3. Message (capa de persistencia).
class RecommendationService:

    def __init__(
        self,
        stats_service: StatisticsService,
        habit_repo: HabitRepository,
        message_repo: MessageRepository,
        strategy: RecommendationStrategy,
    ):
        self.stats_service = stats_service
        self.habit_repo = habit_repo
        self.message_repo = message_repo
        self.strategy = strategy

    # --- Punto de entrada ---------------------------------------------------

    # Genera los nuevos mensajes comprobando que no se hayan generado ya ese mismo día
    def generate_and_store(self, user_id: int, today: date = None) -> list[Message]:
        today = today or date.today()

        contexts = self.build_contexts(user_id, today)
        recommendations = self.strategy.generate(contexts)

        # Toda la tanda comparte el mismo instante. Así al ordenarlos por fecha se ordenan 
        # por id y no se invierten, porque en caso de desempate se decide por id.
        generated_at = datetime.now()

        existing_titles = self.message_repo.get_titles_created_on(user_id, today)
        new_messages = [
            Message(
                user_id=user_id,
                type=recommendation.type,
                title=recommendation.title,
                content=recommendation.content,
                created_at=generated_at,
            )
            for recommendation in recommendations
            if recommendation.title not in existing_titles
        ]
        self.message_repo.create_many(new_messages)

        return self.message_repo.get_by_user_and_day(user_id, today)

    # --- Capa de datos: de filas a HabitContext ------------------------------

    # Construye la fotografía de cada hábito del usuario.
    #
    # Se hace con UNA sola consulta (todo el histórico del usuario) que después se trocea por
    # hábito con Pandas.
    def build_contexts(self, user_id: int, today: date = None) -> list[HabitContext]:
        today = today or date.today()

        habits = self.habit_repo.get_by_user(user_id)
        if not habits:
            return []

        df_all = self.stats_service.sessions_df(user_id, FAR_PAST, FAR_FUTURE)
        # Los hábitos del DataFrame que tienen alguna sesión (pasada o futura).
        scheduled_habit_ids = set(df_all["habit_id"])

        # Obtiene un df con las sesiones pasadas (las que sirven para realizar métricas)
        empty_df = df_all.iloc[0:0]
        df_past = df_all[df_all["date"] <= today] if not df_all.empty else empty_df

        # Obtiene un diccionario con un df por habit_id con sus respectivas sesiones
        sessions_by_habit = (
            {habit_id: group for habit_id, group in df_past.groupby("habit_id", sort=False)}
            if not df_past.empty else {}
        )

        window_start = today - timedelta(days=ANALYSIS_DAYS - 1)

        contexts = []
        for habit in habits:
            habit_df = sessions_by_habit.get(habit.id, empty_df)

            # Cumplimiento reciente (ventana de análisis).
            window_df = habit_df[habit_df["date"] >= window_start] if not habit_df.empty else empty_df
            scheduled, completed, rate = self.stats_service.rate(window_df)

            # Franjas horarias sobre todo el histórico + la franja recomendable (si la hay).
            slots = self.stats_service.slot_stats(habit_df)

            contexts.append(HabitContext(
                habit_id=habit.id,
                habit_name=habit.name,
                importance=habit.importance,
                analysis_days=ANALYSIS_DAYS,
                scheduled=scheduled,
                completed=completed,
                compliance_rate=round(rate, 4),
                days_since_last_completed=self._days_since(
                    habit_df[habit_df["completed"]] if not habit_df.empty else empty_df, today
                ),
                days_since_last_session=self._days_since(habit_df, today),
                current_streak=self._current_streak(habit_df),
                ever_scheduled=habit.id in scheduled_habit_ids,
                slots=slots,
                best_slot=self.stats_service.best_slot(slots),
                sessions=self._session_features(habit_df),
            ))
        return contexts

    # Convierte las sesiones pasadas de un hábito en las filas que entrenan al modelo.
    #
    # Se hace AQUÍ, en la capa de datos, y no en la estrategia: así la estrategia sigue
    # recibiendo solo números y no se entera de que existe Pandas.
    #
    # day_index se cuenta desde la primera sesión del hábito, no desde una fecha absoluta,
    # porque lo único que se le pide es medir la TENDENCIA (si el cumplimiento sube o baja
    # con el tiempo); el origen concreto de la cuenta da igual para el signo de la pendiente.
    @staticmethod
    def _session_features(df: pd.DataFrame) -> list[SessionFeature]:
        if df.empty:
            return []

        first_date = df["date"].min()
        return [
            SessionFeature(
                slot=int(row.slot),
                weekday=row.date.weekday(),
                duration=float(row.duration),
                completed=bool(row.completed),
                day_index=(row.date - first_date).days,
            )
            for row in df.itertuples()
        ]

    # Días transcurridos desde la sesión más reciente del DataFrame. None si está vacío.
    @staticmethod
    def _days_since(df: pd.DataFrame, today: date):
        if df.empty:
            return None
        return (today - df["date"].max()).days

    # Sesiones cumplidas consecutivas contando hacia atrás desde la más reciente. El Dataframe ya viene
    # ordenado por fecha y hora
    @staticmethod
    def _current_streak(df: pd.DataFrame) -> int:
        streak = 0
        for completed in reversed(list(df["completed"])):
            if not completed:
                break
            streak += 1
        return streak
