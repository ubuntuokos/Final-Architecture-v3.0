from __future__ import annotations

import unittest

from fa3_system_one_mcp_compiler import compile_mcp_tools


class SystemOneMcpCompilerTests(unittest.TestCase):
    def test_compiles_finite_tools_and_maps_risk_annotations(self):
        result = compile_mcp_tools([
            {
                "name": "read_record",
                "description": "Read one record",
                "annotations": {"readOnlyHint": True},
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "record": {
                            "type": "string",
                            "x-fa3-candidate-source": "visible_records",
                        },
                        "summary": {"type": "boolean", "default": False},
                    },
                    "required": ["record"],
                },
            },
            {
                "name": "delete_record",
                "annotations": {"destructiveHint": True},
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "record": {"type": "string", "enum": ["r1", "r2"]}
                    },
                    "required": ["record"],
                },
            },
        ])
        data = result.to_dict()
        self.assertFalse(data["authority"])
        self.assertFalse(data["execution_performed"])
        self.assertEqual(data["final_policy_owner"], "FA3-AUTH-MCP-GATEWAY-001")
        by_id = {row["id"]: row for row in data["action_candidates"]}
        self.assertEqual(by_id["read_record"]["metadata"]["risk"], "read")
        self.assertEqual(by_id["delete_record"]["metadata"]["risk"], "destructive")
        self.assertEqual(
            by_id["read_record"]["metadata"]["parameters"]["record"]["kind"],
            "candidates",
        )
        self.assertEqual(
            by_id["read_record"]["metadata"]["parameters"]["summary"]["kind"],
            "flag",
        )
        self.assertEqual(data["unsupported"], {})

    def test_free_text_tool_is_reported_not_silently_dropped(self):
        data = compile_mcp_tools([
            {
                "name": "search",
                "inputSchema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            }
        ]).to_dict()
        self.assertEqual(data["action_candidates"], [])
        self.assertEqual(
            data["unsupported"]["search"]["reason_code"],
            "MCP_PARAMETER_NOT_FINITE",
        )

    def test_reserved_tool_name_is_rejected(self):
        data = compile_mcp_tools([
            {
                "name": "next_action",
                "inputSchema": {"type": "object", "properties": {}},
            }
        ]).to_dict()
        self.assertEqual(
            data["unsupported"]["next_action"]["reason_code"],
            "MCP_TOOL_NAME_RESERVED",
        )


if __name__ == "__main__":
    unittest.main()
