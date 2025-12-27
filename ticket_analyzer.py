"""
Ticket Analyzer - Strategy Pattern Coordinator

This module serves as the main entry point for ticket analysis. It coordinates between
different analysis strategies while providing a clean, simple interface to the rest
of the application.

DESIGN PHILOSOPHY: Composition over Inheritance
-----------------------------------------------
Rather than creating a complex inheritance hierarchy, I used composition with the Strategy
pattern. This makes the code more flexible and easier to test.

WHY THIS APPROACH?
1. The assessment requires multiple analysis methods
2. Future expansion is likely (more analysis types)
3. Testing is simpler when strategies are isolated
4. Runtime method switching provides better user experience
"""

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
        """
        Initialize the analyzer with available strategies.
        
        STRATEGY REGISTRY PATTERN
        ------------------------
        I use a dictionary to register strategies rather than hardcoded if/else statements.
        This makes adding new strategies as simple as adding one line to the registry.
        
        INITIALIZATION STRATEGY
        ----------------------
        I instantiate strategies at initialization rather than on-demand because:
        1. PERFORMANCE: Avoid repeated object creation
        2. EARLY ERROR DETECTION: If a strategy fails to initialize, we know immediately
        3. SIMPLICITY: No complex lazy loading logic needed
        
        TRADE-OFF: Uses slightly more memory, but provides better reliability and performance.
        
        DEFAULT STRATEGY CHOICE
        ----------------------
        I chose 'keyword' as default because:
        - Faster response time for first-time users
        - No external dependencies (works without API keys)
        - Good enough for basic analysis needs
        """
        # Registry of available analysis strategies
        # This allows us to easily add new strategies in the future
        self._strategies = {
            'keyword': KeywordAnalysisStrategy(),
            'llm': LLMAnalysisStrategy(),
        }
        
        # Default strategy if none specified - keyword is fast and always available
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
        # INPUT VALIDATION STRATEGY
        # I chose to validate here rather than in each strategy because:
        # 1. DRY PRINCIPLE: Avoid duplicating validation logic
        # 2. FAIL FAST: Catch data issues before expensive processing
        # 3. CONSISTENT ERRORS: All strategies return same error format
        
        if not tickets:
            return "No tickets provided for analysis."
        
        if not isinstance(tickets, list):
            raise ValueError("Tickets must be provided as a list")
        
        # Validate ticket structure - enforce the assessment's required format
        for i, ticket in enumerate(tickets):
            if not isinstance(ticket, dict):
                raise ValueError(f"Ticket at index {i} must be a dictionary")
            
            # Check required fields based on assessment specification
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


# GLOBAL INSTANCE DECISION
# -----------------------
# I created a global analyzer instance for this assessment because:
# 1. SIMPLICITY: Matches the pattern expected by the provided function signature
# 2. PERFORMANCE: Avoid recreating strategy objects on every request
# 3. STATELESS: The analyzer itself doesn't hold state between requests
# 
# ALTERNATIVE CONSIDERED: Dependency injection
# In a larger application, I'd inject this as a dependency for better testability,
# but for this scope, a global instance keeps things simple and clear.

analyzer = TicketAnalyzer()

"""
TICKET ANALYZER DESIGN DECISIONS AND TRADE-OFFS
================================================

Core Architecture Choice: Facade + Strategy Pattern
---------------------------------------------------
I implemented this class as a Facade that coordinates Strategy objects. This wasn't
the only option - here's what I considered:

OPTION 1: Single monolithic function with if/else logic
- Pros: Very simple, minimal code
- Cons: Hard to test, breaks single responsibility, difficult to extend
- Verdict: Too simplistic for assessment requirements

OPTION 2: Inheritance hierarchy (BaseAnalyzer -> KeywordAnalyzer, LLMAnalyzer)
- Pros: Object-oriented, polymorphism
- Cons: Tight coupling, harder to add strategies at runtime
- Verdict: More complex than needed, less flexible

OPTION 3: Strategy Pattern with Facade (chosen approach)
- Pros: Flexible, testable, extensible, clean interface
- Cons: Slightly more complex initially
- Verdict: Best balance of simplicity and flexibility for this scope

Validation Strategy
------------------
I chose to validate input data at the Facade level rather than in each strategy because:

CENTRALIZED VALIDATION BENEFITS:
1. DRY: No duplicate validation code in each strategy
2. Consistency: All strategies handle bad data the same way  
3. Performance: Fail fast before expensive processing
4. Maintainability: One place to update validation rules

TRADE-OFF: The strategies now assume clean data, which means they're less defensive.
In a microservices architecture, I might validate at both levels, but for this
monolithic structure, centralized validation is more appropriate.

Error Handling Philosophy
-------------------------
I implemented graceful error handling with informative messages rather than
silent failures or cryptic errors:

- INPUT ERRORS: Raise ValueError with specific details about what's wrong
- PROCESSING ERRORS: Return error message as string (matches return type)
- STRATEGY ERRORS: Delegate to strategy's own error handling

This approach prioritizes user experience - someone using the API gets clear
feedback about what went wrong and how to fix it.

Extensibility Design
--------------------
The add_strategy() method allows runtime addition of new analysis methods.
This supports future requirements like:
- A/B testing new algorithms
- Plugin architectures
- Customer-specific analysis methods
- Experimental features that might not be permanent

ASSUMPTION: Future expansion is likely based on assessment context, so I
optimized for extensibility over minimal code.

Memory vs. Performance Trade-offs
---------------------------------
I instantiate all strategies at startup rather than creating them on-demand:

TRADE-OFFS CONSIDERED:
- Memory: Uses more memory (all strategies loaded)
- Startup time: Slightly slower initialization
- Runtime performance: Faster (no object creation during requests)
- Error detection: Fail fast if strategy initialization fails

For a web application serving multiple requests, I prioritized runtime performance
over memory usage. This is especially important for the LLM strategy which might
have significant initialization costs.

Limitations and Future Improvements
-----------------------------------
CURRENT LIMITATIONS:
1. No strategy configuration (strategies are hardcoded)
2. No async support (could be important for LLM calls)
3. No caching (could help with repeated analysis requests)
4. No metrics/monitoring (important for production debugging)

DESIGN CHOICES THAT ENABLE FUTURE IMPROVEMENTS:
- Strategy pattern makes adding async strategies easy
- Registry pattern supports configuration-driven strategy loading
- Clean interface makes adding caching wrapper straightforward
- Separation of concerns allows metrics injection without core changes

The architecture provides a solid foundation for production enhancements while
keeping the assessment implementation focused and understandable.
"""