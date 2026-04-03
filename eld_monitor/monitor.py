"""
ELD Monitor
Checks all drivers every minute for violations and HOS issues.
Sends alerts every 30 minutes (configurable) until the issue is resolved.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, field

from eld_client import ELDDriver
from messages import get_message_at_index

logger = logging.getLogger(__name__)


@dataclass
class ActiveAlert:
    """Tracks an active alert so we don't spam too much."""
    driver_id: str
    driver_name: str
    alert_type: str
    first_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_sent: Optional[datetime] = None
    send_count: int = 0
    message_index: int = 0  # cycles through 15 variants

    def should_send(self, repeat_interval_minutes: int) -> bool:
        """Returns True if enough time has passed to send another alert."""
        if self.last_sent is None:
            return True
        elapsed = (datetime.now(timezone.utc) - self.last_sent).total_seconds() / 60
        return elapsed >= repeat_interval_minutes

    def next_message_index(self) -> int:
        """Cycles through message variants (0–14) to avoid repetition."""
        idx = self.message_index
        self.message_index = (self.message_index + 1) % 15
        return idx


def format_time(hours: float) -> str:
    """Format decimal hours into 'Xh Ym' string."""
    total_minutes = int(hours * 60)
    h = total_minutes // 60
    m = total_minutes % 60
    if h > 0 and m > 0:
        return f"{h}h {m}m"
    elif h > 0:
        return f"{h}h"
    else:
        return f"{m}m"


def format_duration(minutes: float) -> str:
    """Format minutes into human-readable string."""
    if minutes < 60:
        return f"{int(minutes)} minutes"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    if mins > 0:
        return f"{hours}h {mins}m"
    return f"{hours} hours"


class ViolationChecker:
    """
    Checks a driver's data against FMCSA rules and company policies.
    Returns a list of (alert_type, message_kwargs) tuples for each violation found.
    """

    def __init__(self, settings: dict):
        self.hos_shift_warning = settings.get("hos_shift_warning_hours", 2)
        self.hos_drive_warning = settings.get("hos_drive_warning_hours", 2)
        self.hos_break_warning = settings.get("hos_break_warning_hours", 2)
        self.hos_cycle_warning = settings.get("hos_cycle_warning_hours", 30)
        self.on_duty_stuck_hours = settings.get("on_duty_stuck_hours", 2)
        self.profile_stale_days = settings.get("profile_stale_days", 3)

    def check(self, driver: ELDDriver) -> list[tuple[str, dict]]:
        """
        Check all rules for a driver.
        Returns list of (alert_type, kwargs_for_message).
        """
        violations = []
        name = driver.full_name

        # 1. Drive time violation (overtime)
        if driver.drive_violation or driver.drive_remaining_hours < 0:
            violations.append(("violation_overtime", {"name": name}))

        # 2. No PTI
        if not driver.has_pti and driver.status in ("driving", "on_duty", "D", "ON"):
            violations.append(("violation_no_pti", {"name": name}))

        # 3. HOS warnings (only if driver is active, not in off-duty/sleeper)
        is_active = driver.status not in ("off_duty", "sleeper_berth", "OFF", "SB")

        if is_active:
            if 0 < driver.shift_remaining_hours < self.hos_shift_warning:
                violations.append(("hos_shift_low", {
                    "name": name,
                    "time": format_time(driver.shift_remaining_hours)
                }))

            if 0 < driver.drive_remaining_hours < self.hos_drive_warning:
                violations.append(("hos_drive_low", {
                    "name": name,
                    "time": format_time(driver.drive_remaining_hours)
                }))

            if 0 < driver.break_remaining_hours < self.hos_break_warning:
                violations.append(("hos_break_low", {
                    "name": name,
                    "time": format_time(driver.break_remaining_hours)
                }))

        if 0 < driver.cycle_remaining_hours < self.hos_cycle_warning:
            violations.append(("hos_cycle_low", {
                "name": name,
                "time": format_time(driver.cycle_remaining_hours),
                "hours": f"{driver.cycle_remaining_hours:.1f}"
            }))

        # 4. Driver disconnected
        if not driver.connected:
            violations.append(("driver_disconnect", {"name": name}))

        # 5. Stuck On Duty (not driving) for too long
        if driver.status in ("on_duty", "ON", "on_duty_not_driving"):
            duration_min = driver.status_duration_minutes()
            if duration_min and duration_min > (self.on_duty_stuck_hours * 60):
                violations.append(("status_stuck_on_duty", {
                    "name": name,
                    "duration": format_duration(duration_min)
                }))

        # 6. Profile/form stale
        if driver.last_profile_update:
            try:
                if isinstance(driver.last_profile_update, str):
                    last = datetime.fromisoformat(driver.last_profile_update.replace("Z", "+00:00"))
                else:
                    last = datetime.fromtimestamp(driver.last_profile_update, tz=timezone.utc)
                days_old = (datetime.now(timezone.utc) - last).days
                if days_old >= self.profile_stale_days:
                    violations.append(("profile_stale", {
                        "name": name,
                        "days": str(days_old)
                    }))
            except Exception:
                pass

        # 7. Certification missing
        if not driver.logs_certified:
            days = getattr(driver, "uncertified_days", 1)
            violations.append(("certification_missing", {
                "name": name,
                "days": str(days)
            }))

        return violations


