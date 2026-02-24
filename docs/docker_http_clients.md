# Docker-Hosted MCP Clients (HTTP)

This page shows how to connect MCP clients to a UnityRAG server running in Docker.

The Docker image runs a streamable HTTP MCP server at:
- `http://localhost:8765/mcp` (same machine)
- `http://<host>:8765/mcp` (remote host)

## Before You Connect

- Start the container (see `README.md` Docker quick start).
- First startup can take a while (download + bake + index).
- Watch progress with `docker logs -f unityrag`.
- A plain `GET /mcp` may return `406 Not Acceptable`; that is expected for streamable HTTP when the request does not accept `text/event-stream`.

## Codex (Verified)

Add the Docker-hosted MCP server:

```bash
codex mcp add unity-docs-http --url http://localhost:8765/mcp
```

Remote host example:

```bash
codex mcp add unity-docs-http --url http://<host>:8765/mcp
```

Confirm:

```bash
codex mcp list
```

## Claude Desktop (Planned: verify exact HTTP config schema)

We will document an exact Claude Desktop HTTP MCP config snippet after local verification.

Expected shape (conceptually):
- Use an HTTP/streamable MCP server entry (not `command`/`args`)
- Point it to `http://localhost:8765/mcp` (or remote host URL)
- No UnityRAG process path is needed because Docker is running the server

## Cline / GitHub Copilot / Other MCP Clients (Compatibility Planning)

Use the same endpoint concept:
- `http://localhost:8765/mcp` (local)
- `http://<host>:8765/mcp` (remote)

Client-specific config format varies by product and version. We only publish exact snippets after end-to-end verification.

## Compatibility Status (Docker-hosted HTTP MCP)

| Client | How to Configure | Status | Notes |
| --- | --- | --- | --- |
| Codex | CLI (`codex mcp add ... --url ...`) | Verified | Uses streamable HTTP MCP URL directly |
| Claude Desktop | Desktop config (HTTP MCP entry) | Planned | Exact schema/version to verify before publishing snippet |
| Cline | Client config (HTTP MCP entry) | Planned | Format varies; verify before publishing |
| GitHub Copilot | Product-specific MCP integration | Planned | Verify product support/path before publishing |

## Troubleshooting

- Port collision:
  - Start Docker with a different host port, e.g. `-p 8876:8765`
  - Connect clients to `http://localhost:8876/mcp`
- Container not running:
  - `docker ps`
  - `docker logs -f unityrag`
- Remote host unreachable:
  - Check firewall / LAN routing / port exposure
  - Confirm the server is listening on `0.0.0.0` (Docker image default)
- Client gets an HTTP error on manual browser/curl check:
  - `406` on plain `GET` is usually expected for this transport
