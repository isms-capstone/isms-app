import pytest
from datetime import datetime, timedelta
from app.core.working_days import add_business_days, is_auto_close_eligible

def test_add_business_days_skips_weekends():
    # วันศุกร์ที่ 9 ต.ค. + 3 วันทำการ -> ศุกร์(1) -> จันทร์(2) -> อังคาร(3) -> พุธที่ 14 ต.ค.
    friday = datetime(2026, 10, 9, 10, 0, 0)
    expected_wednesday = datetime(2026, 10, 14, 10, 0, 0)
    
    result = add_business_days(friday, 3)
    assert result == expected_wednesday

def test_auto_close_eligibility():
    resolved_at = datetime(2026, 10, 12, 10, 0, 0) # วันจันทร์
    
    # ยังไม่ครบ 3 วันทำการ (วันพุธ) -> False
    current_wednesday = datetime(2026, 10, 14, 10, 0, 0)
    assert is_auto_close_eligible(resolved_at, current_wednesday, 3) is False
    
    # ครบ 3 วันทำการพอดี (วันพฤหัสบดี) -> True
    current_thursday = datetime(2026, 10, 15, 10, 0, 0)
    assert is_auto_close_eligible(resolved_at, current_thursday, 3) is True