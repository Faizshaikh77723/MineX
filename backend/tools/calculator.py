# backend/tools/calculator.py

def calculate_percentage_growth(old_value: float, new_value: float) -> str:
    """Calculates the percentage increase or decrease between two years."""
    try:
        growth = ((new_value - old_value) / old_value) * 100
        direction = "increase" if growth > 0 else "decrease"
        return f"A {abs(growth):.2f}% {direction} from the previous period."
    except ZeroDivisionError:
        return "Error: Base value cannot be zero."

def calculate_share_percentage(part_value: float, total_value: float) -> str:
    """Calculates what percentage a specific entity contributes to the total."""
    try:
        share = (part_value / total_value) * 100
        return f"This represents {share:.2f}% of the total volume."
    except ZeroDivisionError:
        return "Error: Total value cannot be zero."

def execute_math_tool(operation: str, val1: float, val2: float) -> str:
    """Router for mathematical operations."""
    if operation == "growth":
        return calculate_percentage_growth(val1, val2)
    elif operation == "share":
        return calculate_share_percentage(val1, val2)
    return "Invalid mathematical operation."