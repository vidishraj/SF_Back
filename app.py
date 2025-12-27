"""
Flask API for Customer Support Ticket Analysis

This module provides a REST API interface for the ticket analysis system. I chose
Flask over FastAPI or Django because the assessment scope suggests a simple API
with minimal dependencies.

KEY DESIGN DECISIONS:
--------------------
1. RESTful API design with clear endpoint purposes
2. Comprehensive error handling with helpful error messages  
3. CORS enabled for frontend integration
4. Environment-based configuration for flexibility
5. Graceful degradation when services are unavailable

API DESIGN PHILOSOPHY:
---------------------
I prioritized developer experience and reliability over feature richness.
The API should be intuitive to use and provide clear feedback when things go wrong.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
from ticket_analyzer import analyzer

load_dotenv()

app = Flask(__name__)
# CORS DECISION: Enable all origins for development
# In production, this should be restricted to specific frontend domains
CORS(app)

# ASSESSMENT PROVIDED FUNCTION
# ---------------------------  
# This function is included to give you a means to make an LLM call as part of your solution. Using it is optional.
# I chose NOT to use this function because:
# 1. I only have a claude subscription lol.

def _make_llm_call(prompt: str, model: str):
    """
    Mock function for LLM calls - replace with actual implementation
    Available models: ['gemini-3.0-flash', 'gemini-3.0-pro']
    
    NOTE: This function is not used in my implementation. I chose Claude SDK instead
    for better error handling and real analysis results.
    """
    avail_models = ['gemini-3.0-flash', 'gemini-3.0-pro']
    if model not in avail_models: 
        raise ValueError(f"Model {model} not supported.")
    
    # TODO: Implement actual LLM call using the other_file.py import
    # llm_response_str = make_llm_call(prompt, model)
    return "Mock LLM response"


def process_tickets(tickets: list, method: str = 'keyword') -> str:
    """
    Process customer support tickets and return a summary.
    
    ASSESSMENT COMPATIBILITY FUNCTION
    ---------------------------------
    This function maintains the exact signature expected by the assessment while
    internally using the more sophisticated analyzer architecture.
    
    DESIGN DECISION: Facade Pattern
    ------------------------------
    I kept this simple function as a facade to the more complex analyzer system because:
    1. COMPATIBILITY: Matches the expected assessment interface exactly
    2. SIMPLICITY: External users get a simple function call
    3. FLEXIBILITY: Internal implementation can be complex without affecting callers
    4. TESTING: Easy to test both the simple interface and complex implementation
    
    DATA CONTRACT (from assessment specification):
    {
        "id": int,
        "created_at": "YYYY-MM-DD HH:MM:SS", 
        "customer_id": str,
        "priority": str ("low" or "medium" or "high"),
        "status": str ("open" or "resolved"),
        "summary": str,
        "conversation": [
            {
                "sender": str ("customer" or "support"),
                "message": str, 
                "timestamp": "YYYY-MM-DD HH:MM:SS"
            }
        ]
    }
    
    TRADE-OFF ANALYSIS:
    - Pro: Clean separation between external interface and internal implementation
    - Pro: Makes the assessment reviewer's job easier (expected function exists)
    - Con: Slight additional layer of abstraction
    - Verdict: The compatibility benefits outweigh the minimal complexity cost
    """
    return analyzer.analyze(tickets, method)


@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for monitoring and frontend status indication.
    
    ENDPOINT DESIGN DECISION
    ------------------------
    I included this endpoint because:
    1. MONITORING: Production systems need health checks for load balancers
    2. USER FEEDBACK: Frontend can show connection status to users
    3. DEBUGGING: Easy way to verify the backend is running
    4. STANDARD PRACTICE: Expected in modern web APIs
    
    SIMPLE IMPLEMENTATION: Just returns success - could be enhanced to check
    database connections, external services, etc. in a production system.
    """
    return jsonify({"status": "healthy", "message": "Flask backend is running"})


