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
        # Define keyword categories for issue classification
        # These categories are based on common customer support issues
        # and can be extended based on domain knowledge
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
        self.urgency_keywords = ['urgent', 'critical', 'emergency', 'asap', 'immediately', 'production down']
        
        # Customer satisfaction keywords
        self.negative_sentiment = ['frustrated', 'angry', 'disappointed', 'terrible', 'awful', 'hate']
        self.positive_sentiment = ['happy', 'satisfied', 'great', 'excellent', 'love', 'perfect']

    def analyze_tickets(self, tickets: List[Dict[str, Any]]) -> str:
        """
        Perform keyword-based analysis of tickets.
        
        This method processes tickets to extract:
        - Basic statistics (counts by status, priority)
        - Issue categorization based on keywords
        - Customer sentiment analysis
        - Key insights and recommendations
        
        The analysis is designed to be useful for product managers and
        customer support leaders who need actionable insights.
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
        """Initialize LLM analysis strategy with Claude SDK configuration."""
        self.logger = logging.getLogger(__name__)
        
        # Configure Claude SDK options
        # Using minimal turns for focused analysis and cost control
        self.claude_options = ClaudeAgentOptions(
            max_turns=1,
            system_prompt="""You are an expert customer support analyst with years of experience 
            in analyzing support tickets and generating insights for product management teams. 
            Your role is to analyze customer support data and provide actionable insights that 
            help improve customer satisfaction and product development priorities.
            
            Generate analysis reports that are:
            - Professional and concise
            - Focused on actionable insights
            - Suitable for non-technical stakeholders
            - Data-driven and objective
            
            Always format your response as structured text that can be easily read by 
            product managers, customer support leaders, and executive teams."""
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
            # Prepare ticket data for LLM analysis
            # Anonymize sensitive information while preserving analytical value
            sanitized_tickets = self._prepare_tickets_for_analysis(tickets)
            
            # Generate analysis prompt
            prompt = self._create_analysis_prompt(sanitized_tickets)
            
            # Call Claude SDK asynchronously
            analysis_result = self._call_claude_async(prompt)
            
            # Post-process and format the result
            formatted_result = self._format_llm_response(analysis_result, len(tickets))
            
            return formatted_result
            
        except Exception as e:
            self.logger.error(f"LLM analysis failed: {str(e)}")
            # Graceful degradation - provide basic analysis instead of complete failure
            return self._generate_fallback_analysis(tickets, str(e))
    
    def _prepare_tickets_for_analysis(self, tickets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prepare and sanitize tickets for LLM analysis.
        
        This method:
        1. Removes or masks sensitive customer information
        2. Extracts relevant fields for analysis
        3. Limits data size to stay within token limits
        
        Privacy consideration: Customer IDs are anonymized but preserved
        for counting unique customers. Actual customer data is not included
        unless it's essential for analysis (e.g., conversation content).
        """
        sanitized = []
        
        for i, ticket in enumerate(tickets):
            # Anonymize customer ID while preserving uniqueness
            customer_id = ticket.get('customer_id', f'customer_{i}')
            anonymized_id = f"customer_{hash(customer_id) % 10000}"
            
            # Extract conversation summary (limit length for token efficiency)
            conversation_summary = self._summarize_conversation(ticket.get('conversation', []))
            
            sanitized_ticket = {
                'ticket_id': ticket.get('id', i),
                'created_at': ticket.get('created_at', ''),
                'customer_id': anonymized_id,
                'priority': ticket.get('priority', 'unknown'),
                'status': ticket.get('status', 'unknown'),
                'summary': ticket.get('summary', '')[:200],  # Limit summary length
                'conversation_summary': conversation_summary
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
        Create a structured prompt for Claude to analyze the tickets.
        
        The prompt is designed to:
        1. Provide clear context about the analysis task
        2. Include relevant ticket data in a structured format
        3. Request specific types of insights
        4. Guide the output format for consistency
        """
        tickets_json = json.dumps(tickets, indent=2)
        
        prompt = f"""Please analyze the following customer support tickets and generate a comprehensive weekly summary report for our product management and customer support leadership team.

TICKET DATA:
{tickets_json}

ANALYSIS REQUIREMENTS:
Please provide insights on the following areas:

1. OVERVIEW STATISTICS
   - Total tickets and unique customers
   - Status and priority distribution
   - Key volume metrics

2. ISSUE CATEGORIZATION
   - Identify main issue types and themes
   - Highlight emerging patterns or trends
   - Note any recurring problems

3. CUSTOMER SENTIMENT ANALYSIS
   - Overall sentiment trends
   - Identify frustrated vs satisfied customers
   - Note any escalating situations

4. PRIORITY ISSUES
   - Highlight 2-3 tickets that require immediate attention
   - Explain why these tickets are concerning
   - Suggest specific actions

5. STRATEGIC INSIGHTS
   - Root cause analysis of common issues
   - Product improvement recommendations
   - Process optimization suggestions
   - Risk assessment (customer churn, reputation, etc.)

6. ACTIONABLE RECOMMENDATIONS
   - Specific steps for the coming week
   - Resource allocation suggestions
   - Prevention strategies

FORMAT REQUIREMENTS:
- Use clear headings and bullet points
- Keep language professional but accessible
- Focus on actionable insights over raw statistics
- Include specific ticket references when relevant
- Limit response to approximately 1500 words
- Use emojis sparingly for visual organization

Generate a report that a product manager or customer support director would find immediately useful for decision-making."""
        
        return prompt
    
    def _call_claude_async(self, prompt: str) -> str:
        """
        Call Claude SDK asynchronously and collect the response.
        
        This method handles the async/await pattern required by the Claude SDK,
        similar to the implementation in the example code provided.
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