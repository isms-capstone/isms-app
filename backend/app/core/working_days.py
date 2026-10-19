from datetime import datetime, timedelta

def add_business_days(from_date: datetime, business_days: int) -> datetime:
    """คำนวณเวลาถัดไปตามจำนวนวันทำการ (ไม่นับวันเสาร์-อาทิตย์)"""
    current_date = from_date
    added = 0
    while added < business_days:
        current_date += timedelta(days=1)
        # 0 = Monday, 5 = Saturday, 6 = Sunday
        if current_date.weekday() < 5:
            added += 1
    return current_date

def is_auto_close_eligible(resolved_at: datetime, current_time: datetime, allowed_business_days: int = 3) -> bool:
    """ตรวจสอบว่า Ticket เกินกำหนดวันทำการสำหรับการ Auto-close แล้วหรือยัง"""
    if not resolved_at:
        return False
    threshold_time = add_business_days(resolved_at, allowed_business_days)
    return current_time >= threshold_time