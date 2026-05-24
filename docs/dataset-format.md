# Dataset Format

The app expects honeypot telemetry as either a JSON array or newline-delimited JSON.

## Required Fields

| Field | Type | Description |
| --- | --- | --- |
| `timestamp` | string | Event time in ISO 8601-compatible format. |
| `src_ip` | string | Source IP address that generated the event. |
| `dest_ip` | string | Destination IP address of the honeypot service. |
| `src_port` | integer | Source port used by the remote host. |
| `dest_port` | integer | Destination port on the honeypot. |
| `protocol` | string | Protocol label, such as `ssh`, `http`, `https`, or `ftp`. |
| `action` | string | Honeypot action recorded for the event. |

## Example JSON Array

```json
[
  {
    "timestamp": "2026-01-20T10:15:23.123456",
    "src_ip": "192.168.1.100",
    "src_port": 54321,
    "dest_ip": "10.0.0.5",
    "dest_port": 22,
    "protocol": "ssh",
    "action": "default"
  }
]
```

## Sessionization

Events are grouped by `src_ip`. A new session starts when the gap between events from the same source exceeds the configured session gap.

Default session gap:

```text
15 minutes
```

## Service Inference

The app maps events into service buckets:

- `ssh`: protocol `ssh` or destination port `22`
- `http`: protocol `http` or `https`, or destination ports `80`, `8080`, or `443`
- `ftp`: protocol `ftp` or destination port `21`
- `other`: any event that does not match the above rules

## Privacy Note

Before publishing datasets, remove or anonymize sensitive IP addresses, usernames, payloads, tokens, and infrastructure identifiers.
