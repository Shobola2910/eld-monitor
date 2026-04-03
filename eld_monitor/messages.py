"""
Message templates — 15 variants per alert type to avoid Telegram spam detection.
All messages convey the same meaning but with different wording/structure.

Placeholders:
  {name}       - Driver full name
  {time}       - Remaining time (e.g. "1h 45m")
  {hours}      - Numeric hours
  {status}     - Current duty status
  {duration}   - Duration in current status
  {days}       - Number of days
"""

import random

# ─────────────────────────────────────────────────────────────────────────────
# VIOLATION: Overtime driving
# ─────────────────────────────────────────────────────────────────────────────
VIOLATION_OVERTIME = [
    "🚨 {name} — you are currently exceeding your allowed drive time. Please pull over safely and stop driving immediately.",
    "⛔ DRIVE TIME EXCEEDED — {name}, you've gone over your allowed hours. Stop driving now and log your break.",
    "🔴 {name}: Drive time violation detected. You are over your permitted hours. Find a safe spot and stop now.",
    "‼️ Overtime alert for {name}. You are driving beyond the legal limit. Please park immediately.",
    "🚫 {name}, your drive time has exceeded FMCSA limits. Immediate stop required — find a safe location now.",
    "⚠️ Hours violation — {name} has surpassed the maximum drive time allowed. Stop driving and begin rest period.",
    "🔔 {name}: You've exceeded your drive hours. This is a serious violation. Please stop the vehicle now.",
    "ALERT: {name} is over drive time limits. Parking immediately is required to avoid further violations.",
    "📍 {name} — drive time exceeded. Pull over at the nearest safe stop. This cannot be delayed.",
    "🛑 {name}, you've crossed the drive time threshold. Stop now. Log your rest break immediately.",
    "FMCSA violation detected: {name} has exceeded drive time. Immediate action needed — stop driving now.",
    "🚛 {name}: Over-hours alert. Your current drive time violates federal regulations. Please stop driving.",
    "⏰ {name} — time's up. You've driven beyond your allowed limit. Safely park and start your rest period.",
    "Critical: Drive hours exceeded for {name}. Stop the vehicle immediately and contact dispatch.",
    "🔴 Driving time limit breached — {name}, please find a truck stop or rest area right now.",
]

# ─────────────────────────────────────────────────────────────────────────────
# VIOLATION: PTI not completed
# ─────────────────────────────────────────────────────────────────────────────
VIOLATION_NO_PTI = [
    "⚠️ {name} — you went on duty without completing your Pre-Trip Inspection. Please complete PTI now.",
    "🔔 {name}: PTI not found. A Pre-Trip Inspection is required before driving. Complete it in the app.",
    "📋 Heads up {name} — your Pre-Trip Inspection is missing. Please complete your PTI log right away.",
    "🚨 PTI Alert for {name}: No pre-trip inspection recorded. This is a DOT requirement — complete it now.",
    "‼️ {name}, driving without a completed PTI is a violation. Please fill out your pre-trip inspection.",
    "🔴 {name}: Pre-Trip Inspection not completed. Log your PTI before continuing to drive.",
    "ALERT — {name} has not completed a Pre-Trip Inspection. Required by FMCSA. Do it in the ELD app now.",
    "📝 {name}: Missing PTI. Pre-trip inspections are mandatory. Please complete yours immediately.",
    "⛔ {name} — no Pre-Trip Inspection on file for today. Please complete PTI in your ELD app.",
    "🛡️ {name}, safety reminder: PTI not completed. Take a few minutes to do your pre-trip inspection now.",
    "⚠️ Pre-trip inspection missing for {name}. This is required before every drive. Complete it ASAP.",
    "🔔 {name}: Your PTI is overdue. A Pre-Trip Inspection must be done before operating the vehicle.",
    "📋 {name} — ELD shows no PTI completed. Please open the app and submit your pre-trip inspection.",
    "Missing PTI: {name} needs to complete a Pre-Trip Inspection. Required by law — do it now.",
    "🚛 {name}: No pre-trip inspection recorded today. Complete your PTI to stay compliant.",
]

