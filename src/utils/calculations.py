"""
Calculation utilities for Network Data Validation System.

Provides shared calculation functions used across multiple modules.
"""
from typing import Union


def calculate_ecpm(revenue: float, impressions: int) -> float:
    """
    Calculate eCPM (effective Cost Per Mille) from revenue and impressions.
    
    eCPM = (Revenue / Impressions) * 1000
    
    Args:
        revenue: Revenue in dollars
        impressions: Number of impressions
        
    Returns:
        eCPM value rounded to 2 decimal places, or 0.0 if impressions <= 0
    
    Example:
        >>> calculate_ecpm(100.0, 50000)
        2.0
        >>> calculate_ecpm(0.0, 1000)
        0.0
        >>> calculate_ecpm(100.0, 0)
        0.0
    """
    if impressions <= 0:
        return 0.0
    return round((revenue / impressions) * 1000, 2)


def parse_delta_percentage(delta_str: Union[str, float, int]) -> float:
    """
    Parse delta percentage string to float.
    
    Handles various formats:
    - "+10.5%" -> 10.5
    - "-5.2%" -> -5.2
    - "∞" -> float('inf')
    - "N/A" or empty -> 0.0
    
    Args:
        delta_str: Delta string like "+10.5%", "-5%", "∞", etc.
        
    Returns:
        Float value of the delta percentage
    
    Example:
        >>> parse_delta_percentage("+10.5%")
        10.5
        >>> parse_delta_percentage("-5.2%")
        -5.2
        >>> parse_delta_percentage("∞")
        inf
    """
    if delta_str is None:
        return 0.0
    
    # Already a number
    if isinstance(delta_str, (int, float)):
        return float(delta_str)
    
    delta_str = str(delta_str).strip().replace('%', '').replace('+', '')
    
    if not delta_str or delta_str in ('N/A', 'n/a', '-'):
        return 0.0
    
    # Handle infinity symbols
    if '∞' in delta_str or 'inf' in delta_str.lower():
        return float('inf') if not delta_str.startswith('-') else float('-inf')
    
    try:
        return float(delta_str)
    except ValueError:
        return 0.0


def calculate_delta(base_value: float, compare_value: float) -> float:
    """
    Calculate percentage delta between two values.
    
    Formula: ((compare - base) / base) * 100
    
    Args:
        base_value: The base/reference value
        compare_value: The value to compare against base
        
    Returns:
        Percentage difference, or 0.0 if base is 0
    
    Example:
        >>> calculate_delta(100.0, 110.0)
        10.0
        >>> calculate_delta(100.0, 90.0)
        -10.0
        >>> calculate_delta(0.0, 100.0)
        0.0
    """
    if base_value == 0:
        return 0.0
    return round(((compare_value - base_value) / base_value) * 100, 2)


def format_delta(delta: float, include_sign: bool = True) -> str:
    """
    Format delta percentage for display.
    
    Args:
        delta: Delta percentage value
        include_sign: Whether to include + sign for positive values
        
    Returns:
        Formatted string like "+10.5%" or "-5.2%"
    
    Example:
        >>> format_delta(10.5)
        '+10.5%'
        >>> format_delta(-5.2)
        '-5.2%'
        >>> format_delta(float('inf'))
        '∞'
    """
    if delta == float('inf'):
        return '∞'
    if delta == float('-inf'):
        return '-∞'
    
    if include_sign and delta > 0:
        return f"+{delta:.1f}%"
    return f"{delta:.1f}%"


def format_currency(value: float, symbol: str = '$') -> str:
    """
    Format a monetary value for display.
    
    Args:
        value: The monetary value
        symbol: Currency symbol (default: $)
        
    Returns:
        Formatted string like "$1,234.56"
    """
    return f"{symbol}{value:,.2f}"


def format_number(value: int) -> str:
    """
    Format a number with thousand separators.
    
    Args:
        value: The integer value
        
    Returns:
        Formatted string like "1,234,567"
    """
    return f"{value:,}"
