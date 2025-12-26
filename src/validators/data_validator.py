"""
Data validator for comparing network metrics.
"""
from typing import Dict, List, Any, Tuple


class DataValidator:
    """Validator for comparing network data and detecting discrepancies."""
    
    def __init__(self, threshold_percentage: float = 5.0):
        """
        Initialize validator.
        
        Args:
            threshold_percentage: Maximum allowed difference percentage (e.g., 5 means 5%)
        """
        self.threshold_percentage = threshold_percentage
    
    def compare_metrics(
        self, 
        data1: Dict[str, Any], 
        data2: Dict[str, Any],
        metrics: List[str] = ['revenue', 'impressions']
    ) -> Dict[str, Any]:
        """
        Compare metrics between two network data sets.
        
        Args:
            data1: First network data
            data2: Second network data
            metrics: List of metrics to compare
            
        Returns:
            Dictionary containing comparison results
        """
        results = {
            'network1': data1['network'],
            'network2': data2['network'],
            'date_range': data1['date_range'],
            'has_discrepancy': False,
            'discrepancies': []
        }
        
        for metric in metrics:
            value1 = data1.get(metric, 0)
            value2 = data2.get(metric, 0)
            
            # Calculate percentage difference
            if value1 == 0 and value2 == 0:
                diff_percentage = 0.0
            elif value1 == 0:
                # When baseline is 0, any non-zero value is considered a large discrepancy
                diff_percentage = float('inf') if value2 != 0 else 0.0
            else:
                diff_percentage = abs((value2 - value1) / value1) * 100
            
            # Check threshold (treat infinity as exceeding threshold)
            is_over_threshold = (diff_percentage != 0.0 and 
                                (diff_percentage == float('inf') or 
                                 diff_percentage > self.threshold_percentage))
            
            if is_over_threshold:
                results['has_discrepancy'] = True
            
            results['discrepancies'].append({
                'metric': metric,
                'network1_value': value1,
                'network2_value': value2,
                'difference': value2 - value1,
                'difference_percentage': diff_percentage if diff_percentage != float('inf') else float('inf'),
                'over_threshold': is_over_threshold
            })
        
        return results
    
    def compare_multiple_networks(
        self,
        network_data: List[Dict[str, Any]],
        metrics: List[str] = ['revenue', 'impressions']
    ) -> List[Dict[str, Any]]:
        """
        Compare metrics across multiple networks.
        
        Args:
            network_data: List of network data dictionaries
            metrics: List of metrics to compare
            
        Returns:
            List of comparison results for each network pair
        """
        if len(network_data) < 2:
            raise ValueError("Need at least 2 networks to compare")
        
        comparisons = []
        
        # Compare each network with the first one (baseline)
        baseline = network_data[0]
        for i in range(1, len(network_data)):
            comparison = self.compare_metrics(baseline, network_data[i], metrics)
            comparisons.append(comparison)
        
        return comparisons
    
    def has_any_discrepancy(self, comparisons: List[Dict[str, Any]]) -> bool:
        """
        Check if any comparison has discrepancies.
        
        Args:
            comparisons: List of comparison results
            
        Returns:
            True if any discrepancy found, False otherwise
        """
        return any(comp['has_discrepancy'] for comp in comparisons)
