"""Calculator tool for mathematical operations."""

import math
from typing import Any

from src.skills.base import (
    BaseTool,
    ToolDangerLevel,
    ToolParameter,
    ToolResult,
    ToolSchema,
)
from src.core.logging import get_logger

logger = get_logger(__name__)


class CalculatorTool(BaseTool):
    """Tool for evaluating mathematical expressions.
    
    Provides safe evaluation of mathematical expressions
    with support for common math functions.
    """
    
    def __init__(self) -> None:
        """Initialize calculator tool."""
        super().__init__(
            tool_id="calculator.compute",
            name="Calculator",
            description="Evaluate mathematical expressions safely",
            danger_level=ToolDangerLevel.SAFE,
            timeout_seconds=5
        )
        
        # Safe math functions allowed in expressions
        self.safe_functions = {
            'abs': abs,
            'round': round,
            'max': max,
            'min': min,
            'sum': sum,
            'pow': pow,
            'sqrt': math.sqrt,
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'asin': math.asin,
            'acos': math.acos,
            'atan': math.atan,
            'sinh': math.sinh,
            'cosh': math.cosh,
            'tanh': math.tanh,
            'exp': math.exp,
            'log': math.log,
            'log10': math.log10,
            'log2': math.log2,
            'ceil': math.ceil,
            'floor': math.floor,
            'pi': math.pi,
            'e': math.e,
            'degrees': math.degrees,
            'radians': math.radians,
        }
    
    async def execute(self, expression: str) -> ToolResult:
        """Evaluate a mathematical expression.
        
        Args:
            expression: Mathematical expression to evaluate.
            
        Returns:
            Tool result with computed value.
        """
        logger.info(
            "Calculating expression",
            tool_id=self.tool_id,
            expression=expression[:100]
        )
        
        try:
            # Clean and validate expression
            cleaned = self._clean_expression(expression)
            
            # Evaluate safely
            result = eval(cleaned, {"__builtins__": {}}, self.safe_functions)
            
            # Format result
            if isinstance(result, float):
                # Round to avoid floating point weirdness
                result = round(result, 10)
                # Convert to int if it's a whole number
                if result == int(result):
                    result = int(result)
            
            return ToolResult(
                success=True,
                result=result,
                metadata={"expression": expression, "type": type(result).__name__}
            )
            
        except ZeroDivisionError:
            return ToolResult(
                success=False,
                error="Division by zero",
                metadata={"expression": expression}
            )
        except SyntaxError as e:
            return ToolResult(
                success=False,
                error=f"Invalid syntax: {e}",
                metadata={"expression": expression}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Calculation error: {e}",
                metadata={"expression": expression}
            )
    
    def _clean_expression(self, expression: str) -> str:
        """Clean and prepare expression for evaluation.
        
        Args:
            expression: Raw expression.
            
        Returns:
            Cleaned expression.
        """
        # Remove whitespace
        cleaned = expression.strip()
        
        # Basic sanitization - only allow safe characters
        allowed_chars = set('0123456789.+-*/()^% ')
        allowed_chars.update('abcdefghijklmnopqrstuvwxyz_')
        allowed_chars.update('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        
        # Check for dangerous characters
        for char in cleaned:
            if char not in allowed_chars:
                raise ValueError(f"Invalid character in expression: {char}")
        
        # Replace ^ with ** for exponentiation
        cleaned = cleaned.replace('^', '**')
        
        return cleaned
    
    def get_schema(self) -> ToolSchema:
        """Get tool schema."""
        return ToolSchema(
            name=self.name,
            description=self.description,
            danger_level=self.danger_level,
            parameters=[
                ToolParameter(
                    name="expression",
                    type="string",
                    description="Mathematical expression to evaluate (e.g., '2 + 2', 'sqrt(16)', 'sin(pi/2)')",
                    required=True
                )
            ]
        )
