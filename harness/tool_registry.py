"""Tool registry for registering, discovering, and executing typed agent tools."""

import inspect
import json
import traceback
from dataclasses import dataclass
from typing import Callable, Dict, Any, List, Optional
from harness.evidence_store import EvidenceItem


class ToolError(Exception):
    """Raised when a tool encounters an unrecoverable runtime error."""
    pass


@dataclass
class ToolDefinition:
    name: str
    description: str
    func: Callable
    parameters: Dict[str, Any]


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, name: str, description: str):
        """Decorator to register a tool in the registry."""
        def decorator(func: Callable):
            sig = inspect.signature(func)
            params = {}
            for param_name, param in sig.parameters.items():
                if param_name in ("self", "args", "kwargs"):
                    continue
                annotation = param.annotation
                annotation_str = getattr(annotation, "__name__", str(annotation))
                default = None if param.default is inspect.Parameter.empty else param.default
                params[param_name] = {
                    "type": annotation_str,
                    "default": default,
                    "required": param.default is inspect.Parameter.empty
                }

            self._tools[name] = ToolDefinition(
                name=name,
                description=description,
                func=func,
                parameters=params
            )
            return func
        return decorator

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters
            }
            for t in self._tools.values()
        ]

    def render_descriptions(self) -> str:
        """Render markdown-formatted tool descriptions for the plan prompt."""
        lines = []
        for t in self._tools.values():
            param_list = []
            for p_name, p_info in t.parameters.items():
                req = "required" if p_info["required"] else f"optional, default={p_info['default']}"
                param_list.append(f"{p_name}: {p_info['type']} ({req})")
            params_str = ", ".join(param_list) if param_list else "none"
            lines.append(f"- `{t.name}({params_str})`: {t.description}")
        return "\n".join(lines)

    def execute(self, name: str, args: Dict[str, Any]) -> List[EvidenceItem]:
        """Execute tool by name and return list of EvidenceItems. Raises ToolError on failure."""
        tool_def = self.get(name)
        if not tool_def:
            raise ToolError(f"Tool '{name}' is not registered in ToolRegistry.")

        try:
            result = tool_def.func(**args)
            if isinstance(result, list):
                # Verify they are EvidenceItems or convert
                items = []
                for item in result:
                    if isinstance(item, EvidenceItem):
                        items.append(item)
                    else:
                        items.append(EvidenceItem(
                            id=f"{name}-{hash(str(item)) & 0xFFFFFF:06x}",
                            source="tool",
                            origin={"tool": name},
                            content=json.dumps(item) if isinstance(item, (dict, list)) else str(item),
                            relevance=1.0
                        ))
                return items
            elif isinstance(result, EvidenceItem):
                return [result]
            else:
                return [EvidenceItem(
                    id=f"{name}-{hash(str(result)) & 0xFFFFFF:06x}",
                    source="tool",
                    origin={"tool": name},
                    content=json.dumps(result) if isinstance(result, (dict, list)) else str(result),
                    relevance=1.0
                )]
        except Exception as e:
            if isinstance(e, ToolError):
                raise
            trace = traceback.format_exc()
            raise ToolError(f"Tool execution failed for '{name}': {e}\n{trace}") from e


registry = ToolRegistry()
register_tool = registry.register
