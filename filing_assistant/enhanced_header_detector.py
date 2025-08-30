#!/usr/bin/env python3
"""
Enhanced Header Detection with OpenAI API Integration

This module implements a 5-strategy header detection system with OpenAI API
as the final judge to validate and improve header mappings over time.
"""

import json
import re
import os
from typing import Dict, List, Tuple, Optional, Any
from collections import Counter
import statistics
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None

class EnhancedHeaderDetector:
    """
    Advanced header detection system with 5 strategies including OpenAI validation.
    """
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """Initialize enhanced header detector with OpenAI integration."""
        
        # Get API key from environment or parameter
        self.openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        self.openai_client = None
        
        # Initialize OpenAI client with better error handling
        if OPENAI_AVAILABLE and self.openai_api_key:
            try:
                self.openai_client = OpenAI(api_key=self.openai_api_key)
                print("✅ OpenAI client initialized successfully!")
            except Exception as e:
                print(f"⚠️ Could not initialize OpenAI client: {e}")
                self.openai_client = None
        elif not self.openai_api_key:
            print("⚠️ OPENAI_API_KEY not found in environment variables")
        elif not OPENAI_AVAILABLE:
            print("⚠️ OpenAI package not available - install with: pip install openai")
        
        # Enhanced business domain keywords for better pattern detection
        self.business_keywords = {
            'logistics': ['lane', 'service', 'port', 'origin', 'destination', 'carrier', 'freight', 'shipment', 'transport', 'routing', 'mode', 'vessel'],
            'financial': ['cost', 'price', 'rate', 'fee', 'charge', 'amount', 'total', 'minimum', 'surcharge', 'currency', 'billing', 'payment', 'invoice'],
            'measurement': ['cbm', 'volume', 'weight', 'kilos', 'pounds', 'tons', 'cubic', 'meter', 'feet', 'dimensions', 'length', 'width', 'height'],
            'temporal': ['date', 'time', 'effective', 'expiration', 'valid', 'period', 'duration', 'schedule', 'start', 'end', 'from', 'to'],
            'identifiers': ['id', 'code', 'number', 'reference', 'tracking', 'lane_id', 'item', 'sku', 'part', 'model', 'serial'],
            'geographic': ['country', 'region', 'zone', 'area', 'location', 'address', 'city', 'state', 'continent', 'territory'],
            'business': ['quote', 'bid', 'proposal', 'contract', 'agreement', 'terms', 'conditions', 'client', 'customer', 'vendor', 'supplier'],
            'operational': ['status', 'type', 'category', 'class', 'grade', 'level', 'priority', 'urgency', 'requirements']
        }
        
        # Enhanced template patterns for detection
        self.template_patterns = [
            r'<<.*?>>',  # Template variables like <<axis(lane_id)>>
            r'\{\{.*?\}\}',  # Handlebars templates
            r'\$\{.*?\}',  # Variable substitutions
            r'axis\(',  # Axis function calls
            r'bid\|',  # Bid system markers
            r'template\.',  # Template references
            r'var\.',  # Variable references
        ]
        
        # Optimized thresholds based on analysis
        self.thresholds = {
            'pattern': 0.25,      # Reduced for better sensitivity
            'structure': 0.20,    # More aggressive detection
            'template': 0.15,     # Lower threshold for template recognition
            'historical': 0.10,   # Learning-based threshold
            'openai': 0.60       # High confidence for AI validation
        }
        
        # Strategy weights for composite scoring
        self.weights = {
            'pattern': 0.25,
            'structure': 0.20,
            'template': 0.15,
            'historical': 0.10,
            'openai': 0.30  # Highest weight for AI validation
        }
        
        # Load historical decisions for learning
        self.decision_history = self.load_decision_history()
    
    def load_decision_history(self) -> Dict[str, Any]:
        """Load previous OpenAI decisions for learning."""
        history_file = "openai_header_decisions.json"
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Could not load decision history: {e}")
        
        return {
            "metadata": {
                "created": datetime.now().isoformat(),
                "total_decisions": 0,
                "accuracy_feedback": {}
            },
            "decisions": {},
            "learning_patterns": {}
        }
    
    def save_decision_history(self):
        """Save decision history for future learning."""
        history_file = "openai_header_decisions.json"
        try:
            with open(history_file, 'w') as f:
                json.dump(self.decision_history, f, indent=2)
        except Exception as e:
            print(f"⚠️  Could not save decision history: {e}")
    
    def strategy_1_pattern_based(self, sheet_data: Dict[str, Any]) -> List[Tuple[int, float, Dict[str, Any]]]:
        """Strategy 1: Pattern-based detection using business keywords."""
        column_count = len(sheet_data.get('columns', []))
        data_rows = sheet_data.get('data', [])
        candidates = []
        
        for row_idx in range(min(50, len(data_rows))):
            row = data_rows[row_idx]
            score = 0.0
            analysis = {'strategy': 'pattern_based', 'details': {}}
            
            values = []
            for i in range(column_count):
                val = str(row.get(f'col_{i}', '')).strip()
                if val and val.lower() != 'nan':
                    values.append(val)
            
            if len(values) < 3:
                continue
            
            # Check for business keywords
            keyword_matches = 0
            for value in values:
                value_lower = value.lower()
                for category, keywords in self.business_keywords.items():
                    if any(keyword in value_lower for keyword in keywords):
                        keyword_matches += 1
                        break
            
            score += (keyword_matches / len(values)) * 40
            analysis['details']['keyword_matches'] = keyword_matches
            analysis['details']['keyword_ratio'] = keyword_matches / len(values)
            
            if score > 15:  # Threshold for pattern-based detection
                candidates.append((row_idx, score, analysis))
        
        return sorted(candidates, key=lambda x: x[1], reverse=True)
    
    def strategy_2_structural_analysis(self, sheet_data: Dict[str, Any]) -> List[Tuple[int, float, Dict[str, Any]]]:
        """Strategy 2: Structural analysis of data patterns."""
        column_count = len(sheet_data.get('columns', []))
        data_rows = sheet_data.get('data', [])
        candidates = []
        
        for row_idx in range(min(50, len(data_rows))):
            row = data_rows[row_idx]
            score = 0.0
            analysis = {'strategy': 'structural', 'details': {}}
            
            values = []
            for i in range(column_count):
                val = str(row.get(f'col_{i}', '')).strip()
                if val and val.lower() != 'nan':
                    values.append(val)
            
            if len(values) < 3:
                continue
            
            # Coverage score
            coverage = len(values) / column_count
            score += coverage * 30
            
            # Unique values (headers should be unique)
            uniqueness = len(set(values)) / len(values)
            score += uniqueness * 25
            
            # Underscore naming convention
            underscore_ratio = sum(1 for v in values if '_' in v) / len(values)
            score += underscore_ratio * 20
            
            # Length analysis (headers typically 3-25 chars)
            avg_length = statistics.mean([len(v) for v in values])
            if 3 <= avg_length <= 25:
                score += 15
            
            analysis['details'] = {
                'coverage': coverage,
                'uniqueness': uniqueness,
                'underscore_ratio': underscore_ratio,
                'avg_length': avg_length
            }
            
            if score > 20:  # Threshold for structural analysis
                candidates.append((row_idx, score, analysis))
        
        return sorted(candidates, key=lambda x: x[1], reverse=True)
    
    def strategy_3_template_pattern(self, sheet_data: Dict[str, Any]) -> List[Tuple[int, float, Dict[str, Any]]]:
        """Strategy 3: Template pattern recognition."""
        column_count = len(sheet_data.get('columns', []))
        data_rows = sheet_data.get('data', [])
        candidates = []
        
        for row_idx in range(min(50, len(data_rows))):
            row = data_rows[row_idx]
            score = 0.0
            analysis = {'strategy': 'template_pattern', 'details': {}}
            
            values = []
            template_matches = 0
            
            for i in range(column_count):
                val = str(row.get(f'col_{i}', '')).strip()
                if val and val.lower() != 'nan':
                    values.append(val)
                    
                    # Check for template patterns
                    for pattern in self.template_patterns:
                        if re.search(pattern, val):
                            template_matches += 1
                            break
            
            if len(values) < 3:
                continue
            
            template_ratio = template_matches / len(values)
            score = template_ratio * 50  # High weight for template patterns
            
            analysis['details'] = {
                'template_matches': template_matches,
                'template_ratio': template_ratio,
                'total_values': len(values)
            }
            
            if score > 10:  # Threshold for template patterns
                candidates.append((row_idx, score, analysis))
        
        return sorted(candidates, key=lambda x: x[1], reverse=True)
    
    def strategy_4_historical_learning(self, sheet_data: Dict[str, Any], file_name: str) -> List[Tuple[int, float, Dict[str, Any]]]:
        """Strategy 4: Learn from historical OpenAI decisions."""
        column_count = len(sheet_data.get('columns', []))
        data_rows = sheet_data.get('data', [])
        candidates = []
        
        # Extract patterns from decision history with safe defaults
        learning_patterns = self.decision_history.get('learning_patterns', {
            'positive_indicators': [],
            'negative_indicators': [],
            'common_mappings': {}
        })
        
        # Ensure required keys exist
        if 'positive_indicators' not in learning_patterns:
            learning_patterns['positive_indicators'] = []
        if 'negative_indicators' not in learning_patterns:
            learning_patterns['negative_indicators'] = []
        
        for row_idx in range(min(50, len(data_rows))):
            row = data_rows[row_idx]
            score = 0.0
            analysis = {'strategy': 'historical_learning', 'details': {}}
            
            values = []
            for i in range(column_count):
                val = str(row.get(f'col_{i}', '')).strip()
                if val and val.lower() != 'nan':
                    values.append(val)
            
            if len(values) < 3:
                continue
            
            # Apply learned patterns
            pattern_matches = 0
            for value in values:
                value_clean = self.clean_header_name(value)
                
                # Check against learned positive patterns
                for pattern in learning_patterns.get('positive_indicators', []):
                    if pattern.lower() in value_clean.lower():
                        pattern_matches += 1
                        break
                
                # Check against learned negative patterns
                for pattern in learning_patterns.get('negative_indicators', []):
                    if pattern.lower() in value_clean.lower():
                        pattern_matches -= 0.5  # Penalty for negative patterns
            
            if pattern_matches > 0:
                score = (pattern_matches / len(values)) * 30
                
                analysis['details'] = {
                    'pattern_matches': pattern_matches,
                    'learned_patterns_applied': len(learning_patterns.get('positive_indicators', []))
                }
                
                candidates.append((row_idx, score, analysis))
        
        return sorted(candidates, key=lambda x: x[1], reverse=True)
    
    def strategy_5_openai_validation(self, sheet_data: Dict[str, Any], file_name: str, 
                                   candidate_mappings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Strategy 5: Use OpenAI API as final judge and learning source."""
        
        if not self.openai_client:
            print("⚠️  OpenAI client not available, skipping AI validation")
            return {"validated_mapping": {}, "confidence": 0.0, "reasoning": "No OpenAI client"}
        
        # Prepare context for OpenAI
        context = self.prepare_openai_context(sheet_data, file_name, candidate_mappings)
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert data analyst specializing in business document header detection. 
                        Your task is to evaluate proposed header mappings for spreadsheet data and provide the best possible mapping.
                        
                        Focus on:
                        1. Business logic and semantic meaning
                        2. Consistency with logistics/financial domain
                        3. Header naming conventions
                        4. Data type alignment
                        
                        Respond with a JSON object containing:
                        - validated_mapping: {col_X: cleaned_header_name}
                        - confidence: float (0.0-1.0)
                        - reasoning: string explaining your decisions
                        - improvements: list of suggested improvements
                        """
                    },
                    {
                        "role": "user",
                        "content": context
                    }
                ],
                temperature=0.1,  # Low temperature for consistent results
                max_tokens=2000
            )
            
            # Parse OpenAI response
            ai_result = self.parse_openai_response(response.choices[0].message.content)
            
            # Record decision for learning
            self.record_openai_decision(file_name, context, ai_result)
            
            return ai_result
            
        except Exception as e:
            print(f"❌ OpenAI API error: {e}")
            return {"validated_mapping": {}, "confidence": 0.0, "reasoning": f"API Error: {e}"}
    
    def prepare_openai_context(self, sheet_data: Dict[str, Any], file_name: str, 
                              candidates: List[Dict[str, Any]]) -> str:
        """Prepare context for OpenAI analysis."""
        
        context = f"""
File: {file_name}
Sheet: {list(sheet_data.keys())[0] if sheet_data else 'Unknown'}

DETECTION CANDIDATES:
"""
        
        for i, candidate in enumerate(candidates[:3]):  # Top 3 candidates
            context += f"\nCandidate {i+1} (Row {candidate.get('row_index', 'Unknown')}):\n"
            mapping = candidate.get('detected_headers', {})
            
            for col, header in list(mapping.items())[:10]:  # First 10 headers
                context += f"  {col} -> '{header}'\n"
            
            if len(mapping) > 10:
                context += f"  ... and {len(mapping) - 10} more headers\n"
        
        context += f"""

SAMPLE DATA (first 3 rows):
"""
        
        # Add sample data for context
        data_rows = sheet_data.get('data', [])
        for row_idx in range(min(3, len(data_rows))):
            context += f"\nRow {row_idx}:\n"
            row = data_rows[row_idx]
            for i in range(min(10, len(sheet_data.get('columns', [])))):
                val = str(row.get(f'col_{i}', '')).strip()
                if val:
                    context += f"  col_{i}: '{val}'\n"
        
        context += """

TASK: Evaluate the candidates and provide the BEST header mapping. Consider:
1. Business domain appropriateness (logistics, shipping, finance)
2. Header naming consistency and clarity
3. Semantic meaning alignment with data
4. Standard industry terminology

Please provide your analysis in JSON format.
"""
        
        return context
    
    def parse_openai_response(self, response_text: str) -> Dict[str, Any]:
        """Parse OpenAI response into structured data."""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
            else:
                # Fallback parsing
                return {
                    "validated_mapping": {},
                    "confidence": 0.5,
                    "reasoning": response_text,
                    "improvements": []
                }
        except Exception as e:
            return {
                "validated_mapping": {},
                "confidence": 0.0,
                "reasoning": f"Parsing error: {e}",
                "improvements": []
            }
    
    def record_openai_decision(self, file_name: str, context: str, ai_result: Dict[str, Any]):
        """Record OpenAI decision for future learning."""
        decision_id = f"{file_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.decision_history["decisions"][decision_id] = {
            "timestamp": datetime.now().isoformat(),
            "file_name": file_name,
            "context": context[:1000],  # Truncate for storage
            "ai_result": ai_result,
            "confidence": ai_result.get("confidence", 0.0)
        }
        
        self.decision_history["metadata"]["total_decisions"] += 1
        
        # Extract learning patterns
        self.update_learning_patterns(ai_result)
        
        # Save updated history
        self.save_decision_history()
    
    def update_learning_patterns(self, ai_result: Dict[str, Any]):
        """Update learning patterns based on OpenAI decisions."""
        learning_patterns = self.decision_history.setdefault("learning_patterns", {
            "positive_indicators": [],
            "negative_indicators": [],
            "common_mappings": {}
        })
        
        validated_mapping = ai_result.get("validated_mapping", {})
        
        # Extract positive patterns from validated headers
        for col, header in validated_mapping.items():
            if header and len(header) > 2:
                # Add header components as positive indicators
                header_parts = header.replace('_', ' ').split()
                for part in header_parts:
                    if len(part) > 2 and part not in learning_patterns["positive_indicators"]:
                        learning_patterns["positive_indicators"].append(part)
        
        # Limit pattern lists to prevent memory bloat
        learning_patterns["positive_indicators"] = learning_patterns["positive_indicators"][-100:]
        learning_patterns["negative_indicators"] = learning_patterns["negative_indicators"][-50:]
    
    def detect_headers_enhanced(self, sheet_data: Dict[str, Any], file_name: str) -> Dict[str, Any]:
        """
        Run all 5 detection strategies and return the best result.
        """
        print(f"🔍 Running enhanced header detection for {file_name}")
        
        # Strategy 1: Pattern-based detection
        strategy1_results = self.strategy_1_pattern_based(sheet_data)
        
        # Strategy 2: Structural analysis
        strategy2_results = self.strategy_2_structural_analysis(sheet_data)
        
        # Strategy 3: Template pattern recognition
        strategy3_results = self.strategy_3_template_pattern(sheet_data)
        
        # Strategy 4: Historical learning
        strategy4_results = self.strategy_4_historical_learning(sheet_data, file_name)
        
        # Combine and rank all candidates
        all_candidates = []
        
        for row_idx, score, analysis in strategy1_results[:2]:
            headers = self.extract_clean_headers(sheet_data, row_idx)
            all_candidates.append({
                "row_index": row_idx,
                "score": score,
                "strategy": "pattern_based",
                "analysis": analysis,
                "detected_headers": headers
            })
        
        for row_idx, score, analysis in strategy2_results[:2]:
            headers = self.extract_clean_headers(sheet_data, row_idx)
            all_candidates.append({
                "row_index": row_idx,
                "score": score,
                "strategy": "structural",
                "analysis": analysis,
                "detected_headers": headers
            })
        
        for row_idx, score, analysis in strategy3_results[:1]:
            headers = self.extract_clean_headers(sheet_data, row_idx)
            all_candidates.append({
                "row_index": row_idx,
                "score": score,
                "strategy": "template_pattern",
                "analysis": analysis,
                "detected_headers": headers
            })
        
        for row_idx, score, analysis in strategy4_results[:1]:
            headers = self.extract_clean_headers(sheet_data, row_idx)
            all_candidates.append({
                "row_index": row_idx,
                "score": score,
                "strategy": "historical_learning",
                "analysis": analysis,
                "detected_headers": headers
            })
        
        # Remove duplicates based on row_index
        unique_candidates = []
        seen_rows = set()
        for candidate in sorted(all_candidates, key=lambda x: x["score"], reverse=True):
            if candidate["row_index"] not in seen_rows:
                unique_candidates.append(candidate)
                seen_rows.add(candidate["row_index"])
        
        # Strategy 5: OpenAI validation
        openai_result = self.strategy_5_openai_validation(sheet_data, file_name, unique_candidates[:3])
        
        # Return comprehensive result
        return {
            "file_name": file_name,
            "strategy_results": {
                "pattern_based": len(strategy1_results),
                "structural": len(strategy2_results),
                "template_pattern": len(strategy3_results),
                "historical_learning": len(strategy4_results)
            },
            "candidates": unique_candidates[:5],
            "openai_validation": openai_result,
            "final_mapping": openai_result.get("validated_mapping", {}),
            "confidence": openai_result.get("confidence", 0.0)
        }
    
    def extract_clean_headers(self, sheet_data: Dict[str, Any], row_idx: int) -> Dict[str, str]:
        """Extract and clean headers from a specific row."""
        if row_idx >= len(sheet_data.get('data', [])):
            return {}
        
        header_row = sheet_data['data'][row_idx]
        column_count = len(sheet_data.get('columns', []))
        
        headers = {}
        for i in range(column_count):
            raw_header = str(header_row.get(f'col_{i}', '')).strip()
            if raw_header and raw_header.lower() != 'nan':
                cleaned = self.clean_header_name(raw_header)
                if cleaned:
                    headers[f'col_{i}'] = cleaned
        
        return headers
    
    def clean_header_name(self, raw_header: str) -> str:
        """Clean and normalize a raw header value."""
        # Remove template markers
        cleaned = raw_header
        for pattern in self.template_patterns:
            cleaned = re.sub(pattern, '', cleaned)
        
        # Remove common prefixes/suffixes
        cleaned = re.sub(r'^(axis|bid|itemType|predefinedAlternativeBid)[:|\|]', '', cleaned)
        cleaned = re.sub(r'\|.*$', '', cleaned)
        
        # Clean up parentheses and brackets
        cleaned = re.sub(r'[(){}\[\]]', '', cleaned)
        
        # Normalize whitespace and underscores
        cleaned = re.sub(r'\s+', '_', cleaned.strip())
        cleaned = re.sub(r'_+', '_', cleaned)
        cleaned = cleaned.strip('_').lower()
        
        return cleaned if len(cleaned) > 0 else ''


