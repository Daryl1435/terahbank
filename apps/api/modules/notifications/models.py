# Notifications are dispatched via BullMQ queue:notifications.
# No dedicated DB table in Phase 1 — all delivery via FCM, SendGrid, SMS Gateway.
# In-app notification bell: store in a future notifications table at Tier 2.
