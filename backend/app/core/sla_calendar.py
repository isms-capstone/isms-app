"""Time arithmetic on UTC intervals using the company's local business calendar."""
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Schedule:
    zone: str = "Asia/Bangkok"
    start: time = time(8)
    end: time = time(17)
    weekdays: tuple[bool, ...] = (True, True, True, True, True, False, False)
    holidays: frozenset = frozenset()

    @property
    def day_seconds(self):
        return int((datetime.combine(datetime.min, self.end) -
                    datetime.combine(datetime.min, self.start)).total_seconds())

    def seconds(self, start, end):
        if end <= start:
            return 0
        zone = ZoneInfo(self.zone)
        day = start.replace(tzinfo=timezone.utc).astimezone(zone).date()
        last_day = end.replace(tzinfo=timezone.utc).astimezone(zone).date()
        total = timedelta()
        while day <= last_day:
            if self.weekdays[day.weekday()] and day not in self.holidays:
                opening, closing = (
                    datetime.combine(day, hour, zone).astimezone(timezone.utc).replace(tzinfo=None)
                    for hour in (self.start, self.end)
                )
                total += max(timedelta(), min(end, closing) - max(start, opening))
            day += timedelta(days=1)
        return int(total.total_seconds())
