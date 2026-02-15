"""Tool management endpoints for adding tools dynamically."""

from typing import Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.core.logging import get_logger
from src.skills.base import ToolSchema, ToolParameter, ToolDangerLevel
from src.skills.registry import get_tool_registry

logger = get_logger(__name__)
router = APIRouter()


class ToolParameterInput(BaseModel):
    """Input for tool parameter definition."""
    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type (string, integer, number, boolean)")
    description: str = Field(..., description="Parameter description")
    required: bool = Field(default=True, description="Whether parameter is required")
    default: Any = Field(default=None, description="Default value if optional")


class CreateToolRequest(BaseModel):
    """Request to create a new tool."""
    tool_id: str = Field(..., description="Unique tool identifier (e.g., 'custom.search')")
    name: str = Field(..., description="Human-readable tool name")
    description: str = Field(..., description="Tool description")
    danger_level: str = Field(default="safe", description="Tool danger level: safe, normal, or destructive")
    parameters: list[ToolParameterInput] = Field(default_factory=list, description="Tool parameters")
    code: str = Field(..., description="Python code for the tool implementation")


class ToolInstructionsResponse(BaseModel):
    """Response with instructions for adding tools."""
    can_add_dynamically: bool = True
    instructions: str
    file_structure: dict[str, str]
    example_code: str


@router.get("/tools/instructions", response_model=ToolInstructionsResponse)
async def get_tool_instructions() -> ToolInstructionsResponse:
    """Get instructions for adding new tools.
    
    Returns:
        Detailed instructions for manual and dynamic tool addition.
    """
    instructions = """
There are two ways to add tools to OMNI:

**Method 1: Dynamic Addition (No Restart Required)**
Use the POST /api/v1/tools endpoint to add a tool dynamically.
The tool will be available immediately without server restart.

**Method 2: Manual Addition (Requires Restart)**
1. Create a new Python file in: backend/src/skills/library/
2. Implement your tool class extending BaseTool
3. Register the tool in backend/src/api/app.py
4. Restart the server

File Structure:
- backend/src/skills/library/ - Tool implementations
- backend/src/skills/base.py - BaseTool class
- backend/src/api/app.py - Tool registration

After adding a tool manually, you must restart the server with:
  ./start.sh

Or if using Docker:
  docker-compose restart backend
"""

    file_structure = {
        "Tool Location": "backend/src/skills/library/your_tool.py",
        "Base Class": "backend/src/skills/base.py",
        "Registration": "backend/src/api/app.py (initialize_registries function)",
        "Config": "CONFIG/tools/your_tool.yaml (optional)"
    }

    example_code = '''"""Example tool implementation."""

from src.skills.base import BaseTool, ToolSchema, ToolParameter, ToolResult, ToolDangerLevel
from src.core.logging import get_logger

logger = get_logger(__name__)


class MyCustomTool(BaseTool):
    """Description of what your tool does."""
    
    def __init__(self):
        super().__init__(
            tool_id="custom.my_tool",
            name="My Custom Tool",
            description="What this tool does",
            danger_level=ToolDangerLevel.SAFE,
            timeout_seconds=30
        )
    
    async def execute(self, param1: str, param2: int = 10) -> ToolResult:
        """Execute the tool.
        
        Args:
            param1: Description of param1
            param2: Description of param2
            
        Returns:
            Tool execution result.
        """
        logger.info("Executing my custom tool", param1=param1)
        
        try:
            # Your tool logic here
            result = f"Processed {param1} with value {param2}"
            
            return ToolResult(
                success=True,
                result=result,
                metadata={"param1": param1, "param2": param2}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e)
            )
    
    def get_schema(self) -> ToolSchema:
        """Get tool schema."""
        return ToolSchema(
            name=self.name,
            description=self.description,
            danger_level=self.danger_level,
            parameters=[
                ToolParameter(
                    name="param1",
                    type="string",
                    description="Description of param1",
                    required=True
                ),
                ToolParameter(
                    name="param2",
                    type="integer",
                    description="Description of param2",
                    required=False,
                    default=10
                )
            ]
        )


# In backend/src/api/app.py, add to initialize_registries():
# tool_registry.register(MyCustomTool())
'''

    return ToolInstructionsResponse(
        can_add_dynamically=True,
        instructions=instructions,
        file_structure=file_structure,
        example_code=example_code
    )


