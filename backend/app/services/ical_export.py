from icalendar import Calendar, Event
from datetime import datetime

from models.habit_session import HabitSession

def export_to_iCal(sessions: list[HabitSession])->bytes:

    cal = Calendar()
    cal.add('prodid', '-//Focus Flow//mxm.dk//')
    cal.add('version', '2.0')

    for session in sessions:
        event = Event()
        event.add('uid', f'session-{session.id}@focusflow')
        event.add('summary', f'Habit {session.habit.name}')

        # Combinamos la fecha con las horas de inicio y fin
        dtstart = datetime.combine(session.date, session.start_time)
        dtend = datetime.combine(session.end_date, session.end_time)

        event.add('dtstart', dtstart)
        event.add('dtend', dtend)

        status = 'Completed' if session.completed else 'Not completed'
        event.add('description', f'Status: {status}')

        cal.add_component(event)

    return cal.to_ical()
