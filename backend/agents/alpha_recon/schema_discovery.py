"""
Alpha V6 Schema Discovery — OpenAPI, Swagger, GraphQL, Postman.

Discovers and parses API schemas from live targets to extract
endpoints, parameters, and authentication requirements.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from backend.agents.alpha_recon.models import stable_id
from backend.parsers.recon.base import ParsedEntity

logger = logging.getLogger("alpha.schema_discovery")

# Common paths where API specs live
OPENAPI_PATHS = [
    "/openapi.json", "/openapi.yaml", "/openapi.yml",
    "/swagger.json", "/swagger.yaml", "/swagger/v1/swagger.json",
    "/api-docs", "/api-docs/swagger.json", "/api/swagger.json",
    "/v1/swagger.json", "/v2/swagger.json", "/v3/swagger.json",
    "/api/v1/swagger.json", "/api/v2/swagger.json",
    "/docs/openapi.json", "/.well-known/openapi.json",
    "/api/openapi.json", "/api/docs",
    "/swagger-ui.html", "/swagger-ui/",
    "/redoc", "/rapidoc",
]

GRAPHQL_PATHS = [
    "/graphql", "/graphiql", "/playground",
    "/api/graphql", "/v1/graphql", "/gql",
    "/graphql/console", "/altair",
]

POSTMAN_PATHS = [
    "/postman_collection.json", "/api/postman",
    "/.postman/collection.json",
]

GRAPHQL_INTROSPECTION_QUERY = """
query IntrospectionQuery {
  __schema {
    queryType { name }
    mutationType { name }
    types {
      kind name description
      fields(includeDeprecated: true) {
        name description
        args { name type { name kind ofType { name kind } } }
        type { name kind ofType { name kind } }
      }
    }
  }
}
""".strip()


class SchemaDiscovery:
    """Discovers and parses API schemas from target URLs."""

    def __init__(self, scan_id: str, http_client=None):
        self.scan_id = scan_id
        self._http = http_client

    async def discover_all(self, base_urls: list[str]) -> list[ParsedEntity]:
        """Run full schema discovery against all base URLs."""
        all_entities: list[ParsedEntity] = []
        for base in base_urls[:20]:  # Limit to 20 targets
            all_entities.extend(await self.discover_openapi(base))
            all_entities.extend(await self.discover_graphql(base))
        return all_entities

    async def discover_openapi(self, base_url: str) -> list[ParsedEntity]:
        """Probe common OpenAPI/Swagger endpoints."""
        entities: list[ParsedEntity] = []
        if not self._http:
            return entities

        for path in OPENAPI_PATHS:
            try:
                url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
                resp = await self._http.get(url, timeout=10)
                if resp.status_code != 200:
                    continue
                ct = resp.headers.get("content-type", "")
                body = resp.text[:500_000]

                # Detect if it's a JSON spec
                if "json" in ct or body.strip().startswith("{"):
                    try:
                        spec = json.loads(body)
                    except json.JSONDecodeError:
                        continue

                    # Validate it looks like an OpenAPI spec
                    if "paths" not in spec and "swagger" not in spec and "openapi" not in spec:
                        continue

                    logger.info(f"[SCHEMA] Found OpenAPI spec at {url}")
                    entities.extend(self._parse_openapi_spec(spec, base_url))

                    # Register the schema itself as an entity
                    entities.append(ParsedEntity(
                        kind="api_schema",
                        label=url,
                        confidence=0.95,
                        source_tool="schema_discovery",
                        phase="api_reconnaissance",
                        scan_id=self.scan_id,
                        properties={
                            "schema_type": "openapi",
                            "version": spec.get("openapi", spec.get("swagger", "unknown")),
                            "title": spec.get("info", {}).get("title", ""),
                            "endpoints_count": len(spec.get("paths", {})),
                        }))
                    break  # Found one, no need to probe more for this base

            except Exception as exc:
                logger.debug(f"[SCHEMA] Probe {path} failed: {exc}")
                continue

        return entities

    async def discover_graphql(self, base_url: str) -> list[ParsedEntity]:
        """Probe GraphQL endpoints and attempt introspection."""
        entities: list[ParsedEntity] = []
        if not self._http:
            return entities

        for path in GRAPHQL_PATHS:
            try:
                url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))

                # Try introspection
                resp = await self._http.post(url,
                    json={"query": GRAPHQL_INTROSPECTION_QUERY},
                    headers={"Content-Type": "application/json"},
                    timeout=10)

                if resp.status_code != 200:
                    continue

                body = resp.json()
                if "data" not in body or "__schema" not in body.get("data", {}):
                    continue

                logger.info(f"[SCHEMA] GraphQL introspection successful at {url}")
                schema = body["data"]["__schema"]

                # Extract types and fields
                types = schema.get("types", [])
                query_type = (schema.get("queryType") or {}).get("name", "Query")
                mutation_type = (schema.get("mutationType") or {}).get("name", "")

                user_types = [t for t in types
                              if t.get("name", "").startswith("__") is False
                              and t.get("kind") in ("OBJECT", "INPUT_OBJECT")]

                entities.append(ParsedEntity(
                    kind="graphql_endpoint",
                    label=url,
                    confidence=0.95,
                    source_tool="schema_discovery",
                    phase="api_reconnaissance",
                    scan_id=self.scan_id,
                    properties={
                        "introspection_enabled": True,
                        "query_type": query_type,
                        "mutation_type": mutation_type,
                        "type_count": len(user_types),
                        "total_types": len(types),
                    }))

                # Extract query/mutation fields as endpoints
                for t in types:
                    if t.get("name") in (query_type, mutation_type):
                        for field in (t.get("fields") or []):
                            fname = field.get("name", "")
                            args = [a.get("name", "") for a in field.get("args", [])]
                            entities.append(ParsedEntity(
                                kind="graphql_operation",
                                label=f"{t['name']}.{fname}",
                                confidence=0.9,
                                source_tool="schema_discovery",
                                phase="api_reconnaissance",
                                scan_id=self.scan_id,
                                properties={
                                    "operation_type": "query" if t["name"] == query_type else "mutation",
                                    "field_name": fname,
                                    "arguments": args,
                                    "return_type": (field.get("type") or {}).get("name", ""),
                                    "graphql_url": url,
                                }))

                # Only need one successful introspection per base URL
                break

            except Exception as exc:
                logger.debug(f"[SCHEMA] GraphQL probe {path} failed: {exc}")
                continue

        return entities

    def _parse_openapi_spec(self, spec: dict, base_url: str) -> list[ParsedEntity]:
        """Parse an OpenAPI spec into individual endpoint entities."""
        entities: list[ParsedEntity] = []
        paths = spec.get("paths", {})
        servers = spec.get("servers", [{"url": base_url}])
        server_base = servers[0].get("url", base_url) if servers else base_url

        # Resolve relative server URLs
        if server_base.startswith("/"):
            server_base = urljoin(base_url, server_base)

        for path, methods in paths.items():
            if not isinstance(methods, dict):
                continue
            for method, details in methods.items():
                if method.lower() in ("parameters", "summary", "description", "$ref"):
                    continue
                if not isinstance(details, dict):
                    continue

                full_url = urljoin(server_base.rstrip("/") + "/", path.lstrip("/"))
                params = []
                for param in details.get("parameters", []):
                    params.append({
                        "name": param.get("name", ""),
                        "in": param.get("in", "query"),
                        "required": param.get("required", False),
                        "type": (param.get("schema") or {}).get("type", "string"),
                    })

                # Check request body
                req_body = details.get("requestBody", {})
                content_types = list((req_body.get("content") or {}).keys())

                # Auth requirements
                security = details.get("security", spec.get("security", []))
                auth_required = bool(security)

                # Tags
                tags = details.get("tags", [])

                entities.append(ParsedEntity(
                    kind="api_endpoint",
                    label=f"{method.upper()} {full_url}",
                    confidence=0.95,
                    source_tool="schema_discovery",
                    phase="api_reconnaissance",
                    scan_id=self.scan_id,
                    properties={
                        "method": method.upper(),
                        "url": full_url,
                        "path": path,
                        "summary": details.get("summary", ""),
                        "description": (details.get("description") or "")[:500],
                        "parameters": params,
                        "content_types": content_types,
                        "auth_required": auth_required,
                        "tags": tags,
                        "operation_id": details.get("operationId", ""),
                        "deprecated": details.get("deprecated", False),
                    }))

        return entities


class PostmanParser:
    """Parse Postman collection files."""

    def parse(self, collection_path: Path, scan_id: str) -> list[ParsedEntity]:
        if not collection_path.exists():
            return []
        try:
            data = json.loads(collection_path.read_text(encoding="utf-8"))
        except Exception:
            return []

        entities: list[ParsedEntity] = []
        items = data.get("item", [])
        self._flatten_items(items, entities, scan_id)
        return entities

    def _flatten_items(self, items: list, entities: list, scan_id: str,
                        prefix: str = ""):
        for item in items:
            if "item" in item:
                # Folder
                folder_name = item.get("name", "")
                self._flatten_items(item["item"], entities, scan_id,
                                     prefix=f"{prefix}/{folder_name}")
            elif "request" in item:
                req = item["request"]
                method = req.get("method", "GET") if isinstance(req, dict) else "GET"
                url = ""
                if isinstance(req, dict):
                    url_obj = req.get("url", {})
                    if isinstance(url_obj, str):
                        url = url_obj
                    elif isinstance(url_obj, dict):
                        url = url_obj.get("raw", "")

                entities.append(ParsedEntity(
                    kind="api_endpoint",
                    label=f"{method} {url}",
                    confidence=0.8,
                    source_tool="postman_collection",
                    phase="api_reconnaissance",
                    scan_id=scan_id,
                    properties={
                        "method": method,
                        "url": url,
                        "name": item.get("name", ""),
                        "folder": prefix,
                        "source": "postman",
                    }))