class AlertTracker:
    """
    Tracks active alerts and decides when to (re)send them.
    Prevents duplicate alerts within the repeat interval window.
    """

    def __init__(self, repeat_interval_minutes: int = 30):
        self.repeat_interval = repeat_interval_minutes
        self._alerts: dict[str, ActiveAlert] = {}  # key = "driver_id:alert_type"

    def _key(self, driver_id: str, alert_type: str) -> str:
        return f"{driver_id}:{alert_type}"

    def should_send(self, driver_id: str, alert_type: str) -> bool:
        key = self._key(driver_id, alert_type)
        alert = self._alerts.get(key)
        if not alert:
            return True
        return alert.should_send(self.repeat_interval)

    def mark_sent(self, driver_id: str, driver_name: str, alert_type: str) -> int:
        """Mark an alert as sent. Returns the message variant index to use."""
        key = self._key(driver_id, alert_type)
        if key not in self._alerts:
            self._alerts[key] = ActiveAlert(driver_id, driver_name, alert_type)
        alert = self._alerts[key]
        alert.last_sent = datetime.now(timezone.utc)
        alert.send_count += 1
        return alert.next_message_index()

    def clear_resolved(self, driver_id: str, current_violations: list[str]):
        """Remove alerts for issues that are no longer occurring."""
        prefix = f"{driver_id}:"
        resolved_keys = [
            k for k in self._alerts
            if k.startswith(prefix) and k.split(":", 1)[1] not in current_violations
        ]
        for k in resolved_keys:
            logger.info(f"Alert resolved: {k}")
            del self._alerts[k]

    def active_count(self) -> int:
        return len(self._alerts)

    def get_all_active(self) -> list[ActiveAlert]:
        return list(self._alerts.values())


class ELDMonitor:
    """
    Main monitoring loop.
    Polls ELD every minute, checks for violations, sends Telegram alerts.
    """

    def __init__(self, eld_clients: list, telegram_manager, settings: dict):
        self.eld_clients = eld_clients
        self.telegram = telegram_manager
        self.settings = settings
        self.checker = ViolationChecker(settings)
        self.alert_tracker = AlertTracker(
            repeat_interval_minutes=settings.get("alert_repeat_interval_minutes", 30)
        )
        self._running = False
        self.poll_interval = settings.get("poll_interval_seconds", 60)

    async def run(self):
        """Start the monitoring loop. Runs until stop() is called."""
        self._running = True
        logger.info(f"ELD Monitor started — polling every {self.poll_interval}s")

        while self._running:
            try:
                await self._poll_cycle()
            except Exception as e:
                logger.error(f"Poll cycle error: {e}", exc_info=True)

            await asyncio.sleep(self.poll_interval)

    async def stop(self):
        self._running = False

    async def _poll_cycle(self):
        """One full polling cycle: fetch all driver data and process alerts."""
        logger.info("=== Poll cycle started ===")

        all_drivers: list[ELDDriver] = []

        # Fetch from all ELD accounts
        for client in self.eld_clients:
            try:
                drivers = await client.get_all_driver_data()
                all_drivers.extend(drivers)
                logger.info(f"[{client.account_name}] Got {len(drivers)} drivers")
            except Exception as e:
                logger.error(f"Failed to fetch from {client.account_name}: {e}")

        # Process each driver
        for driver in all_drivers:
            await self._process_driver(driver)

        logger.info(f"=== Poll cycle done — {len(all_drivers)} drivers, "
                    f"{self.alert_tracker.active_count()} active alerts ===")

    async def _process_driver(self, driver: ELDDriver):
        """Check violations for one driver and send necessary alerts."""
        violations = self.checker.check(driver)
        current_types = [v[0] for v in violations]

        # Clear resolved alerts
        self.alert_tracker.clear_resolved(driver.id, current_types)

        # Process each violation
        for alert_type, kwargs in violations:
            if not self.alert_tracker.should_send(driver.id, alert_type):
                continue

            # Get message variant index (cycles through 0-14)
            idx = self.alert_tracker.mark_sent(driver.id, driver.full_name, alert_type)

            try:
                message = get_message_at_index(alert_type, idx, **kwargs)
                success = await self.telegram.send_alert(driver.full_name, message)
                if success:
                    logger.info(f"Alert sent: {driver.full_name} — {alert_type} (variant #{idx})")
                else:
                    logger.warning(f"Alert NOT sent: {driver.full_name} — {alert_type}")
            except Exception as e:
                logger.error(f"Error sending alert for {driver.full_name}/{alert_type}: {e}")
