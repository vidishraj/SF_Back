# Backend Architecture

## Overview

Flask API with dual analysis strategies using the Strategy Pattern.

## Architecture

```
Flask API → Ticket Analyzer → Strategy (Keyword/LLM)
```

## Key Design Decisions

### Strategy Pattern
Two analysis approaches:
- **Keyword Strategy**: Fast, predefined categories
- **LLM Strategy**: AI analysis using Claude SDK

### Why Flask?
- Simple, lightweight for this scope
- No ORM needed (stateless analysis)
- Easy to understand and debug

### Error Handling
- Input validation at API level
- Graceful LLM fallbacks
- Clear error messages

## File Structure

- `app.py` - Flask routes and configuration
- `ticket_analyzer.py` - Strategy coordination
- `analysis_strategies.py` - Analysis implementations

## Trade-offs Made

**Strategy Pattern vs Simple If/Else**
- Pro: Easy to add new analysis methods
- Pro: Better testing isolation
- Con: Slightly more complex

**Flask vs FastAPI**
- Pro: Simpler, fewer dependencies
- Con: No automatic API docs

**In-Memory vs Database**
- Pro: Simpler for assessment scope
- Con: No persistence for production use