# ─────────────────────────────────────────────────────────────────────────────
# HOS: Shift time running low (< 2 hours)
# ─────────────────────────────────────────────────────────────────────────────
HOS_SHIFT_LOW = [
    "⏳ {name} — shift time is running low. Only {time} left in your 14-hour window. Plan your stop.",
    "🕐 {name}: {time} left on your shift clock. Start looking for a place to rest soon.",
    "⚠️ Shift time alert — {name}, you have {time} remaining in your shift. Find a spot to park soon.",
    "🔔 {name}: Shift window is nearly over. {time} left. Wrap up your trip and find a safe stop.",
    "📍 {name} — only {time} remaining on your 14-hour shift. Begin planning your rest stop now.",
    "⏰ Heads up {name}: your shift expires in {time}. Locate a truck stop or rest area soon.",
    "🟡 {name}, shift clock warning: {time} left. You need to be parked before your shift ends.",
    "SHIFT ALERT: {name} has {time} left in the current shift window. Pull over before time expires.",
    "🔴 {name}: {time} on your shift remaining. Start your end-of-day routine and find parking.",
    "⚠️ Time check for {name} — your 14-hour shift has {time} left. Don't push it — find rest now.",
    "🕑 {name}: Shift ends in {time}. Make sure you're heading toward a safe stopping point.",
    "⏳ SHIFT LOW — {name}, {time} left. You must stop driving before your shift clock hits zero.",
    "📢 {name}: {time} remaining in your shift. Begin winding down and looking for a stop.",
    "🟠 Shift warning for {name}: only {time} left. Plan your route to a rest area immediately.",
    "⚠️ {name} — shift clock at {time}. Get to a safe parking location before your shift expires.",
]

# ─────────────────────────────────────────────────────────────────────────────
# HOS: Drive time running low (< 2 hours)
# ─────────────────────────────────────────────────────────────────────────────
HOS_DRIVE_LOW = [
    "⏳ {name} — only {time} of drive time left today. Start planning your 30-min break or final stop.",
    "🕐 {name}: Drive clock is at {time}. Consider taking your break now to reset.",
    "⚠️ Drive time low for {name}. {time} remaining before you must stop. Plan accordingly.",
    "🔔 {name}: {time} left on your drive clock. Take your 30-minute break to stay compliant.",
    "📍 {name} — drive time almost up. {time} remaining. Find a safe place to stop soon.",
    "⏰ {name}: Your 11-hour drive limit has {time} left. Start your break planning now.",
    "🟡 Drive alert — {name}, you have {time} of drive time left. Don't wait too long to stop.",
    "DRIVE LOW: {name} has {time} remaining on drive clock. Locate a rest stop ahead.",
    "🔴 {name}: {time} of drive time left. You'll need to stop soon — look for parking.",
    "⚠️ {name} — drive clock warning. {time} left. Stop at the next available rest area.",
    "🕑 {name}: Only {time} left to drive. Take your required break before time runs out.",
    "⏳ DRIVE TIME — {name}, {time} remaining. Begin your rest break to stay within limits.",
    "📢 {name}: Drive time almost exhausted. {time} left. Park up and take your 30-minute break.",
    "🟠 {name}: Drive hours low — {time} remaining. Find a safe stop in the next town.",
    "⚠️ {name} — drive limit approaching. {time} left. Time to pull over and take a break.",
]

# ─────────────────────────────────────────────────────────────────────────────
# HOS: Break time running low (< 2 hours)
# ─────────────────────────────────────────────────────────────────────────────
HOS_BREAK_LOW = [
    "⏳ {name}: You've been off the break clock for a while. Only {time} left before a 30-min break is required.",
    "🔔 {name} — break clock reminder. {time} left before you need to take your mandatory 30-minute break.",
    "⚠️ {name}: Break window closing in {time}. Schedule your 30-minute break soon to stay compliant.",
    "📋 {name}: {time} before mandatory break required. Plan your stop — 30 min off duty needed.",
    "🕐 Break alert for {name}: {time} remaining before a required 30-minute break. Don't skip it.",
    "🟡 {name} — you'll need a 30-minute break in {time}. Find a good spot and plan your stop.",
    "BREAK REMINDER: {name} must take a 30-min break in {time}. Start planning your rest stop.",
    "⏰ {name}: Your break window expires in {time}. A 30-minute off-duty break is coming up.",
    "🔴 {name}: {time} until mandatory break. Pull over for your 30-minute rest to stay legal.",
    "📍 {name} — break needed in {time}. Find a truck stop for your required 30-minute break.",
    "⚠️ {name}: Only {time} left in your break window. Schedule your stop ahead of time.",
    "🕑 Heads up {name}: {time} before mandatory 30-min break. Make sure you can stop safely.",
    "⏳ {name}: Break clock running out — {time} left. Don't drive past your mandatory break.",
    "📢 {name}: Required break in {time}. Find a safe parking spot and take your 30-minute rest.",
    "🟠 {name} — break window closing. {time} remaining. Take your 30-min break before driving further.",
]

