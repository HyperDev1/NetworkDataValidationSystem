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
        metrics: List[str] = ['revenue', 'impressions', 'ecpm']
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
            'network1_data': data1,  # Include full data for ad_data access
            'network2_data': data2,  # Include full data for ad_data access
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
    
    def compare_platforms(self, baseline: Dict[str, Any], other: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare platform-level totals and ad-type breakdowns between baseline and other network.
        Returns a dictionary with platform discrepancies and ad-type details.
        """
        platforms = ['android', 'ios']
        result = {
            'network1': baseline['network'],
            'network2': other['network'],
            'platforms': {},
            'has_discrepancy': False
        }
        
        for plat in platforms:
            base_plat = baseline.get('platform_data', {}).get(plat, {'revenue':0,'impressions':0,'ecpm':0,'ad_data':{}})
            other_plat = other.get('platform_data', {}).get(plat, {'revenue':0,'impressions':0,'ecpm':0,'ad_data':{}})
            
            plat_comp = {
                'revenue': {
                    'network1_value': base_plat.get('revenue', 0),
                    'network2_value': other_plat.get('revenue', 0)
                },
                'impressions': {
                    'network1_value': base_plat.get('impressions', 0),
                    'network2_value': other_plat.get('impressions', 0)
                },
                'ecpm': {
                    'network1_value': base_plat.get('ecpm', 0),
                    'network2_value': other_plat.get('ecpm', 0)
                },
                'ad_types': {}
            }
            
            # Compare ad types
            ad_keys = set(list(base_plat.get('ad_data', {}).keys()) + list(other_plat.get('ad_data', {}).keys()))
            for ad_key in ad_keys:
                a1 = base_plat.get('ad_data', {}).get(ad_key, {'revenue':0,'impressions':0,'ecpm':0})
                a2 = other_plat.get('ad_data', {}).get(ad_key, {'revenue':0,'impressions':0,'ecpm':0})
                # compute diff percent for revenue
                base_rev = a1.get('revenue', 0)
                other_rev = a2.get('revenue', 0)
                if base_rev == 0 and other_rev == 0:
                    rev_pct = 0.0
                elif base_rev == 0:
                    rev_pct = float('inf')
                else:
                    rev_pct = abs((other_rev - base_rev)/base_rev) * 100
                over_rev = rev_pct != 0.0 and (rev_pct == float('inf') or rev_pct > self.threshold_percentage)
                
                plat_comp['ad_types'][ad_key] = {
                    'network1': a1,
                    'network2': a2,
                    'revenue_diff_pct': rev_pct,
                    'revenue_over_threshold': over_rev
                }
                if over_rev:
                    result['has_discrepancy'] = True
            
            result['platforms'][plat] = plat_comp
        
        return result
    
    def compare_multiple_networks(
        self,
        network_data: List[Dict[str, Any]],
        metrics: List[str] = ['revenue', 'impressions', 'ecpm'],
        baseline_name: str = 'Applovin Max'
    ) -> List[Dict[str, Any]]:
        """
        Compare metrics across multiple networks using a named baseline (default Applovin Max).
        Returns list of comparisons where each comparison contains both overall metric comparison and platform/ad-type breakdown.
        """
        if len(network_data) < 2:
            raise ValueError("Need at least 2 networks to compare")
        
        # find baseline by name
        baseline = None
        for nd in network_data:
            if nd.get('network') == baseline_name:
                baseline = nd
                break
        if baseline is None:
            # fallback to first
            baseline = network_data[0]
        
        comparisons = []
        for nd in network_data:
            if nd is baseline:
                continue
            overall = self.compare_metrics(baseline, nd, metrics)
            platform_comp = self.compare_platforms(baseline, nd)
            overall['platform_comparison'] = platform_comp
            comparisons.append(overall)
        
        return comparisons
    
    def has_any_discrepancy(self, comparisons: List[Dict[str, Any]]) -> bool:
        """
        Check if any comparison has discrepancies.
        """
        for comp in comparisons:
            if comp.get('has_discrepancy'):
                return True
            # also check platform comparison
            plat = comp.get('platform_comparison', {})
            if plat.get('has_discrepancy'):
                return True
        return False
