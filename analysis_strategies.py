"""
Customer Support Ticket Analysis Strategies

This module implements different ways to analyze customer support tickets. I chose to use
the Strategy pattern here because the assessment specifically asks for both keyword-based
and LLM-based analysis methods.

Why the Strategy Pattern?
-------------------------
Instead of having one big analysis function with if/else statements, I split the logic
into separate strategy classes. This makes it much easier to:
- Add new analysis methods later without breaking existing code
- Test each method independently  
- Switch between methods at runtime based on user preference
- Keep the code organized and readable

The trade-off is a bit more initial complexity, but it pays off quickly when you need
to maintain or extend the system.

Key Assumptions:
- Users want to choose between analysis methods (hence the UI selector)
- Both methods should generate similar output format for consistent UX
- Performance vs accuracy trade-offs are acceptable (keyword = fast, LLM = thorough)
- The target audience is non-technical team members (affects output format)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from collections import Counter, defaultdict
import re
from datetime import datetime
import json
import logging
import anyio
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock


class TicketAnalysisStrategy(ABC):
    """
    Abstract base class for ticket analysis strategies.
    
    This defines the interface that all analysis strategies must implement.
    Using the Strategy pattern allows us to easily switch between different
    analysis methods (keyword-based, LLM-based, etc.) without changing
    the core application logic.
    """
    
    @abstractmethod
    def analyze_tickets(self, tickets: List[Dict[str, Any]]) -> str:
        """
        Analyze a list of tickets and return a summary string.
        
        Args:
            tickets: List of ticket dictionaries
            
        Returns:
            str: Formatted summary for non-technical team members
        """
        pass


class KeywordAnalysisStrategy(TicketAnalysisStrategy):
    """
    Keyword-based analysis strategy for ticket processing.
    
    This strategy uses predefined keyword categories to analyze tickets
    and generate insights. It's fast, deterministic, and doesn't require
    external API calls, making it cost-effective and reliable.
    
    Trade-offs considered:
    - Pro: Fast, deterministic, no external dependencies
    - Pro: Cost-effective (no API calls)
    - Pro: Privacy-preserving (data doesn't leave our system)
    - Con: May miss nuanced issues not captured by keywords
    - Con: Requires manual keyword list maintenance
    """
    
    def __init__(self):
        """
        Initialize keyword categories and sentiment indicators.
        
        DESIGN DECISION: Pre-defined keyword categories
        -----------------------------------------------
        I chose to hardcode these categories rather than load from config because:
        1. SIMPLICITY: For this assessment, configuration complexity isn't needed
        2. TRANSPARENCY: Reviewers can easily see what keywords are being used
        3. PERFORMANCE: No file I/O on every analysis request
        
        TRADE-OFF: Less flexible than external config, but much simpler to implement
        and maintain for this scope. In production, these might come from a database.
        
        ASSUMPTION: These categories cover the most common support issues based on
        typical SaaS customer support patterns (auth, billing, bugs, features).
        """
        # Define keyword categories for issue classification
        # Each category has keywords and a severity level for prioritization
        self.keyword_categories = {
            'authentication': {
                'keywords': ['login', 'password', 'sign in', 'access', 'account', 'authentication', 'locked'],
                'severity': 'high'  # Authentication issues are typically urgent
            },
            'payment': {
                'keywords': ['payment', 'billing', 'charge', 'credit card', 'invoice', 'refund', 'subscription'],
                'severity': 'high'  # Payment issues affect revenue
            },
            'performance': {
                'keywords': ['slow', 'timeout', 'loading', 'lag', 'performance', 'speed', 'hang'],
                'severity': 'medium'
            },
            'bug': {
                'keywords': ['error', 'bug', 'crash', 'broken', 'not working', 'issue', 'problem'],
                'severity': 'medium'
            },
            'feature_request': {
                'keywords': ['feature', 'enhancement', 'suggestion', 'improvement', 'add', 'new'],
                'severity': 'low'
            },
            'integration': {
                'keywords': ['api', 'integration', 'webhook', 'sync', 'export', 'import'],
                'severity': 'medium'
            },
            'ui_ux': {
                'keywords': ['interface', 'design', 'confusing', 'layout', 'button', 'menu'],
                'severity': 'low'
            }
        }
        
        # Priority keywords that indicate urgent issues
        # REASONING: These help identify tickets that need immediate attention
        self.urgency_keywords = ['urgent', 'critical', 'emergency', 'asap', 'immediately', 'production down']
        
        # Customer satisfaction keywords for sentiment analysis
        # ASSUMPTION: Simple positive/negative word matching gives reasonable sentiment insight
        # TRADE-OFF: Not as sophisticated as NLP sentiment analysis, but much faster and simpler
        self.negative_sentiment = ['frustrated', 'angry', 'disappointed', 'terrible', 'awful', 'hate']
        self.positive_sentiment = ['happy', 'satisfied', 'great', 'excellent', 'love', 'perfect']

    def analyze_tickets(self, tickets: List[Dict[str, Any]]) -> str:
        """
        Perform keyword-based analysis of tickets.
        
        APPROACH: Multi-step analysis pipeline
        --------------------------------------
        I broke this into distinct steps rather than one large function because:
        1. READABILITY: Each step has a clear purpose and can be understood independently
        2. TESTABILITY: Each step can be unit tested in isolation
        3. MAINTAINABILITY: Easy to modify one aspect without affecting others
        4. DEBUGGABILITY: Can easily see which step is causing issues if something breaks
        
        ASSUMPTION: The assessment wants a comprehensive weekly summary that includes
        all the standard metrics a support team would need (status, priority, trends, etc.)
        
        OUTPUT FORMAT DECISION: Plain text report instead of JSON
        --------------------------------------------------------
        I chose formatted text because:
        - The assessment specifies "non-technical team members" as the audience
        - Text reports are immediately readable without additional processing
        - Easy to copy/paste into emails, Slack, or documents
        """
        if not tickets:
            return "No tickets to analyze."
        
        # Basic statistics
        stats = self._calculate_basic_stats(tickets)
        
        # Categorize issues by keywords
        categories = self._categorize_issues(tickets)
        
        # Analyze customer sentiment
        sentiment = self._analyze_sentiment(tickets)
        
        # Identify high-priority tickets
        priority_tickets = self._identify_priority_tickets(tickets)
        
        # Generate insights
        insights = self._generate_insights(tickets, categories, sentiment)
        
        # Format the summary
        summary = self._format_summary(stats, categories, sentiment, priority_tickets, insights)
        
        return summary

    def _calculate_basic_stats(self, tickets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate basic ticket statistics."""
        total_tickets = len(tickets)
        
        # Count by status
        status_counts = Counter(ticket.get('status', 'unknown') for ticket in tickets)
        
        # Count by priority
        priority_counts = Counter(ticket.get('priority', 'unknown') for ticket in tickets)
        
        # Count messages
        total_customer_messages = 0
        total_support_messages = 0
        
        for ticket in tickets:
            for message in ticket.get('conversation', []):
                if message.get('sender') == 'customer':
                    total_customer_messages += 1
                elif message.get('sender') == 'support':
                    total_support_messages += 1
        
        # Count unique customers
        unique_customers = len(set(ticket.get('customer_id') for ticket in tickets if ticket.get('customer_id')))
        
        return {
            'total_tickets': total_tickets,
            'status_counts': dict(status_counts),
            'priority_counts': dict(priority_counts),
            'customer_messages': total_customer_messages,
            'support_messages': total_support_messages,
            'unique_customers': unique_customers
        }

    def _categorize_issues(self, tickets: List[Dict[str, Any]]) -> Dict[str, Dict]:
        """Categorize tickets based on keyword matching."""
        categories = defaultdict(lambda: {'count': 0, 'tickets': [], 'severity_score': 0})
        
        for ticket in tickets:
            # Combine all text content for analysis
            text_content = self._extract_text_content(ticket)
            text_lower = text_content.lower()
            
            # Check each category
            ticket_categories = []
            for category_name, category_data in self.keyword_categories.items():
                keyword_matches = sum(1 for keyword in category_data['keywords'] 
                                    if keyword in text_lower)
                
                if keyword_matches > 0:
                    categories[category_name]['count'] += 1
                    categories[category_name]['tickets'].append(ticket['id'])
                    
                    # Add severity score based on category and priority
                    severity_multiplier = {'high': 3, 'medium': 2, 'low': 1}
                    priority_multiplier = {'high': 3, 'medium': 2, 'low': 1}
                    
                    severity_score = (severity_multiplier.get(category_data['severity'], 1) * 
                                    priority_multiplier.get(ticket.get('priority', 'low'), 1))
                    categories[category_name]['severity_score'] += severity_score
                    
                    ticket_categories.append(category_name)
            
            # If no category matches, classify as 'other'
            if not ticket_categories:
                categories['other']['count'] += 1
                categories['other']['tickets'].append(ticket['id'])
        
        return dict(categories)

    def _analyze_sentiment(self, tickets: List[Dict[str, Any]]) -> Dict[str, int]:
        """Analyze customer sentiment based on keyword presence."""
        negative_count = 0
        positive_count = 0
        neutral_count = 0
        
        for ticket in tickets:
            text_content = self._extract_text_content(ticket).lower()
            
            # Check for sentiment keywords
            has_negative = any(keyword in text_content for keyword in self.negative_sentiment)
            has_positive = any(keyword in text_content for keyword in self.positive_sentiment)
            
            if has_negative and not has_positive:
                negative_count += 1
            elif has_positive and not has_negative:
                positive_count += 1
            else:
                neutral_count += 1
        
        return {
            'negative': negative_count,
            'positive': positive_count,
            'neutral': neutral_count
        }

    def _identify_priority_tickets(self, tickets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify tickets that should be highlighted to the team."""
        priority_tickets = []
        
        for ticket in tickets:
            text_content = self._extract_text_content(ticket).lower()
            
            # High priority conditions
            is_urgent = any(keyword in text_content for keyword in self.urgency_keywords)
            is_high_priority = ticket.get('priority') == 'high'
            is_open = ticket.get('status') == 'open'
            has_long_conversation = len(ticket.get('conversation', [])) > 10
            
            # Calculate priority score
            priority_score = 0
            if is_urgent: priority_score += 3
            if is_high_priority: priority_score += 2
            if is_open: priority_score += 1
            if has_long_conversation: priority_score += 1
            
            if priority_score >= 3:  # Threshold for highlighting
                priority_tickets.append({
                    'ticket': ticket,
                    'priority_score': priority_score,
                    'reasons': []
                })
                
                # Add reasons for highlighting
                if is_urgent: priority_tickets[-1]['reasons'].append('Contains urgency keywords')
                if is_high_priority: priority_tickets[-1]['reasons'].append('High priority')
                if is_open: priority_tickets[-1]['reasons'].append('Still open')
                if has_long_conversation: priority_tickets[-1]['reasons'].append('Extended conversation')
        
        # Sort by priority score and limit to top 5
        priority_tickets.sort(key=lambda x: x['priority_score'], reverse=True)
        return priority_tickets[:5]

    def _generate_insights(self, tickets: List[Dict[str, Any]], categories: Dict, sentiment: Dict) -> List[str]:
        """Generate actionable insights based on the analysis."""
        insights = []
        
        # Resolution rate insight
        resolved_count = sum(1 for ticket in tickets if ticket.get('status') == 'resolved')
        resolution_rate = (resolved_count / len(tickets)) * 100 if tickets else 0
        
        if resolution_rate < 70:
            insights.append(f"Resolution rate is {resolution_rate:.1f}% - consider reviewing support processes")
        elif resolution_rate > 90:
            insights.append(f"Excellent resolution rate of {resolution_rate:.1f}%")
        
        # Category insights
        if categories:
            top_category = max(categories.items(), key=lambda x: x[1]['count'])
            insights.append(f"Most common issue type: {top_category[0]} ({top_category[1]['count']} tickets)")
        
        # Sentiment insights
        total_sentiment = sum(sentiment.values())
        if total_sentiment > 0:
            negative_percentage = (sentiment['negative'] / total_sentiment) * 100
            if negative_percentage > 30:
                insights.append(f"High negative sentiment: {negative_percentage:.1f}% of tickets show customer frustration")
        
        # Authentication issues insight
        auth_issues = categories.get('authentication', {}).get('count', 0)
        if auth_issues > len(tickets) * 0.2:  # More than 20% of tickets
            insights.append("High volume of authentication issues - consider reviewing login flow")
        
        return insights

    def _extract_text_content(self, ticket: Dict[str, Any]) -> str:
        """Extract all text content from a ticket for analysis."""
        text_parts = [
            ticket.get('summary', ''),
        ]
        
        # Add conversation messages
        for message in ticket.get('conversation', []):
            text_parts.append(message.get('message', ''))
        
        return ' '.join(text_parts)

    def _format_summary(self, stats: Dict, categories: Dict, sentiment: Dict, 
                       priority_tickets: List, insights: List[str]) -> str:
        """Format the analysis results into a readable summary."""
        summary_parts = []
        
        # Header
        summary_parts.append("🎫 WEEKLY CUSTOMER SUPPORT SUMMARY")
        summary_parts.append("=" * 50)
        summary_parts.append("")
        
        # Basic statistics
        summary_parts.append("📊 OVERVIEW")
        summary_parts.append(f"Total Tickets: {stats['total_tickets']}")
        summary_parts.append(f"Unique Customers: {stats['unique_customers']}")
        summary_parts.append(f"Customer Messages: {stats['customer_messages']}")
        summary_parts.append(f"Support Messages: {stats['support_messages']}")
        summary_parts.append("")
        
        # Status breakdown
        summary_parts.append("📈 TICKET STATUS")
        for status, count in stats['status_counts'].items():
            percentage = (count / stats['total_tickets']) * 100
            summary_parts.append(f"  {status.title()}: {count} ({percentage:.1f}%)")
        summary_parts.append("")
        
        # Priority breakdown
        summary_parts.append("🚨 PRIORITY DISTRIBUTION")
        for priority, count in stats['priority_counts'].items():
            percentage = (count / stats['total_tickets']) * 100
            summary_parts.append(f"  {priority.title()}: {count} ({percentage:.1f}%)")
        summary_parts.append("")
        
        # Issue categories
        if categories:
            summary_parts.append("🏷️  ISSUE CATEGORIES")
            sorted_categories = sorted(categories.items(), key=lambda x: x[1]['count'], reverse=True)
            for category, data in sorted_categories:
                if data['count'] > 0:
                    percentage = (data['count'] / stats['total_tickets']) * 100
                    summary_parts.append(f"  {category.title().replace('_', ' ')}: {data['count']} ({percentage:.1f}%)")
            summary_parts.append("")
        
        # Customer sentiment
        total_sentiment = sum(sentiment.values())
        if total_sentiment > 0:
            summary_parts.append("😊 CUSTOMER SENTIMENT")
            for sentiment_type, count in sentiment.items():
                percentage = (count / total_sentiment) * 100
                emoji = "😞" if sentiment_type == "negative" else "😊" if sentiment_type == "positive" else "😐"
                summary_parts.append(f"  {emoji} {sentiment_type.title()}: {count} ({percentage:.1f}%)")
            summary_parts.append("")
        
        # Priority tickets
        if priority_tickets:
            summary_parts.append("🔥 TICKETS REQUIRING ATTENTION")
            for i, item in enumerate(priority_tickets, 1):
                ticket = item['ticket']
                reasons = ", ".join(item['reasons'])
                summary_parts.append(f"  {i}. Ticket #{ticket['id']} - {ticket.get('summary', 'No summary')[:60]}...")
                summary_parts.append(f"     Priority: {ticket.get('priority', 'unknown')} | Status: {ticket.get('status', 'unknown')}")
                summary_parts.append(f"     Reasons: {reasons}")
                summary_parts.append("")
        
        # Insights
        if insights:
            summary_parts.append("💡 KEY INSIGHTS & RECOMMENDATIONS")
            for insight in insights:
                summary_parts.append(f"  • {insight}")
            summary_parts.append("")
        
        # Footer
        summary_parts.append("=" * 50)
        summary_parts.append(f"Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        summary_parts.append("Analysis method: Keyword-based classification")
        
        return "\n".join(summary_parts)


class LLMAnalysisStrategy(TicketAnalysisStrategy):
    """
    LLM-based analysis strategy using Claude SDK for advanced ticket processing.
    
    This strategy leverages Claude's natural language understanding to provide
    more nuanced analysis of customer support tickets, including sentiment
    analysis, trend identification, and intelligent insights generation.
    
    Trade-offs considered:
    - Pro: More sophisticated analysis with natural language understanding
    - Pro: Can identify complex patterns and nuanced issues
    - Pro: Generates human-like insights and recommendations
    - Pro: Adaptable to different domains without code changes
    - Con: Requires API calls (cost and latency implications)
    - Con: Non-deterministic results (may vary between runs)
    - Con: Requires internet connectivity and API availability
    - Con: May expose customer data to external service (privacy consideration)
    
    Design decisions:
    1. Using Claude SDK for reliable LLM integration
    2. Structured prompt engineering for consistent output format
    3. Error handling for API failures with graceful degradation
    4. Async/await pattern for efficient API calls
    """
    
    def __init__(self):
        """
        Initialize LLM analysis strategy with Claude SDK configuration.
        
        CLAUDE SDK CHOICE
        -----------------
        I chose Claude SDK over direct API calls because:
        1. RELIABILITY: Built-in retry logic and error handling
        2. SIMPLICITY: Less boilerplate code for common operations
        3. MAINTENANCE: SDK handles API changes automatically
        4. FEATURES: Built-in streaming and async support
        
        SYSTEM PROMPT STRATEGY
        ----------------------
        I kept the system prompt minimal because:
        - The main instructions are in the user prompt (more flexible)
        - Minimal system prompts often work better for specific tasks
        - Easier to modify behavior without changing code
        
        TRADE-OFF: Could have put more constraints in system prompt for consistency,
        but chose flexibility over rigid structure.
        """
        self.logger = logging.getLogger(__name__)
        
        # Configure Claude SDK options with minimal system prompt
        # ASSUMPTION: max_turns=1 is sufficient since we only need one analysis response
        self.claude_options = ClaudeAgentOptions(
            max_turns=1,
            system_prompt="You are a support ticket analyst. Provide concise, actionable insights from ticket data. Keep responses brief and focused."
        )
    
    def analyze_tickets(self, tickets: List[Dict[str, Any]]) -> str:
        """
        Perform LLM-based analysis of customer support tickets.
        
        This method uses Claude to analyze tickets and generate sophisticated
        insights that go beyond keyword matching. The LLM can identify:
        - Complex sentiment patterns
        - Emerging issues and trends
        - Root cause analysis
        - Strategic recommendations
        - Customer journey insights
        
        Args:
            tickets: List of ticket dictionaries to analyze
            
        Returns:
            str: Comprehensive analysis report generated by Claude
            
        Raises:
            Exception: If LLM analysis fails, falls back to error message
        """
        if not tickets:
            return "No tickets to analyze."
        
        try:
            import time
            start_time = time.time()
            
            # Prepare ticket data for LLM analysis
            sanitized_tickets = self._prepare_tickets_for_analysis(tickets)
            prep_time = time.time()
            self.logger.info(f"Data preparation took: {prep_time - start_time:.2f} seconds")
            
            # Generate analysis prompt
            prompt = self._create_analysis_prompt(sanitized_tickets)
            prompt_time = time.time()
            self.logger.info(f"Prompt creation took: {prompt_time - prep_time:.2f} seconds")
            self.logger.info(f"Prompt length: {len(prompt)} characters")
            
            # Call Claude SDK asynchronously
            analysis_result = self._call_claude_async(prompt)
            claude_time = time.time()
            self.logger.info(f"Claude API call took: {claude_time - prompt_time:.2f} seconds")
            
            # Post-process and format the result
            formatted_result = self._format_llm_response(analysis_result, len(tickets))
            
            total_time = time.time()
            self.logger.info(f"Total LLM analysis time: {total_time - start_time:.2f} seconds")
            
            return formatted_result
            
        except Exception as e:
            self.logger.error(f"LLM analysis failed: {str(e)}")
            # Graceful degradation - provide basic analysis instead of complete failure
            return self._generate_fallback_analysis(tickets, str(e))
    
    def _prepare_tickets_for_analysis(self, tickets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prepare tickets for LLM analysis with accurate message counting.
        
        DATA SANITIZATION STRATEGY
        --------------------------
        I transform the raw ticket data because:
        1. TOKEN EFFICIENCY: LLMs have context limits, so I extract just the essential info
        2. COST OPTIMIZATION: Less data = fewer tokens = lower API costs
        4. CONSISTENCY: Ensure all tickets have the same data structure
        
        KEY DESIGN DECISIONS:
        - Process ALL tickets (user requested no limits after seeing loading overlay)
        - Truncate summaries to 200 chars (balance context vs token usage)
        - Pre-calculate message counts (expensive to do in LLM prompt)
        - Flag escalations (helps LLM identify priority tickets)
        
        ASSUMPTION: The metadata (counts, flags, truncated summary) provides sufficient
        context for LLM to generate useful insights without full conversation text.
        """
        sanitized = []
        
        # Calculate accurate message counts across all tickets for the prompt
        self.total_customer_messages = 0
        self.total_support_messages = 0
        
        for ticket in tickets:
            conversation = ticket.get('conversation', [])
            for msg in conversation:
                if msg.get('sender') == 'customer':
                    self.total_customer_messages += 1
                elif msg.get('sender') == 'support':
                    self.total_support_messages += 1
        
        for i, ticket in enumerate(tickets):
            conversation = ticket.get('conversation', [])
            
            # Count customer/support messages for this ticket
            customer_msg_count = sum(1 for msg in conversation if msg.get('sender') == 'customer')
            support_msg_count = sum(1 for msg in conversation if msg.get('sender') == 'support')
            
            sanitized_ticket = {
                'id': ticket.get('id', i),
                'priority': ticket.get('priority', 'unknown'),
                'status': ticket.get('status', 'unknown'),
                'summary': ticket.get('summary', '')[:200],  # Increased back to 200 chars
                'msg_count': len(conversation),
                'customer_msg_count': customer_msg_count,
                'support_msg_count': support_msg_count,
                'has_customer_escalation': any('urgent' in msg.get('message', '').lower() or 
                                              'frustrated' in msg.get('message', '').lower() or
                                              'asap' in msg.get('message', '').lower()
                                             for msg in conversation if msg.get('sender') == 'customer')
            }
            
            sanitized.append(sanitized_ticket)
        
        return sanitized
    
    def _summarize_conversation(self, conversation: List[Dict[str, Any]]) -> str:
        """
        Create a concise summary of ticket conversation for LLM analysis.
        
        This helps stay within token limits while preserving essential context.
        """
        if not conversation:
            return "No conversation available"
        
        # Extract key conversation elements
        customer_messages = []
        support_messages = []
        
        for message in conversation:
            sender = message.get('sender', 'unknown')
            content = message.get('message', '')[:100]  # Limit message length
            
            if sender == 'customer':
                customer_messages.append(content)
            elif sender == 'support':
                support_messages.append(content)
        
        summary_parts = []
        
        if customer_messages:
            summary_parts.append(f"Customer concerns: {' | '.join(customer_messages[:2])}")
        
        if support_messages:
            summary_parts.append(f"Support responses: {' | '.join(support_messages[:2])}")
        
        summary_parts.append(f"Message count: {len(conversation)} total")
        
        return "; ".join(summary_parts)
    
    def _create_analysis_prompt(self, tickets: List[Dict[str, Any]]) -> str:
        """
        Create a prompt that meets the specific assessment requirements.
        Ensures the summary includes all required elements for weekly team review.
        """
        # Calculate required statistics
        total_tickets = len(tickets)
        
        # Status counts
        open_tickets = sum(1 for t in tickets if t.get('status') == 'open')
        resolved_tickets = sum(1 for t in tickets if t.get('status') == 'resolved')
        
        # Priority counts  
        high_priority = sum(1 for t in tickets if t.get('priority') == 'high')
        medium_priority = sum(1 for t in tickets if t.get('priority') == 'medium')
        low_priority = sum(1 for t in tickets if t.get('priority') == 'low')
        
        # Use accurate message counts calculated during data preparation
        customer_messages = getattr(self, 'total_customer_messages', 0)
        support_messages = getattr(self, 'total_support_messages', 0)
        
        # Key tickets that need attention
        key_tickets = []
        for ticket in tickets:  # Check ALL tickets
            if (ticket.get('priority') == 'high' or 
                ticket.get('status') == 'open' or 
                ticket.get('has_customer_escalation')):
                key_tickets.append(f"#{ticket.get('id')}: {ticket.get('summary')[:80]}... [{ticket.get('priority')}/{ticket.get('status')}]")
        
        prompt = f"""Generate a WEEKLY SUPPORT SUMMARY for our product management and customer support team.

TICKET DATA ANALYSIS:
- Total Tickets: {total_tickets}
- Status: Open ({open_tickets}), Resolved ({resolved_tickets})
- Priority: High ({high_priority}), Medium ({medium_priority}), Low ({low_priority})
- Messages: {customer_messages} customer, {support_messages} support
- Key Tickets Needing Attention: {len(key_tickets)} tickets

SAMPLE KEY TICKETS:
{chr(10).join(key_tickets[:3])}

REQUIRED SUMMARY FORMAT:
Generate a professional weekly summary that MUST include:

1. OVERVIEW STATISTICS
   - Total number of tickets: {total_tickets}
   - Count by status (Open: {open_tickets}, Resolved: {resolved_tickets})
   - Count by priority (High: {high_priority}, Medium: {medium_priority}, Low: {low_priority})
   - Total messages (Customer: {customer_messages}, Support: {support_messages})

2. KEY TICKETS FOR ATTENTION
   - Highlight 2-3 specific tickets that need team focus
   - Explain why each ticket is important
   - Include ticket numbers and brief descriptions

3. INSIGHTS & TRENDS
   - Support trends and patterns
   - Resolution rate analysis
   - Customer satisfaction indicators
   - Emerging issues or concerns

4. RECOMMENDATIONS
   - 2-3 specific action items for the team
   - Priority focus areas for next week

Target audience: Non-technical team members (product managers, customer support leaders)
Keep professional, actionable, and under 600 words."""
        
        return prompt
    
    def _call_claude_async(self, prompt: str) -> str:
        """
        Call Claude SDK without timeout limits for complete analysis.
        """
        output_text = ""
        
        async def get_claude_response():
            nonlocal output_text
            
            try:
                async for message in query(prompt=prompt, options=self.claude_options):
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                output_text += block.text
                                self.logger.debug(f"Received text block: {len(block.text)} characters")
                
            except Exception as e:
                self.logger.error(f"Claude SDK error: {e}")
                self.logger.error(f"Error type: {type(e)}")
                import traceback
                self.logger.error(f"Full traceback: {traceback.format_exc()}")
                raise Exception(f"Claude analysis failed: {str(e)}")
        
        # Run async query in sync context
        anyio.run(get_claude_response)
        
        if not output_text:
            raise Exception("Claude returned empty response")
        
        self.logger.info(f"Claude analysis completed: {len(output_text)} characters")
        return output_text
    
    def _format_llm_response(self, claude_response: str, ticket_count: int) -> str:
        """
        Post-process and format the Claude response for consistency.
        
        This ensures the output follows a consistent format regardless
        of variations in Claude's response style.
        """
        # Add header if not present
        if not claude_response.startswith("🎫"):
            header = f"🎫 WEEKLY CUSTOMER SUPPORT SUMMARY (LLM Analysis)\n{'=' * 60}\n\n"
            claude_response = header + claude_response
        
        # Add footer with metadata
        footer = f"\n\n{'=' * 60}\n"
        footer += f"Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        footer += f"Analysis method: Claude LLM (Advanced AI Analysis)\n"
        footer += f"Tickets analyzed: {ticket_count}\n"
        footer += "Note: This analysis uses artificial intelligence to identify patterns and generate insights."
        
        return claude_response + footer
    
    def _generate_fallback_analysis(self, tickets: List[Dict[str, Any]], error_msg: str) -> str:
        """
        Generate a basic fallback analysis when LLM analysis fails.
        
        This provides graceful degradation by offering basic statistics
        instead of a complete failure. This approach ensures the system
        remains functional even when the LLM service is unavailable.
        """
        total_tickets = len(tickets)
        status_counts = Counter(ticket.get('status', 'unknown') for ticket in tickets)
        priority_counts = Counter(ticket.get('priority', 'unknown') for ticket in tickets)
        unique_customers = len(set(ticket.get('customer_id') for ticket in tickets if ticket.get('customer_id')))
        
        fallback_summary = f"""🎫 WEEKLY CUSTOMER SUPPORT SUMMARY (Fallback Analysis)
{'=' * 60}

⚠️  LLM Analysis Unavailable
The advanced AI analysis could not be completed due to: {error_msg}
Providing basic statistical summary instead.

📊 BASIC OVERVIEW
Total Tickets: {total_tickets}
Unique Customers: {unique_customers}

📈 TICKET STATUS
"""
        
        for status, count in status_counts.items():
            percentage = (count / total_tickets) * 100 if total_tickets > 0 else 0
            fallback_summary += f"  {status.title()}: {count} ({percentage:.1f}%)\n"
        
        fallback_summary += "\n🚨 PRIORITY DISTRIBUTION\n"
        
        for priority, count in priority_counts.items():
            percentage = (count / total_tickets) * 100 if total_tickets > 0 else 0
            fallback_summary += f"  {priority.title()}: {count} ({percentage:.1f}%)\n"
        
        fallback_summary += f"""
💡 RECOMMENDATION
Please check the LLM service configuration and try again for detailed analysis.
For immediate insights, consider using the keyword-based analysis method.

{'=' * 60}
Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Analysis method: Fallback (LLM service unavailable)
"""
        
        return fallback_summary


"""
OVERALL SOLUTION ARCHITECTURE AND REASONING
===========================================

High-Level Approach
-------------------
I designed this as a dual-strategy system where users can choose between keyword-based and
LLM-based analysis. This wasn't just about implementing two methods - it was about creating
a flexible architecture that could grow with future needs.

Why Strategy Pattern Over Simple If/Else?
-----------------------------------------
Initially, I considered just having a single function with if/else logic for the two methods.
However, I chose the Strategy pattern because:

1. SCALABILITY: The assessment hinted at potential future expansion
2. TESTABILITY: Each strategy can be thoroughly tested in isolation
3. MAINTAINABILITY: Changes to one method don't risk breaking the other
4. CLEAN CODE: Separation of concerns makes the codebase easier to understand

The trade-off was additional upfront complexity, but this pays dividends as soon as you need
to modify or extend the system.

Performance vs. Accuracy Trade-offs
-----------------------------------
KEYWORD STRATEGY:
- Performance: Very fast, processes hundreds of tickets in seconds
- Accuracy: Good for obvious patterns, may miss subtle issues
- Use case: Quick daily summaries, high-volume processing

LLM STRATEGY:
- Performance: Slower due to API calls, can take 1-2 minutes for large datasets
- Accuracy: Excellent for nuanced insights and patterns
- Use case: Weekly deep-dive reports, strategic analysis

I made these trade-offs explicit in the UI so users can make informed choices based on
their immediate needs (quick check vs. thorough analysis).

Data Processing Philosophy
--------------------------
KEYWORD APPROACH: I chose comprehensive data processing with multiple analysis dimensions
(categories, sentiment, priority scoring) rather than simple keyword counting. This provides
much richer insights while maintaining the speed advantage.

LLM APPROACH: I focused on data sanitization and prompt engineering rather than raw data
dumping. The LLM gets structured, pre-processed data that's optimized for analysis while
staying within token limits and cost constraints.

Error Handling Strategy
-----------------------
I implemented graceful degradation rather than hard failures:
- LLM failures fall back to basic statistics
- Missing data gets default values rather than errors
- User sees something useful even when systems partially fail

This was critical because support teams need reliable reporting even when external services
have issues.

Key Assumptions That Shaped the Design
-------------------------------------
1. TARGET AUDIENCE: Non-technical team members (product managers, support leaders)
   - Impact: Plain text reports, emoji icons, percentage breakdowns
   - Alternative considered: JSON output for developers, rejected for accessibility

2. USAGE PATTERNS: Weekly team meetings and daily quick checks
   - Impact: Two-tiered analysis (quick keyword, thorough LLM)
   - Alternative considered: Single advanced method, rejected for performance

3. DATA VOLUME: Hundreds of tickets per week, not thousands
   - Impact: No pagination, process all tickets at once
   - Alternative considered: Streaming analysis, rejected for complexity

4. INFRASTRUCTURE: Standard web deployment, not high-performance computing
   - Impact: In-memory processing, simple data structures
   - Alternative considered: Database storage, rejected as overkill for scope

Limitations and Future Improvements
-----------------------------------
CURRENT LIMITATIONS:
1. Keyword categories are hardcoded (should be configurable)
2. No historical trending (only point-in-time analysis)
3. No customer segmentation (treats all customers equally)
4. No integration with actual support platforms
5. Simple sentiment analysis (could use proper NLP)

CONSCIOUS TRADE-OFFS FOR ASSESSMENT SCOPE:
- Chose simplicity over enterprise features
- Prioritized demonstrating architectural thinking over feature completeness
- Focused on code quality and reasoning over UI polish

If this were a production system, I would add:
- Configuration management for keywords and thresholds
- Database persistence for historical analysis
- More sophisticated NLP for sentiment and categorization
- Integration APIs for common support platforms (Zendesk, Intercom, etc.)
- Caching and background processing for large datasets
- A/B testing framework for comparing analysis methods

The architecture I've built here provides a solid foundation for all these enhancements
without requiring major restructuring.
"""