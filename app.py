from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
from ticket_analyzer import analyzer

load_dotenv()

app = Flask(__name__)
CORS(app)

# This function is included to give you a means to make an LLM call as part of your solution. Using it is optional.
def _make_llm_call(prompt: str, model: str):
    """
    Mock function for LLM calls - replace with actual implementation
    Available models: ['gemini-3.0-flash', 'gemini-3.0-pro']
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
    
    This function serves as the main entry point for ticket analysis as specified
    in the assessment requirements. It uses the strategy pattern to support
    different analysis methods.
    
    Args:
        tickets: List of ticket dictionaries with structure:
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
        method: Analysis method to use ('keyword' or 'llm')
    
    Returns:
        str: Summary report for non-technical team members
        
    Design decisions:
    1. Added method parameter to support strategy selection
    2. Delegate to analyzer instance for separation of concerns
    3. Keep function signature compatible with assessment requirements
    
    Trade-offs:
    - Pro: Maintains compatibility with existing function signature
    - Pro: Allows easy switching between analysis methods
    - Con: Could be simplified by directly using analyzer, but this maintains
           the expected function interface from the assessment
    """
    return analyzer.analyze(tickets, method)


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "message": "Flask backend is running"})


@app.route('/api/process-tickets', methods=['POST'])
def process_tickets_endpoint():
    """
    Endpoint to process support tickets and return summary.
    
    Accepts JSON payload with:
    - tickets: List of ticket dictionaries (required)
    - method: Analysis method ('keyword' or 'llm', optional, defaults to 'keyword')
    
    Returns JSON response with summary and metadata.
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
    Endpoint to get available analysis methods.
    
    Returns:
        JSON response with list of available analysis methods
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