@router.post("/tools")
async def create_tool(request: CreateToolRequest) -> dict[str, Any]:
    """Create a new tool dynamically.
    
    Args:
        request: Tool creation request with code and configuration.
        
    Returns:
        Created tool information.
        
    Note:
        This executes user-provided code. Use with caution in production.
        Consider implementing code validation/sandboxing.
    """
    try:
        # Validate danger level
        danger_level = ToolDangerLevel.SAFE
        if request.danger_level == "destructive":
            danger_level = ToolDangerLevel.DESTRUCTIVE
        elif request.danger_level == "normal":
            danger_level = ToolDangerLevel.NORMAL
        
        # Create dynamic tool class
        # WARNING: This executes arbitrary code - implement proper validation
        tool_class = create_dynamic_tool_class(
            tool_id=request.tool_id,
            name=request.name,
            description=request.description,
            danger_level=danger_level,
            parameters=request.parameters,
            code=request.code
        )
        
        # Instantiate and register
        tool = tool_class()
        registry = get_tool_registry()
        registry.register(tool)
        
        logger.info(
            "Tool created dynamically",
            tool_id=request.tool_id,
            name=request.name
        )
        
        return {
            "success": True,
            "tool_id": request.tool_id,
            "name": request.name,
            "message": f"Tool '{request.name}' created successfully and is now available."
        }
        
    except Exception as e:
        logger.error(
            "Failed to create tool",
            tool_id=request.tool_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tool: {str(e)}"
        )


def create_dynamic_tool_class(
    tool_id: str,
    name: str,
    description: str,
    danger_level: ToolDangerLevel,
    parameters: list[ToolParameterInput],
    code: str
):
    """Create a dynamic tool class from user-provided code.
    
    WARNING: This executes arbitrary code. Implement proper validation.
    
    Args:
        tool_id: Tool identifier.
        name: Tool name.
        description: Tool description.
        danger_level: Safety level.
        parameters: Tool parameters.
        code: Python code for execute method.
        
    Returns:
        Dynamic tool class.
    """
    from src.skills.base import BaseTool, ToolSchema, ToolParameter, ToolResult
    from src.core.logging import get_logger
    
    logger = get_logger(__name__)
    
    # Create the class dynamically
    # In production, implement proper code validation and sandboxing
    class_dict = {
        '__init__': lambda self: BaseTool.__init__(
            self,
            tool_id=tool_id,
            name=name,
            description=description,
            danger_level=danger_level,
            timeout_seconds=30
        ),
        'get_schema': lambda self: ToolSchema(
            name=name,
            description=description,
            danger_level=danger_level,
            parameters=[
                ToolParameter(
                    name=p.name,
                    type=p.type,
                    description=p.description,
                    required=p.required,
                    default=p.default
                )
                for p in parameters
            ]
        )
    }
    
    # Compile and add execute method
    # WARNING: This is potentially dangerous - exec() runs arbitrary code
    exec_globals = {
        'ToolResult': ToolResult,
        'logger': logger,
        'get_logger': get_logger,
    }
    exec_locals = {}
    
    # Wrap user code in execute method
    execute_code = f"""
async def execute(self, {', '.join([f"{p.name}=None" if not p.required else p.name for p in parameters])}):
{chr(10).join('    ' + line for line in code.split(chr(10)))}
"""
    
    exec(execute_code, exec_globals, exec_locals)
    class_dict['execute'] = exec_locals['execute']
    
    # Create the class
    DynamicTool = type(
        f"DynamicTool_{tool_id.replace('.', '_')}",
        (BaseTool,),
        class_dict
    )
    
    return DynamicTool