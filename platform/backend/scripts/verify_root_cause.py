"""Ad-hoc end-to-end verification for the causal_graphrag pipeline."""

import asyncio
import json

from app.core.database import async_session_maker
from app.services.causal_graphrag.neo4j_client import Neo4jClient
from app.services.causal_graphrag.root_cause_service import RootCauseService


async def main():
    client = Neo4jClient()
    connected = await client.verify_connectivity()
    print("neo4j_connected:", connected)

    service = RootCauseService(client, llm_client=None)

    async with async_session_maker() as db:
        build = await service.build_graph(db, days=90)
        print("BUILD:", json.dumps(build, default=str))

        for rid in ["rc-demo-regression-039", "rc-demo-flaky-035", "rc-demo-env-039"]:
            res = await service.analyze_run(db, rid)
            causal = res.get("causal", {})
            primary = causal.get("primary") or {}
            print(
                f"\n=== {rid} ===\n"
                f"verdict={res.get('verdict')} "
                f"effect={primary.get('effect')} p={primary.get('p_value')} "
                f"engine={primary.get('engine')}\n"
                f"community={(res.get('community') or {}).get('label')} "
                f"nodes={len(res.get('subgraph', {}).get('nodes', []))} "
                f"selectors={res.get('top_selectors')}\n"
                f"summary={res.get('summary')}"
            )

        glob = await service.analyze_global(db, days=90)
        print("\n=== GLOBAL ===")
        print("community_count:", glob.get("community_count"))
        for c in glob.get("communities", []):
            print(f"  #{c.get('id')} {c.get('label')} failures={c.get('failure_count')} categories={c.get('categories')}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
