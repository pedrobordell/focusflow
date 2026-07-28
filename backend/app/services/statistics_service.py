from datetime import date, datetime, timedelta

import pandas as pd

from repositories.statistics_repository import StatisticsRepository
from repositories.habit_repository import HabitRepository
from schemas.statistics_schema import (
    ComplianceSummary,
    DayPoint,
    HourPoint,
    HabitHighlight,
    WeeklyHighlights,
    HabitDetail,
    SlotStat,
)

# Franjas horarias cada 6 horas
SLOT_LABELS = ["Early morning", "Morning", "Afternoon", "Evening"]

# Nº de sesiones recientes que resume "Last 10 sessions" en Habit Stats.
LAST_N = 10

# Mínimo de sesiones programadas en una franja para considerarla representativa.
# Por debajo de esto no se propone la franja: con 1 sola sesión el porcentaje
# observado sería 0% o 100% y no significaría nada.
MIN_SLOT_SESSIONS = 3

# Columnas del DataFrame de trabajo (fijas para que un periodo vacío tenga esquema válido).
_DF_COLUMNS = ["habit_id", "habit_name", "date", "hour", "slot", "duration", "completed"]


def _slot_index(hour: int) -> int:
    # Divide el día en 4 franjas (0-3) de 6 horas; asegurándose de que nunca pase de 3
    return min(hour // 6, 3)


class StatisticsService:

    # Recibe StatisticsRepository y HabitRepository
    def __init__(self, stats_repo: StatisticsRepository, habit_repo: HabitRepository):
        self.stats_repo = stats_repo
        self.habit_repo = habit_repo

    # --- Construcción del DataFrame -----------------------------------------

    # Convierte las filas del StatisticsRepository en un DataFrame con las columnas derivadas
    # (hour, slot, duration). Duration se mide en minutos.
    def _rows_to_df(self, rows: list) -> pd.DataFrame:
        records = []
        for r in rows:
            end_date = r.end_date or r.date
            start = datetime.combine(r.date, r.start_time)
            end = datetime.combine(end_date, r.end_time)
            duration = (end - start).total_seconds() / 60
            records.append({
                "habit_id": r.habit_id,
                "habit_name": r.habit_name,
                "date": r.date,
                "hour": r.start_time.hour,
                "slot": _slot_index(r.start_time.hour),
                "duration": duration,
                "completed": bool(r.completed),
            })
        return pd.DataFrame.from_records(records, columns=_DF_COLUMNS)

    # Público: es la entrada de la capa de datos. Además de las pantallas de estadísticas,
    # lo reutiliza el motor de Recomendaciones para construir su contexto.
    def sessions_df(self, user_id: int, date_from: date, date_to: date) -> pd.DataFrame:
        return self._rows_to_df(self.stats_repo.get_sessions_for_stats(user_id, date_from, date_to))

    def _habit_df(self, user_id: int, habit_id: int, date_from: date, date_to: date) -> pd.DataFrame:
        return self._rows_to_df(
            self.stats_repo.get_sessions_for_habit(user_id, habit_id, date_from, date_to)
        )

    # Deveuelve las Sessiones totales, las cumplidas y el ratio de cumplimiento de un DataFrame
    @staticmethod
    def rate(df: pd.DataFrame) -> tuple:
        scheduled = int(len(df))
        completed = int(df["completed"].sum()) if scheduled else 0
        rate = (completed / scheduled) if scheduled else 0.0
        return scheduled, completed, rate

    # Comprueba que el hábito existe y la propiedad
    def _assert_owned(self, user_id: int, habit_id: int):
        habit = self.habit_repo.get_by_id(habit_id)
        if habit is None or habit.user_id != user_id:
            raise ValueError("Habit not found")
        return habit

    # --- Dashboard ----------------------------------------------------------

    def compliance_summary(self, user_id: int, date_from: date, date_to: date) -> ComplianceSummary:
        scheduled, completed, rate = self.rate(self.sessions_df(user_id, date_from, date_to))
        return ComplianceSummary(
            scheduled=scheduled,
            completed=completed,
            compliance_rate=round(rate, 4),
        )

    # --- Series para gráficas ----------------------------------------------

    # Serie por día (Weekly Stats): % de cumplimiento de cada día con sesiones, ordenado.
    def daily_compliance(self, user_id: int, date_from: date, date_to: date) -> list:
        df = self.sessions_df(user_id, date_from, date_to)
        if df.empty:
            return []
        points = []
        # .groupby divide el DF en subcampos con el mismo valor de "date" y devuelve day y el group (subcampo)
        for day, group in df.groupby("date", sort=True):
            _, _, rate = self.rate(group)
            points.append(DayPoint(date=day, compliance_rate=round(rate, 4)))
        return points

    # Serie por hora del día (Habit Stats) para un hábito propio: % por hora con sesiones.
    def hourly_compliance(self, user_id: int, habit_id: int, date_from: date, date_to: date) -> list:
        self._assert_owned(user_id, habit_id)
        df = self._habit_df(user_id, habit_id, date_from, date_to)
        if df.empty:
            return []
        points = []
        # .groupby divide el DF en subcampos con el mismo valor de "hour" y devuelve hour y el group (subcampo)
        for hour, group in df.groupby("hour", sort=True):
            _, _, rate = self.rate(group)
            points.append(HourPoint(hour=int(hour), compliance_rate=round(rate, 4)))
        return points

    # --- Weekly Stats -------------------------------------------------------

    # Destacados de la semana vs la anterior.
    def get_weekly_highlights(self, user_id: int, ref: date = None) -> WeeklyHighlights:
        today = ref or date.today()
        monday = today - timedelta(days=today.weekday())     # lunes de esta semana
        sunday = monday + timedelta(days=6)
        prev_monday = monday - timedelta(days=7)
        prev_sunday = sunday - timedelta(days=7)

        df_now = self.sessions_df(user_id, monday, sunday)
        df_prev = self.sessions_df(user_id, prev_monday, prev_sunday)

        _, _, comp_now = self.rate(df_now)
        _, _, comp_prev = self.rate(df_prev)

        habits = self._week_habits(df_now)
        # Hábitos que tengan horas completadas
        habits_with_hours = [habit for habit in habits if habit.completed_hours > 0]
        if habits_with_hours:
            # key dice el criterio se deben compaara.
            # lambda: Función anónima que devuelve el número de horas completadas
            most_hours = max(habits_with_hours, key=lambda habit: habit.completed_hours)
        else:
            most_hours = None
        # Peor cumplimiento entre hábitos con al menos una sesión programada.
        worst = min(habits, key=lambda h: h.compliance_rate) if habits else None

        return WeeklyHighlights(
            week_from=monday,
            week_to=sunday,
            most_hours=most_hours,
            worst_compliance=worst,
            compliance_now=round(comp_now, 4),
            compliance_prev=round(comp_prev, 4),
            improvement_pp=round((comp_now - comp_prev) * 100, 1),
        )

    # Métricas por hábito de una semana: % y sumatorio de horas cumplidas.
    def _week_habits(self, df: pd.DataFrame) -> list:
        if df.empty:
            return []
        result = []
        for habit_id, group in df.groupby("habit_id", sort=False):
            _, _, rate = self.rate(group)
            done = group[group["completed"]]    # Obtiene solo las filas completadas
            hours = float(done["duration"].sum()) / 60 if not done.empty else 0.0
            result.append(HabitHighlight(
                habit_id=int(habit_id),
                habit_name=str(group["habit_name"].iloc[0]),
                compliance_rate=round(rate, 4),
                completed_hours=round(hours, 1),
            ))
        return result

    # --- Habit Stats --------------------------------------------------------

    def get_habit_detail(self, user_id: int, habit_id: int, date_from: date, date_to: date) -> HabitDetail:
        habit = self._assert_owned(user_id, habit_id)

        # Estado completed de las últimas 10 sesiones
        recent = self.stats_repo.get_recent_completed_for_habit(user_id, habit_id, date.today(), LAST_N)
        
        # Nº de sesiones recientes y su ratio de cumplimiento
        last10_count = len(recent)
        if last10_count:
            completed_recent = recent.count(True)               # cuántas se cumplieron
            last10_rate = round(completed_recent / last10_count, 4)
        else:
            last10_rate = None                                  # evita dividir por 0

        # Mejor franja horaria del hábito en el periodo.
        slots = self.slot_stats(self._habit_df(user_id, habit_id, date_from, date_to))
        best = self.best_slot(slots)
        best_slot = best.label if best else None

        return HabitDetail(
            habit_id=habit.id,
            habit_name=habit.name,
            type=habit.type,
            importance=habit.importance,
            last10_rate=last10_rate,
            last10_count=last10_count,
            best_slot=best_slot,
        )

    # --- Franjas horarias (compartido con Recomendaciones) ------------------

    # Métricas de las 4 franjas horarias de un DataFrame ya filtrado (normalmente de un hábito).
    # Devuelve una entrada por franja CON sesiones; las franjas vacías se omiten.
    #
    # 'probability' aplica el suavizado de Laplace ("regla de sucesión"): en vez de
    # cumplidas / programadas se usa (cumplidas + 1) / (programadas + 2). Así una franja con
    # 1 sesión cumplida no vale 100% sino 67%, y el valor se acerca al porcentaje observado
    # solo a medida que se acumulan sesiones. Es lo que permite comparar franjas con distinto
    # número de muestras sin que una casualidad gane siempre.
    def slot_stats(self, df: pd.DataFrame) -> list[SlotStat]:
        if df.empty:
            return []
        stats = []
        for index, label in enumerate(SLOT_LABELS):
            group = df[df["slot"] == index]     # Filtra solo las filas que sean de la franja
            if group.empty:
                continue
            scheduled, completed, rate = self.rate(group)
            stats.append(SlotStat(
                slot=index,
                label=label,
                scheduled=scheduled,
                completed=completed,
                compliance_rate=round(rate, 4),
                probability=round((completed + 1) / (scheduled + 2), 4),
            ))
        return stats

    # Franja recomendable: la de mayor probabilidad entre las que tienen suficientes sesiones
    # (desempate: más sesiones programadas). None si ninguna franja llega al mínimo.
    @staticmethod
    def best_slot(slots: list[SlotStat]):
        usable = [slot for slot in slots if slot.scheduled >= MIN_SLOT_SESSIONS]
        if not usable:
            return None
        return max(usable, key=lambda slot: (slot.probability, slot.scheduled))
