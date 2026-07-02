# User Notifications

**Program code:** `T0098` (User Notifications)

## Purpose
View and manage system-generated notifications. Shows all notifications sent to users, with the ability to mark individual or all notifications as read, and delete notifications. Used by all system users to stay informed about system events, alerts, and updates.

## How to access
1. Log in to Nova ERP
2. Navigate to **Administration > Notifications** in the sidebar
3. The screen loads at `#/notifications`

## Backing table
`Nova.T0098` — stores all user notification records.

## API prefix
`/api/T0098I`

## Permissions
- **Full access**: Admin (can view, mark read, delete)
- **Read only**: Viewer (can view notifications only)
- Notifications are user-scoped; users typically see their own notifications.

## Dependencies
- Depends on: `T0021` (System Users) — `user_id` foreign key
- Used by: System processes that generate notifications
