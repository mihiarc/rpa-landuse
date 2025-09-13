#!/usr/bin/env python3
"""
Automatic prompt selection system based on user query analysis.
Detects query intent and selects appropriate specialized prompts.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from landuse.agents.prompts import PromptVariations, get_system_prompt


@dataclass
class QueryIntent:
    """Represents detected intent from user query."""
    domain_focus: Optional[str] = None
    analysis_style: str = "standard"
    confidence: float = 0.0
    keywords_matched: List[str] = None
    
    def __post_init__(self):
        if self.keywords_matched is None:
            self.keywords_matched = []


class PromptSelector:
    """
    Automatically selects specialized prompts based on user query content.
    """
    
    def __init__(self):
        """Initialize the prompt selector with keyword patterns."""
        self.domain_patterns = {
            "agricultural": {
                "keywords": [
                    "agricultural", "agriculture", "farm", "farming", "crop", "crops", 
                    "cropland", "pasture", "livestock", "cattle", "food", "harvest",
                    "irrigation", "soil", "yield", "production", "feed", "grain",
                    "corn", "wheat", "soy", "beef", "dairy", "ranching", "grazing"
                ],
                "phrases": [
                    "agricultural land", "farm land", "crop production", "food security",
                    "agricultural productivity", "farming operations", "crop yields"
                ]
            },
            "climate": {
                "keywords": [
                    "climate", "rcp", "ssp", "scenario", "scenarios", "warming",
                    "temperature", "precipitation", "drought", "flood", "weather",
                    "carbon", "emissions", "mitigation", "adaptation", "resilience",
                    "pathway", "projections"
                ],
                "phrases": [
                    "climate change", "climate scenarios", "climate impacts", 
                    "global warming", "climate pathways", "rcp45", "rcp85",
                    "climate projections", "future climate"
                ]
            },
            "urban": {
                "keywords": [
                    "urban", "city", "cities", "development", "sprawl", "suburb",
                    "residential", "commercial", "infrastructure", "roads", "housing",
                    "population", "growth", "density", "zoning", "planning",
                    "metropolitan", "downtown", "neighborhood", "subdivision", "expansion"
                ],
                "phrases": [
                    "urban development", "urban expansion", "urban sprawl", 
                    "urban planning", "city growth", "metropolitan area",
                    "residential development", "commercial development"
                ]
            }
        }
        
        self.analysis_style_patterns = {
            "detailed": {
                "keywords": [
                    "detailed", "comprehensive", "thorough", "analysis", "deep",
                    "statistics", "correlation", "regression", "significance",
                    "research", "study", "investigate", "examine", "explore"
                ],
                "phrases": [
                    "detailed analysis", "comprehensive study", "in-depth",
                    "statistical analysis", "research question"
                ]
            },
            "executive": {
                "keywords": [
                    "summary", "brief", "overview", "key", "main", "important",
                    "highlights", "executive", "policy", "decision", "recommend",
                    "strategic", "priorities", "implications", "impact"
                ],
                "phrases": [
                    "executive summary", "key findings", "main points",
                    "policy implications", "strategic overview"
                ]
            }
        }
    
    def analyze_query(self, query: str) -> QueryIntent:
        """
        Analyze user query to determine appropriate prompt specialization.
        
        Args:
            query: User's natural language query
            
        Returns:
            QueryIntent with detected domain focus and analysis style
        """
        query_lower = query.lower()
        
        # Detect domain focus
        domain_scores = {}
        for domain, patterns in self.domain_patterns.items():
            score = self._calculate_domain_score(query_lower, patterns)
            if score > 0:
                domain_scores[domain] = score
        
        # Detect analysis style
        style_scores = {}
        for style, patterns in self.analysis_style_patterns.items():
            score = self._calculate_domain_score(query_lower, patterns)
            if score > 0:
                style_scores[style] = score
        
        # Determine best domain focus
        domain_focus = None
        domain_confidence = 0.0
        domain_keywords = []
        
        if domain_scores:
            best_domain = max(domain_scores.keys(), key=lambda k: domain_scores[k])
            domain_confidence = domain_scores[best_domain]
            if domain_confidence >= 0.3:  # Minimum confidence threshold
                domain_focus = best_domain
                domain_keywords = self._get_matched_keywords(query_lower, self.domain_patterns[best_domain])
        
        # Determine analysis style
        analysis_style = "standard"
        if style_scores:
            best_style = max(style_scores.keys(), key=lambda k: style_scores[k])
            if style_scores[best_style] >= 0.2:  # Lower threshold for style
                analysis_style = best_style
        
        return QueryIntent(
            domain_focus=domain_focus,
            analysis_style=analysis_style,
            confidence=domain_confidence,
            keywords_matched=domain_keywords
        )
    
    def _calculate_domain_score(self, query: str, patterns: Dict[str, List[str]]) -> float:
        """Calculate relevance score for a domain based on keyword matches."""
        total_words = len(query.split())
        if total_words == 0:
            return 0.0
        
        matched_words = 0
        phrase_bonus = 0.0
        
        # Check individual keywords
        for keyword in patterns["keywords"]:
            if keyword in query:
                matched_words += 1
        
        # Check phrases (worth more than individual keywords)
        for phrase in patterns["phrases"]:
            if phrase in query:
                phrase_bonus += 0.2  # Each phrase match adds significant weight
        
        # Calculate base score from keyword density
        keyword_score = matched_words / total_words
        
        # Add phrase bonus
        total_score = keyword_score + phrase_bonus
        
        return min(total_score, 1.0)  # Cap at 1.0
    
    def _get_matched_keywords(self, query: str, patterns: Dict[str, List[str]]) -> List[str]:
        """Get list of matched keywords for debugging/explanation."""
        matched = []
        
        for keyword in patterns["keywords"]:
            if keyword in query:
                matched.append(keyword)
        
        for phrase in patterns["phrases"]:
            if phrase in query:
                matched.append(phrase)
        
        return matched
    
    def select_prompt(self, query: str, schema_info: str, 
                     enable_maps: bool = False) -> Tuple[str, QueryIntent]:
        """
        Select and generate appropriate prompt for the given query.
        
        Args:
            query: User's natural language query
            schema_info: Database schema information
            enable_maps: Whether to enable map generation
            
        Returns:
            Tuple of (generated_prompt, query_intent)
        """
        intent = self.analyze_query(query)
        
        # Use pre-configured prompt variations for high-confidence matches
        if intent.confidence >= 0.5:
            if intent.domain_focus == "agricultural" and intent.analysis_style == "detailed":
                prompt = PromptVariations.agricultural_analyst(schema_info)
            elif intent.domain_focus == "climate" and intent.analysis_style == "executive":
                prompt = PromptVariations.policy_maker(schema_info)
            elif intent.domain_focus == "urban":
                prompt = PromptVariations.urban_planner(schema_info)
            elif intent.analysis_style == "detailed":
                prompt = PromptVariations.research_analyst(schema_info)
            else:
                # Use standard prompt with detected specializations
                prompt = get_system_prompt(
                    include_maps=enable_maps,
                    analysis_style=intent.analysis_style,
                    domain_focus=intent.domain_focus,
                    schema_info=schema_info
                )
        else:
            # Use standard prompt with any detected specializations
            prompt = get_system_prompt(
                include_maps=enable_maps,
                analysis_style=intent.analysis_style,
                domain_focus=intent.domain_focus,
                schema_info=schema_info
            )
        
        return prompt, intent
    
    def explain_selection(self, intent: QueryIntent) -> str:
        """
        Generate explanation of why a particular prompt was selected.
        
        Args:
            intent: The detected query intent
            
        Returns:
            Human-readable explanation
        """
        explanations = []
        
        if intent.domain_focus:
            explanations.append(f"Detected {intent.domain_focus} focus (confidence: {intent.confidence:.2f})")
            if intent.keywords_matched:
                explanations.append(f"Keywords: {', '.join(intent.keywords_matched[:3])}")
        
        if intent.analysis_style != "standard":
            explanations.append(f"Analysis style: {intent.analysis_style}")
        
        if not explanations:
            explanations.append("Using standard prompt")
        
        return " | ".join(explanations)


# Global instance for easy access
prompt_selector = PromptSelector()


def auto_select_prompt(query: str, schema_info: str, 
                      enable_maps: bool = False, 
                      debug: bool = False) -> str:
    """
    Convenience function for automatic prompt selection.
    
    Args:
        query: User's natural language query
        schema_info: Database schema information  
        enable_maps: Whether to enable map generation
        debug: Whether to print selection reasoning
        
    Returns:
        Generated system prompt
    """
    prompt, intent = prompt_selector.select_prompt(query, schema_info, enable_maps)
    
    if debug:
        explanation = prompt_selector.explain_selection(intent)
        print(f"[Prompt Selection] {explanation}")
    
    return prompt
