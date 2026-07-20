from typing import List, Dict, Any, Tuple

class McNemarTest:
    """
    Implements McNemar's Test for paired nominal data.
    Useful for comparing if Prompt B is statistically significantly better than Prompt A
    on the exact same dataset of tasks.
    """
    
    @staticmethod
    def calculate(tasks_a: List[Dict[str, Any]], tasks_b: List[Dict[str, Any]]) -> Tuple[float, float, str]:
        """
        Expects two lists of tasks that are aligned (same tasks, same order).
        Returns (chi_squared, p_value, interpretation)
        """
        if len(tasks_a) != len(tasks_b):
            return 0.0, 1.0, "Mismatched dataset sizes"
            
        b = 0 # Passed in A, Failed in B
        c = 0 # Failed in A, Passed in B
        
        for ta, tb in zip(tasks_a, tasks_b):
            pass_a = ta.get("evaluation_status") == "PASS"
            pass_b = tb.get("evaluation_status") == "PASS"
            
            if pass_a and not pass_b:
                b += 1
            elif not pass_a and pass_b:
                c += 1
                
        # McNemar's chi-squared statistic with continuity correction
        if b + c == 0:
            return 0.0, 1.0, "No discordant pairs (identical performance)"
            
        chi_squared = ((abs(b - c) - 1) ** 2) / (b + c)
        
        # Approximate p-value for 1 degree of freedom chi-squared
        # To avoid scipy dependency, we use a rough threshold table or math approximation
        from scipy.stats import chi2
        
        try:
            p_value = chi2.sf(chi_squared, 1)
        except ImportError:
            # Fallback if scipy is somehow missing (it shouldn't be since we pip installed it)
            p_value = 1.0 # placeholder
            
        interpretation = "Not significant"
        if p_value < 0.05:
            interpretation = "Significant difference (p < 0.05)"
            
        return chi_squared, p_value, interpretation
