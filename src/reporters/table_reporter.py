"""
Table reporter for generating platform and ad-type comparison tables.
Displays iOS & Android data with ad type breakdown in a clear tabular format.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime


class TableReporter:
    """
    Generates formatted tables for network data comparison.
    Shows iOS & Android platforms with ad type breakdown.
    """
    
    # Column widths for formatting
    LABEL_WIDTH = 14
    VALUE_WIDTH = 22
    
    # Ad type display order
    AD_TYPE_ORDER = ['banner', 'interstitial', 'rewarded']
    
    # Platform display order
    PLATFORM_ORDER = ['android', 'ios']
    
    def __init__(self):
        """Initialize table reporter."""
        pass
    
    def generate_platform_ad_table(
        self, 
        network_data: List[Dict[str, Any]], 
        show_diff: bool = True
    ) -> str:
        """
        Generate a comprehensive table showing platform and ad type data for all networks.
        
        Args:
            network_data: List of network data dictionaries
            show_diff: Whether to show difference percentages
            
        Returns:
            Formatted table string
        """
        if not network_data:
            return "No data available."
        
        output_lines = []
        
        # Get date range from first network
        date_range = network_data[0].get('date_range', {})
        start_date = date_range.get('start', 'N/A')
        end_date = date_range.get('end', 'N/A')
        
        # Header
        output_lines.append("=" * 100)
        output_lines.append(f"📊 NETWORK DATA COMPARISON REPORT")
        output_lines.append(f"📅 Date Range: {start_date} to {end_date}")
        output_lines.append(f"🕐 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output_lines.append("=" * 100)
        output_lines.append("")
        
        # Get network names
        network_names = [nd.get('network', 'Unknown') for nd in network_data]
        
        # Generate table for each platform
        for platform in self.PLATFORM_ORDER:
            output_lines.append(self._generate_platform_section(
                platform, network_data, network_names, show_diff
            ))
            output_lines.append("")
        
        # Overall totals comparison
        output_lines.append(self._generate_totals_section(network_data, network_names))
        
        return "\n".join(output_lines)
    
    def _generate_platform_section(
        self, 
        platform: str, 
        network_data: List[Dict[str, Any]], 
        network_names: List[str],
        show_diff: bool
    ) -> str:
        """
        Generate table section for a specific platform.
        
        Args:
            platform: Platform name (android/ios)
            network_data: List of network data
            network_names: List of network names
            show_diff: Whether to show differences
            
        Returns:
            Formatted platform section string
        """
        lines = []
        platform_icon = "🤖" if platform == "android" else "🍎"
        
        lines.append(f"{platform_icon} {platform.upper()} Platform")
        lines.append("-" * 100)
        
        # Build header row with network columns
        header = f"{'Ad Type':<{self.LABEL_WIDTH}}"
        for name in network_names:
            # Each network gets: Revenue | eCPM | Impressions
            header += f" | {name:^{self.VALUE_WIDTH * 3 + 4}}"
        lines.append(header)
        
        # Sub-header for metrics
        sub_header = " " * self.LABEL_WIDTH
        for _ in network_names:
            sub_header += f" | {'Revenue':>{self.VALUE_WIDTH}}{'eCPM':>{self.VALUE_WIDTH}}{'Impressions':>{self.VALUE_WIDTH}}"
        lines.append(sub_header)
        lines.append("-" * 100)
        
        # Collect all ad types present
        all_ad_types = set()
        for nd in network_data:
            platform_info = nd.get('platform_data', {}).get(platform, {})
            all_ad_types.update(platform_info.get('ad_data', {}).keys())
        
        # Order ad types
        ordered_ad_types = [at for at in self.AD_TYPE_ORDER if at in all_ad_types]
        ordered_ad_types.extend([at for at in sorted(all_ad_types) if at not in self.AD_TYPE_ORDER])
        
        # Data rows for each ad type
        for ad_type in ordered_ad_types:
            row = f"{ad_type.capitalize():<{self.LABEL_WIDTH}}"
            
            baseline_data = None
            for idx, nd in enumerate(network_data):
                platform_info = nd.get('platform_data', {}).get(platform, {})
                ad_info = platform_info.get('ad_data', {}).get(ad_type, {
                    'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0
                })
                
                revenue = ad_info.get('revenue', 0.0)
                impressions = ad_info.get('impressions', 0)
                ecpm = ad_info.get('ecpm', 0.0)
                
                # Store baseline for diff calculation
                if idx == 0:
                    baseline_data = ad_info
                
                # Format values
                rev_str = f"${revenue:,.2f}"
                ecpm_str = f"${ecpm:.2f}"
                imp_str = f"{impressions:,}"
                
                # Add diff indicator if not baseline and show_diff is True
                if show_diff and idx > 0 and baseline_data:
                    diff_indicator = self._get_diff_indicator(
                        baseline_data.get('revenue', 0), revenue
                    )
                    rev_str = f"{rev_str} {diff_indicator}"
                
                row += f" | {rev_str:>{self.VALUE_WIDTH}}{ecpm_str:>{self.VALUE_WIDTH}}{imp_str:>{self.VALUE_WIDTH}}"
            
            lines.append(row)
        
        # Platform totals row
        lines.append("-" * 100)
        total_row = f"{'TOTAL':<{self.LABEL_WIDTH}}"
        
        baseline_platform = None
        for idx, nd in enumerate(network_data):
            platform_info = nd.get('platform_data', {}).get(platform, {
                'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0
            })
            
            revenue = platform_info.get('revenue', 0.0)
            impressions = platform_info.get('impressions', 0)
            ecpm = platform_info.get('ecpm', 0.0)
            
            if idx == 0:
                baseline_platform = platform_info
            
            rev_str = f"${revenue:,.2f}"
            ecpm_str = f"${ecpm:.2f}"
            imp_str = f"{impressions:,}"
            
            if show_diff and idx > 0 and baseline_platform:
                diff_indicator = self._get_diff_indicator(
                    baseline_platform.get('revenue', 0), revenue
                )
                rev_str = f"{rev_str} {diff_indicator}"
            
            total_row += f" | {rev_str:>{self.VALUE_WIDTH}}{ecpm_str:>{self.VALUE_WIDTH}}{imp_str:>{self.VALUE_WIDTH}}"
        
        lines.append(total_row)
        
        return "\n".join(lines)
    
    def _generate_totals_section(
        self, 
        network_data: List[Dict[str, Any]], 
        network_names: List[str]
    ) -> str:
        """
        Generate overall totals section.
        
        Args:
            network_data: List of network data
            network_names: List of network names
            
        Returns:
            Formatted totals section string
        """
        lines = []
        lines.append("📈 OVERALL TOTALS (All Platforms)")
        lines.append("=" * 100)
        
        # Header
        header = f"{'Network':<{self.LABEL_WIDTH + 5}}"
        header += f"{'Revenue':>{self.VALUE_WIDTH}}{'eCPM':>{self.VALUE_WIDTH}}{'Impressions':>{self.VALUE_WIDTH}}"
        lines.append(header)
        lines.append("-" * 100)
        
        baseline = None
        for idx, nd in enumerate(network_data):
            name = nd.get('network', 'Unknown')
            revenue = nd.get('revenue', 0.0)
            impressions = nd.get('impressions', 0)
            ecpm = nd.get('ecpm', 0.0)
            
            if idx == 0:
                baseline = nd
            
            rev_str = f"${revenue:,.2f}"
            ecpm_str = f"${ecpm:.2f}"
            imp_str = f"{impressions:,}"
            
            # Add diff for non-baseline
            if idx > 0 and baseline:
                diff_pct = self._calc_diff_percentage(baseline.get('revenue', 0), revenue)
                diff_str = f" ({diff_pct})"
                rev_str = f"{rev_str}{diff_str}"
            
            row = f"{name:<{self.LABEL_WIDTH + 5}}"
            row += f"{rev_str:>{self.VALUE_WIDTH}}{ecpm_str:>{self.VALUE_WIDTH}}{imp_str:>{self.VALUE_WIDTH}}"
            lines.append(row)
        
        return "\n".join(lines)
    
    def _get_diff_indicator(self, baseline: float, value: float) -> str:
        """
        Get a visual indicator for difference.
        
        Args:
            baseline: Baseline value
            value: Comparison value
            
        Returns:
            Indicator string (↑/↓/=)
        """
        if baseline == 0 and value == 0:
            return "="
        elif baseline == 0:
            return "↑∞"
        
        diff_pct = ((value - baseline) / baseline) * 100
        
        if abs(diff_pct) < 0.5:
            return "="
        elif diff_pct > 0:
            return f"↑{diff_pct:.1f}%"
        else:
            return f"↓{abs(diff_pct):.1f}%"
    
    def _calc_diff_percentage(self, baseline: float, value: float) -> str:
        """
        Calculate difference percentage string.
        
        Args:
            baseline: Baseline value
            value: Comparison value
            
        Returns:
            Formatted percentage string
        """
        if baseline == 0 and value == 0:
            return "0.0%"
        elif baseline == 0:
            return "∞%"
        
        diff_pct = ((value - baseline) / baseline) * 100
        sign = "+" if diff_pct > 0 else ""
        return f"{sign}{diff_pct:.1f}%"
    
    def generate_compact_table(
        self, 
        network_data: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a compact table showing key metrics per platform per network.
        Format: Platform | Network | Rewarded | Interstitial | Banner | Total
        
        Args:
            network_data: List of network data dictionaries
            
        Returns:
            Formatted compact table string
        """
        if not network_data:
            return "No data available."
        
        lines = []
        
        # Fixed column widths for alignment
        col_platform = 10
        col_network = 15
        col_ad = 18
        col_total = 18
        
        header = (
            f"{'Platform':<{col_platform}}| "
            f"{'Network':<{col_network}}| "
            f"{'Rewarded':>{col_ad}}| "
            f"{'Interstitial':>{col_ad}}| "
            f"{'Banner':>{col_ad}}| "
            f"{'Total':>{col_total}}"
        )
        
        separator = "-" * len(header)
        
        lines.append("=" * len(header))
        lines.append("📊 COMPACT PLATFORM & AD TYPE REPORT")
        lines.append("   Format: Revenue (eCPM)")
        lines.append("=" * len(header))
        lines.append(header)
        lines.append(separator)
        
        for platform in self.PLATFORM_ORDER:
            platform_icon = "🤖" if platform == "android" else "🍎"
            
            for idx, nd in enumerate(network_data):
                network_name = nd.get('network', 'Unknown')
                short_name = network_name[:13] if len(network_name) > 13 else network_name
                platform_info = nd.get('platform_data', {}).get(platform, {})
                
                # Get ad type data
                def get_ad_cell(ad_type: str) -> str:
                    ad_info = platform_info.get('ad_data', {}).get(ad_type, {})
                    rev = ad_info.get('revenue', 0.0)
                    ecpm = ad_info.get('ecpm', 0.0)
                    return f"${rev:,.0f} (${ecpm:.2f})"
                
                # Platform total
                total_rev = platform_info.get('revenue', 0.0)
                total_ecpm = platform_info.get('ecpm', 0.0)
                total_cell = f"${total_rev:,.0f} (${total_ecpm:.2f})"
                
                # Build row
                plat_display = f"{platform_icon} {platform.upper()}" if idx == 0 else ""
                row = (
                    f"{plat_display:<{col_platform}}| "
                    f"{short_name:<{col_network}}| "
                    f"{get_ad_cell('rewarded'):>{col_ad}}| "
                    f"{get_ad_cell('interstitial'):>{col_ad}}| "
                    f"{get_ad_cell('banner'):>{col_ad}}| "
                    f"{total_cell:>{col_total}}"
                )
                lines.append(row)
            
            # Add separator between platforms
            if platform != self.PLATFORM_ORDER[-1]:
                lines.append(separator)
        
        lines.append(separator)
        
        return "\n".join(lines)
    
    def generate_diff_summary(
        self, 
        comparisons: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a summary of discrepancies between networks.
        
        Args:
            comparisons: List of comparison results from DataValidator
            
        Returns:
            Formatted summary string
        """
        if not comparisons:
            return "No comparisons available."
        
        lines = []
        lines.append("=" * 80)
        lines.append("⚠️  DISCREPANCY SUMMARY")
        lines.append("=" * 80)
        
        has_any_discrepancy = False
        
        for comp in comparisons:
            network1 = comp.get('network1', 'Unknown')
            network2 = comp.get('network2', 'Unknown')
            
            if comp.get('has_discrepancy'):
                has_any_discrepancy = True
                lines.append(f"\n🔍 {network1} vs {network2}")
                lines.append("-" * 40)
                
                # Overall metric discrepancies
                for disc in comp.get('discrepancies', []):
                    if disc.get('over_threshold'):
                        metric = disc['metric'].upper()
                        v1 = disc['network1_value']
                        v2 = disc['network2_value']
                        pct = disc['difference_percentage']
                        pct_str = "∞" if pct == float('inf') else f"{pct:.1f}%"
                        
                        if metric == 'REVENUE':
                            lines.append(f"  💰 {metric}: ${v1:,.2f} → ${v2:,.2f} ({pct_str} diff)")
                        elif metric == 'ECPM':
                            lines.append(f"  📊 {metric}: ${v1:.2f} → ${v2:.2f} ({pct_str} diff)")
                        else:
                            lines.append(f"  📈 {metric}: {v1:,} → {v2:,} ({pct_str} diff)")
                
                # Platform-level discrepancies
                plat_comp = comp.get('platform_comparison', {})
                if plat_comp.get('has_discrepancy'):
                    for plat, plat_info in plat_comp.get('platforms', {}).items():
                        plat_icon = "🤖" if plat == "android" else "🍎"
                        
                        for ad_type, ad_info in plat_info.get('ad_types', {}).items():
                            if ad_info.get('revenue_over_threshold'):
                                pct = ad_info['revenue_diff_pct']
                                pct_str = "∞" if pct == float('inf') else f"{pct:.1f}%"
                                n1 = ad_info['network1']
                                n2 = ad_info['network2']
                                lines.append(
                                    f"  {plat_icon} {plat.upper()} - {ad_type.capitalize()}: "
                                    f"${n1.get('revenue', 0):,.2f} → ${n2.get('revenue', 0):,.2f} ({pct_str})"
                                )
        
        if not has_any_discrepancy:
            lines.append("\n✅ No discrepancies found. All networks are aligned!")
        
        return "\n".join(lines)


def print_network_table(network_data: List[Dict[str, Any]], compact: bool = False):
    """
    Utility function to print network data table.
    
    Args:
        network_data: List of network data dictionaries
        compact: If True, use compact format
    """
    reporter = TableReporter()
    
    if compact:
        print(reporter.generate_compact_table(network_data))
    else:
        print(reporter.generate_platform_ad_table(network_data))


def print_comparison_summary(comparisons: List[Dict[str, Any]]):
    """
    Utility function to print comparison summary.
    
    Args:
        comparisons: List of comparison results
    """
    reporter = TableReporter()
    print(reporter.generate_diff_summary(comparisons))