def demo_enhanced_detection():
    """Demonstrate the enhanced 5-strategy detection system."""
    
    print("🚀 ENHANCED HEADER DETECTION WITH OPENAI VALIDATION")
    print("=" * 60)
    
    # Initialize detector (will work with or without OpenAI API key)
    detector = EnhancedHeaderDetector()
    
    # Test file
    test_file = "training_files2/(AppliedMat) External CPT Empty_structured.json"
    
    try:
        with open(test_file, 'r') as f:
            data = json.load(f)
        
        # Test on first sheet with generic headers
        for sheet_name, sheet_data in data.items():
            if 'columns' in sheet_data:
                columns = sheet_data['columns']
                has_generic = any(re.match(r'^col_\d+$', col) for col in columns)
                
                if has_generic:
                    print(f"\n📋 Testing on sheet: {sheet_name}")
                    print(f"📊 Columns: {len(columns)}, Rows: {len(sheet_data.get('data', []))}")
                    
                    result = detector.detect_headers_enhanced(sheet_data, test_file)
                    
                    print(f"\n🎯 DETECTION RESULTS:")
                    print(f"   Strategy Results: {result['strategy_results']}")
                    print(f"   Candidates Found: {len(result['candidates'])}")
                    print(f"   OpenAI Confidence: {result['confidence']}")
                    
                    if result['final_mapping']:
                        print(f"   Final Headers ({len(result['final_mapping'])}):")
                        for col, header in list(result['final_mapping'].items())[:5]:
                            print(f"     {col} → '{header}'")
                        if len(result['final_mapping']) > 5:
                            print(f"     ... and {len(result['final_mapping']) - 5} more")
                    
                    break
    
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    demo_enhanced_detection()
