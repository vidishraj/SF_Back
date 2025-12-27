from typing import List, Dict, Any
from analysis_strategies import TicketAnalysisStrategy, KeywordAnalysisStrategy, LLMAnalysisStrategy


class TicketAnalyzer:
    """
    Main ticket analyzer class that uses different strategies for analysis.
    
    This class implements the Strategy pattern, allowing us to switch between
    different analysis methods (keyword-based, LLM-based) based on requirements.
    
    Design decisions:
    1. Strategy pattern allows easy extension with new analysis methods
    2. Single responsibility - this class only handles strategy selection
    3. The actual analysis logic is delegated to strategy implementations
    
    Trade-offs considered:
    - Pro: Easy to add new analysis methods without changing existing code
    - Pro: Can switch analysis methods at runtime based on parameters
    - Pro: Each strategy can be tested independently
    - Con: Slight overhead from additional abstraction layer
    """
    
    def __init__(self):
        """Initialize the analyzer with available strategies."""
        # Registry of available analysis strategies
        # This allows us to easily add new strategies in the future
        self._strategies = {
            'keyword': KeywordAnalysisStrategy(),
            'llm': LLMAnalysisStrategy(),
        }
        
        # Default strategy if none specified
        self._default_strategy = 'keyword'
    
    def analyze(self, tickets: List[Dict[str, Any]], method: str = None) -> str:
        """
        Analyze tickets using the specified method.
        
        Args:
            tickets: List of ticket dictionaries to analyze
            method: Analysis method to use ('keyword', 'llm', etc.)
                   If None, uses default strategy
        
        Returns:
            str: Formatted summary report
            
        Raises:
            ValueError: If the specified method is not available
            
        This method acts as a facade, hiding the complexity of strategy
        selection and validation from the caller.
        """
        # Input validation
        if not tickets:
            return "No tickets provided for analysis."
        
        if not isinstance(tickets, list):
            raise ValueError("Tickets must be provided as a list")
        
        # Validate ticket structure
        for i, ticket in enumerate(tickets):
            if not isinstance(ticket, dict):
                raise ValueError(f"Ticket at index {i} must be a dictionary")
            
            # Check required fields
            required_fields = ['id', 'status', 'priority']
            missing_fields = [field for field in required_fields if field not in ticket]
            if missing_fields:
                raise ValueError(f"Ticket {ticket.get('id', i)} missing required fields: {missing_fields}")
        
        # Select strategy
        strategy = self._select_strategy(method)
        
        # Perform analysis
        try:
            return strategy.analyze_tickets(tickets)
        except Exception as e:
            # Log the error in a real application
            error_msg = f"Analysis failed with method '{method or self._default_strategy}': {str(e)}"
            return f"Error during analysis: {error_msg}"
    
    def _select_strategy(self, method: str = None) -> TicketAnalysisStrategy:
        """
        Select the appropriate analysis strategy.
        
        Args:
            method: Requested analysis method
            
        Returns:
            TicketAnalysisStrategy: The selected strategy instance
            
        Raises:
            ValueError: If the requested method is not available
        """
        if method is None:
            method = self._default_strategy
        
        method = method.lower().strip()
        
        if method not in self._strategies:
            available_methods = list(self._strategies.keys())
            raise ValueError(f"Analysis method '{method}' not available. "
                           f"Available methods: {available_methods}")
        
        return self._strategies[method]
    
    def get_available_methods(self) -> List[str]:
        """
        Get list of available analysis methods.
        
        Returns:
            List[str]: List of method names
        """
        return list(self._strategies.keys())
    
    def add_strategy(self, name: str, strategy: TicketAnalysisStrategy) -> None:
        """
        Add a new analysis strategy.
        
        Args:
            name: Name for the strategy
            strategy: Strategy instance
            
        This method allows for runtime addition of new strategies,
        useful for plugins or experimental analysis methods.
        """
        if not isinstance(strategy, TicketAnalysisStrategy):
            raise ValueError("Strategy must implement TicketAnalysisStrategy interface")
        
        self._strategies[name.lower().strip()] = strategy


# Global analyzer instance
# Using a singleton pattern here for simplicity, but could be dependency-injected
# in a larger application for better testability
analyzer = TicketAnalyzer()