@app.route('/api/process-tickets', methods=['POST'])
def process_tickets_endpoint():
    """
    Main analysis endpoint - processes support tickets and returns summary.
    
    API DESIGN DECISIONS
    -------------------
    1. POST METHOD: Ticket data can be large, POST is more appropriate than GET
    2. JSON PAYLOAD: Standard for modern APIs, easy to work with in frontend
    3. COMPREHENSIVE ERROR HANDLING: Different error types get appropriate HTTP codes
    4. METADATA RESPONSE: Include method used, ticket count for frontend display
    5. GRACEFUL DEGRADATION: Errors return helpful messages, not crashes
    
    REQUEST/RESPONSE FORMAT CHOICE
    -----------------------------
    I chose to include both the analysis result AND metadata because:
    - Frontend needs to know which method was used for display
    - Ticket count helps with user feedback
    - Available methods enable dynamic UI updates
    - Success flag makes error handling cleaner in frontend
    
    ERROR HANDLING STRATEGY
    ----------------------
    Different error types get different HTTP status codes:
    - 400 Bad Request: Client errors (missing data, invalid format)
    - 500 Internal Server Error: Server errors (unexpected exceptions)
    This helps frontend handle errors appropriately.
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        tickets = data.get('tickets', [])
        method = data.get('method', 'keyword')
        
        if not tickets:
            return jsonify({"error": "No tickets provided"}), 400
        
        if not isinstance(tickets, list):
            return jsonify({"error": "Tickets must be provided as an array"}), 400
        
        # Validate method
        available_methods = analyzer.get_available_methods()
        if method not in available_methods:
            return jsonify({
                "error": f"Invalid analysis method '{method}'. Available methods: {available_methods}"
            }), 400
        
        # Process tickets
        summary = process_tickets(tickets, method)
        
        return jsonify({
            "success": True,
            "summary": summary,
            "ticket_count": len(tickets),
            "method_used": method,
            "available_methods": available_methods
        })
    
    except ValueError as e:
        # Handle validation errors from analyzer
        return jsonify({"error": str(e)}), 400
    
    except Exception as e:
        # Handle unexpected errors
        app.logger.error(f"Unexpected error in process_tickets_endpoint: {str(e)}")
        return jsonify({"error": "An unexpected error occurred during processing"}), 500


@app.route('/api/analysis-methods', methods=['GET'])
def get_analysis_methods():
    """
    Endpoint to get available analysis methods for dynamic UI generation.
    
    DYNAMIC UI SUPPORT
    ------------------
    This endpoint enables the frontend to discover available analysis methods
    without hardcoding them. This is important because:
    1. FLEXIBILITY: New analysis methods appear in UI automatically
    2. CONFIGURATION: Different deployments can have different methods available
    3. ERROR HANDLING: UI can disable methods that aren't working
    4. FUTURE-PROOFING: Plugin architectures can add methods dynamically
    
    SIMPLE IMPLEMENTATION: Just returns static list for now, but architecture
    supports dynamic discovery in the future.
    """
    try:
        return jsonify({
            "success": True,
            "methods": analyzer.get_available_methods(),
            "default_method": "keyword"
        })
    
    except Exception as e:
        app.logger.error(f"Error getting analysis methods: {str(e)}")
        return jsonify({"error": "Failed to retrieve analysis methods"}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5500)


"""
FLASK API ARCHITECTURE DECISIONS AND TRADE-OFFS
===============================================

Framework Choice: Flask vs Alternatives
---------------------------------------
I chose Flask over other Python web frameworks because:

FLASK vs FASTAPI:
- Pro: Simpler for this scope, fewer dependencies
- Pro: More mature ecosystem, better documentation
- Con: No automatic API documentation (OpenAPI/Swagger)
- Con: No built-in async support (though not needed here)
- Verdict: Flask's simplicity fits the assessment scope better


API Design Philosophy
--------------------
I designed this as a RESTful API with these principles:

1. RESOURCE-ORIENTED URLS: /api/process-tickets, /api/health, etc.
2. HTTP SEMANTICS: POST for data processing, GET for retrieval
3. JSON COMMUNICATION: Standard for modern web APIs
4. COMPREHENSIVE ERROR HANDLING: Different codes for different error types
5. METADATA RESPONSES: Include context information for better UX

Error Handling Strategy
-----------------------
I implemented multi-layered error handling:

VALIDATION ERRORS (400): Bad input data, missing fields
- Return helpful error messages explaining what's wrong
- Don't expose internal implementation details
- Help developers fix their requests quickly

SERVER ERRORS (500): Unexpected exceptions, service failures
- Log detailed errors for debugging
- Return generic error messages to users (security)
- Ensure service stays responsive even when things break

DESIGN TRADE-OFF: Detailed vs Secure Error Messages
I chose detailed error messages for validation errors because:
- This is an assessment/development context
- Detailed feedback improves developer experience
- No sensitive data is exposed in validation errors

For production, I'd add more security around error message content.

CORS Configuration
------------------
I enabled CORS for all origins because:
- DEVELOPMENT: Frontend and backend run on different ports
- SIMPLICITY: No complex CORS configuration needed for assessment


Logging and Monitoring
----------------------
CURRENT APPROACH: Basic Flask logging for errors

Data Flow Architecture
----------------------
REQUEST FLOW: Client -> Flask -> Analyzer -> Strategy -> Response
1. Flask handles HTTP concerns (parsing, validation, headers)
2. Analyzer handles business logic (method selection, coordination)
3. Strategy handles specific analysis implementation
4. Response flows back with proper HTTP codes and format

This separation allows each layer to focus on its core responsibility while
maintaining clean interfaces between components.
"""