# ─────────────────────────────────────────────────────────────────────────────
# HOS: Cycle time running low (< 30 hours)
# ─────────────────────────────────────────────────────────────────────────────
HOS_CYCLE_LOW = [
    "⚠️ {name}: Your 70-hour cycle has {time} left. You're approaching your weekly limit.",
    "🔴 {name} — cycle time alert. Only {time} left in your 8-day cycle. Coordinate with dispatch.",
    "⏳ {name}: Cycle clock is running low — {time} remaining. Plan your schedule accordingly.",
    "🔔 Heads up {name}: {time} left on your weekly cycle. You'll need reset time soon.",
    "📋 {name}: Cycle limit approaching. {time} remaining before 34-hour restart may be needed.",
    "🕐 {name} — only {time} left in your 70-hour/8-day cycle. Plan your rest period with dispatch.",
    "⚠️ CYCLE WARNING — {name}: {time} remaining in the weekly cycle. Contact dispatch for schedule.",
    "📍 {name}: Your cycle is almost full. {time} left. A 34-hour restart may be needed soon.",
    "🟠 {name}: Cycle time running low — {time} left. Review your upcoming trips with dispatch.",
    "⏰ {name} — weekly cycle alert: {time} remaining. Don't overload — plan your rest period.",
    "CYCLE LOW: {name} has {time} left in the 70-hour window. Dispatch coordination needed.",
    "🔴 {name}: {time} of cycle time left. You'll be due for a 34-hour reset soon.",
    "⚠️ {name} — cycle clock at {time}. Plan ahead for your mandatory reset period.",
    "📢 {name}: Only {time} remaining in your weekly cycle. Schedule your 34-hour restart.",
    "🟡 {name}: Cycle warning — {time} left in the 8-day window. Talk to dispatch about your schedule.",
]

# ─────────────────────────────────────────────────────────────────────────────
# Driver Disconnected
# ─────────────────────────────────────────────────────────────────────────────
DRIVER_DISCONNECT = [
    "📵 {name} — your ELD device appears to be disconnected. Please check your device and reconnect.",
    "🔌 DISCONNECT ALERT: {name}'s ELD is offline. Reconnect your device as soon as possible.",
    "⚠️ {name}: ELD connection lost. Make sure your device is plugged in and Bluetooth is on.",
    "🔴 {name} — ELD device not communicating. Check your tablet/phone and reconnect to the truck.",
    "📡 Connection lost for {name}. Your ELD is showing as offline. Please reconnect immediately.",
    "❌ {name}: ELD offline detected. Check your device connection — Bluetooth or cable may be loose.",
    "DISCONNECT: {name}'s ELD has gone offline. Reconnect your device to resume logging.",
    "🔌 {name} — device disconnected from ELD. Please check your hardware and reconnect ASAP.",
    "⚠️ {name}: No ELD signal detected. Check if your device is connected to the ECM port.",
    "📵 ELD disconnect detected for {name}. Reconnect your device to stay compliant.",
    "🔴 {name} — your ELD is showing offline status. Please reconnect your tablet/device now.",
    "📡 {name}: Connection to ELD lost. Ensure your device is paired and connected properly.",
    "❌ ELD offline — {name}, please check your device. Make sure it's connected to the truck ECM.",
    "ALERT: {name}'s ELD device is disconnected. Reconnect before driving further.",
    "🔌 {name} — ELD not responding. Check device connection, restart app if needed.",
]

# ─────────────────────────────────────────────────────────────────────────────
# Status Stuck: On Duty for too long (> 2 hours without change)
# ─────────────────────────────────────────────────────────────────────────────
STATUS_STUCK_ON_DUTY = [
    "👋 {name} — you've been On Duty (not driving) for {duration}. Everything okay? Update your status when ready.",
    "🤙 {name}: Still On Duty for {duration}. If you're loading, waiting, or working — that's fine! Just checking in.",
    "📋 {name} — on duty for {duration} now. No worries, just a check-in. Update your ELD status when things change.",
    "👀 Hey {name}, you've been in On Duty status for {duration}. Let us know everything's good!",
    "✅ Status check for {name}: On Duty for {duration}. If you need to switch status, please do so in the app.",
    "🟡 {name} — you've had On Duty status for {duration}. Just making sure everything is okay with you.",
    "📍 {name}: {duration} in On Duty status. If your situation has changed, please update your ELD.",
    "🤝 Checking in on {name} — On Duty for {duration}. Please update your status if it has changed.",
    "⏰ {name} has been On Duty (not driving) for {duration}. Status update appreciated when available.",
    "👋 Hi {name}! Just a friendly check-in — you've been On Duty for {duration}. How's it going?",
    "📞 {name} — {duration} in On Duty status. All good? Update your status in the ELD app when ready.",
    "🔔 {name}: On Duty check-in. You've been in this status for {duration}. Please update when done.",
    "✅ Status reminder for {name}: {duration} as On Duty. Change status in app when situation changes.",
    "👀 {name} — still On Duty after {duration}. No rush, but please update your status when you can.",
    "🤙 Hey {name}, {duration} on On Duty status. Just checking in — update your ELD when ready!",
]

