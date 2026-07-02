# APIs Used by Dashboard View

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/T0003I/` | GET | Count products |
| `/api/T0010I/` | GET | Count customers |
| `/api/T0011I/` | GET | Count suppliers |
| `/api/T0012I/` | GET | Count sales orders |
| `/api/T0090I/` | GET | Count invoices + recent activity |
| `/api/T0091I/` | GET | Count payments |
| `/api/T0030I/` | GET | Count employees |
| `/api/T0021I/` | GET | Count users |

All requests use the shared `api/client.js` with Bearer token auth.