# ─────────────────────────────────────────────────────────────────────────────
# Profile Not Updated (same for 3+ days)
# ─────────────────────────────────────────────────────────────────────────────
PROFILE_STALE = [
    "📝 {name} — your profile/form has not been updated in {days} days. Please review and update your BOL.",
    "🗂️ {name}: Form data hasn't changed in {days} days. Please check and update your Bill of Lading.",
    "📋 Reminder for {name}: Your profile form is {days} days old. Please take a moment to update your BOL.",
    "🔔 {name} — no form updates in {days} days. If you have new load info, please update your BOL now.",
    "📄 {name}: Your form hasn't been updated since {days} days ago. Please review and update BOL details.",
    "✏️ Update needed — {name}, your profile form is {days} days without changes. Please update your BOL.",
    "🗃️ {name}: Form data is {days} days old. If your load details have changed, please update your BOL.",
    "📝 {name} — {days}-day form reminder. Please take a few minutes to review and update your BOL info.",
    "📋 BOL Update: {name}, your form hasn't changed in {days} days. Please verify and update it.",
    "🔔 {name}: {days} days since your last form update. Please check your profile and update the BOL.",
    "📄 Form check for {name}: {days} days with no updates. Please review your BOL and make changes.",
    "✏️ {name} — just a reminder: your form data is {days} days unchanged. Please update your BOL.",
    "🗂️ {name}: Profile form reminder — {days} days since last update. Update your Bill of Lading now.",
    "📝 BOL reminder for {name}: Please update your form — it hasn't been changed in {days} days.",
    "🔔 Update request for {name}: {days} days since form update. Please review and update your BOL.",
]

# ─────────────────────────────────────────────────────────────────────────────
# Certification Missing
# ─────────────────────────────────────────────────────────────────────────────
CERTIFICATION_MISSING = [
    "✍️ {name} — your logs have not been certified. Please certify your ELD logs in the app.",
    "📋 {name}: Log certification required. Please open your ELD app and certify your recent logs.",
    "🔔 Certification needed — {name}, your ELD logs are not yet certified. Please do this now.",
    "⚠️ {name}: Uncertified logs detected. Please certify your logs in the ELD app immediately.",
    "✅ {name} — your logs need certification. Open the app and certify to stay compliant.",
    "📝 Reminder for {name}: Please certify your ELD logs. This is required under FMCSA regulations.",
    "🔴 {name}: Log certification missing. Please certify your recent ELD logs as soon as possible.",
    "CERTIFY LOGS: {name}, your ELD logs are pending certification. Please certify them now.",
    "✍️ {name} — certify your logs reminder. Open your ELD app and certify your daily records.",
    "📋 {name}: Your logs from the past day(s) need to be certified. Please do so in your ELD app.",
    "⚠️ {name}: ELD certification required. Uncertified logs can result in violations — certify now.",
    "✅ Certification alert for {name}: Your ELD logs need your signature. Please certify ASAP.",
    "🔔 {name} — please certify your logs. Open ELD app → Logs → Certify. Takes under a minute.",
    "📝 {name}: Logs uncertified for {days} day(s). This is required daily. Please certify now.",
    "LOGS: {name}, please certify your ELD records. Required by FMCSA — open app and certify.",
]


# ─────────────────────────────────────────────────────────────────────────────
# Message selector — picks a random variant from the given alert type
# ─────────────────────────────────────────────────────────────────────────────
ALERT_TEMPLATES = {
    "violation_overtime":   VIOLATION_OVERTIME,
    "violation_no_pti":     VIOLATION_NO_PTI,
    "hos_shift_low":        HOS_SHIFT_LOW,
    "hos_drive_low":        HOS_DRIVE_LOW,
    "hos_break_low":        HOS_BREAK_LOW,
    "hos_cycle_low":        HOS_CYCLE_LOW,
    "driver_disconnect":    DRIVER_DISCONNECT,
    "status_stuck_on_duty": STATUS_STUCK_ON_DUTY,
    "profile_stale":        PROFILE_STALE,
    "certification_missing": CERTIFICATION_MISSING,
}


def get_message(alert_type: str, **kwargs) -> str:
    """
    Returns a random message for the given alert type,
    formatted with the provided keyword arguments.
    
    Usage:
        get_message("hos_shift_low", name="John Smith", time="1h 30m")
    """
    templates = ALERT_TEMPLATES.get(alert_type)
    if not templates:
        raise ValueError(f"Unknown alert type: {alert_type}")
    
    template = random.choice(templates)
    return template.format(**kwargs)


def get_message_at_index(alert_type: str, index: int, **kwargs) -> str:
    """
    Returns a specific message variant (useful for avoiding repeats).
    Index wraps around if out of range.
    """
    templates = ALERT_TEMPLATES.get(alert_type)
    if not templates:
        raise ValueError(f"Unknown alert type: {alert_type}")
    
    template = templates[index % len(templates)]
    return template.format(**kwargs)
