"""
Named Entity Recognition extras for extracting dates and action items from email text.

Uses dateparser for date extraction and rule-based heuristics for action items.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

import dateparser

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Common action verbs for task extraction
ACTION_VERBS = [
    'submit', 'register', 'attend', 'complete', 'finish', 'send', 'reply',
    'respond', 'schedule', 'book', 'reserve', 'confirm', 'cancel', 'update',
    'review', 'approve', 'reject', 'sign', 'upload', 'download', 'install',
    'configure', 'setup', 'test', 'verify', 'check', 'validate', 'create',
    'delete', 'modify', 'change', 'update', 'fix', 'resolve', 'implement',
    'develop', 'build', 'deploy', 'publish', 'share', 'forward', 'copy',
    'paste', 'print', 'save', 'backup', 'restore', 'migrate', 'upgrade',
    'downgrade', 'rollback', 'merge', 'split', 'combine', 'separate',
    'organize', 'sort', 'filter', 'search', 'find', 'locate', 'identify',
    'analyze', 'evaluate', 'assess', 'measure', 'calculate', 'compute',
    'process', 'handle', 'manage', 'administer', 'supervise', 'monitor',
    'track', 'follow', 'trace', 'investigate', 'research', 'study',
    'learn', 'understand', 'comprehend', 'explain', 'describe', 'document',
    'record', 'log', 'note', 'mention', 'refer', 'cite', 'quote',
    'reference', 'link', 'connect', 'associate', 'relate', 'correlate',
    'compare', 'contrast', 'differentiate', 'distinguish', 'separate',
    'categorize', 'classify', 'group', 'cluster', 'segment', 'partition',
    'divide', 'split', 'break', 'separate', 'isolate', 'extract',
    'remove', 'eliminate', 'exclude', 'include', 'add', 'insert',
    'append', 'prepend', 'attach', 'detach', 'link', 'unlink',
    'connect', 'disconnect', 'join', 'leave', 'enter', 'exit',
    'start', 'stop', 'begin', 'end', 'pause', 'resume', 'continue',
    'proceed', 'advance', 'progress', 'move', 'shift', 'transfer',
    'relocate', 'reposition', 'rearrange', 'reorganize', 'restructure',
    'reformat', 'redesign', 'rebuild', 'reconstruct', 'recreate',
    'reproduce', 'replicate', 'duplicate', 'clone', 'copy', 'paste'
]

# Date patterns to look for
DATE_PATTERNS = [
    r'\b(?:next|this|last)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|week|month|year)\b',
    r'\b(?:tomorrow|yesterday|today)\b',
    r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(?:st|nd|rd|th)?\b',
    r'\b\d{1,2}/(?:\d{1,2}|\d{4})\b',  # MM/DD or MM/DD/YYYY
    r'\b\d{1,2}-\d{1,2}-\d{2,4}\b',    # MM-DD-YY or MM-DD-YYYY
    r'\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b',
    r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\.?\s+\d{1,2}\b',
    r'\b\d{4}-\d{1,2}-\d{1,2}\b',      # YYYY-MM-DD
    r'\b(?:by|before|after|on|at)\s+(?:next|this|last)?\s*(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|week|month|year)\b',
    r'\b(?:by|before|after|on|at)\s+\d{1,2}(?:st|nd|rd|th)?\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)\b',
    r'\b(?:by|before|after|on|at)\s+\d{1,2}/\d{1,2}(?:/\d{2,4})?\b',
    r'\b(?:due|deadline)\s+(?:by|on|before)?\s*:?\s*(.+?)(?:\n|$)',  # "due by: ..." or "deadline: ..."
]


def extract_dates(text: str) -> List[Dict[str, Any]]:
    """
    Extract date-like phrases from text using multiple methods.
    
    Returns list of dictionaries with:
    - text: original text matched
    - parsed_date: parsed datetime object
    - confidence: confidence score (0-1)
    """
    if not text:
        return []
    
    dates = []
    text_lower = text.lower()
    
    # Method 1: Use dateparser on the entire text
    try:
        parsed = dateparser.parse(text, languages=['en'])
        if parsed:
            dates.append({
                'text': text[:100] + '...' if len(text) > 100 else text,
                'parsed_date': parsed,
                'confidence': 0.8,
                'method': 'dateparser_full'
            })
    except Exception as e:
        logger.debug(f"Dateparser full text failed: {e}")
    
    # Method 2: Look for date patterns
    for pattern in DATE_PATTERNS:
        try:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                matched_text = match.group(0)
                try:
                    parsed = dateparser.parse(matched_text, languages=['en'])
                    if parsed:
                        dates.append({
                            'text': matched_text,
                            'parsed_date': parsed,
                            'confidence': 0.9,
                            'method': 'pattern_match'
                        })
                except Exception as e:
                    logger.debug(f"Dateparser pattern match failed: {e}")
        except Exception as e:
            logger.debug(f"Pattern matching failed for {pattern}: {e}")
    
    # Method 3: Look for sentences containing date keywords
    sentences = re.split(r'[.!?]+', text)
    for sentence in sentences:
        if any(keyword in sentence.lower() for keyword in ['deadline', 'due', 'by', 'before', 'after', 'on', 'at']):
            try:
                parsed = dateparser.parse(sentence, languages=['en'])
                if parsed:
                    dates.append({
                        'text': sentence.strip(),
                        'parsed_date': parsed,
                        'confidence': 0.7,
                        'method': 'keyword_context'
                    })
            except Exception as e:
                logger.debug(f"Dateparser keyword context failed: {e}")
    
    # Remove duplicates and sort by confidence
    unique_dates = []
    seen_texts = set()
    
    for date in dates:
        if date['text'] not in seen_texts:
            unique_dates.append(date)
            seen_texts.add(date['text'])
    
    # Sort by confidence (highest first)
    unique_dates.sort(key=lambda x: x['confidence'], reverse=True)
    
    return unique_dates[:5]  # Return top 5 dates


def extract_action_items(text: str) -> List[Dict[str, Any]]:
    """
    Extract action items from text using rule-based heuristics.
    
    Returns list of dictionaries with:
    - text: original action item text
    - verb: detected action verb
    - confidence: confidence score (0-1)
    """
    if not text:
        return []
    
    action_items = []
    lines = text.split('\n')
    
    for line_num, line in enumerate(lines):
        line = line.strip()
        if not line or len(line) < 10:  # Skip very short lines
            continue
        
        # Look for lines that start with action verbs
        line_lower = line.lower()
        
        # Check if line starts with an action verb
        for verb in ACTION_VERBS:
            if line_lower.startswith(verb + ' ') or line_lower.startswith(verb + ':'):
                action_items.append({
                    'text': line,
                    'verb': verb,
                    'confidence': 0.9,
                    'line_number': line_num + 1,
                    'method': 'verb_start'
                })
                break
        
        # Look for bullet points with action verbs
        if line.startswith(('•', '-', '*', '1.', '2.', '3.', '4.', '5.')):
            for verb in ACTION_VERBS:
                if verb in line_lower:
                    action_items.append({
                        'text': line,
                        'verb': verb,
                        'confidence': 0.8,
                        'line_number': line_num + 1,
                        'method': 'bullet_verb'
                    })
                    break
        
        # Look for imperative sentences (commands)
        if line.endswith('.') and not line.startswith(('I', 'We', 'You', 'They', 'He', 'She', 'It')):
            for verb in ACTION_VERBS:
                if verb in line_lower:
                    action_items.append({
                        'text': line,
                        'verb': verb,
                        'confidence': 0.7,
                        'line_number': line_num + 1,
                        'method': 'imperative'
                    })
                    break
        
        # Look for "Please" + action verb
        if line_lower.startswith('please '):
            for verb in ACTION_VERBS:
                if verb in line_lower:
                    action_items.append({
                        'text': line,
                        'verb': verb,
                        'confidence': 0.8,
                        'line_number': line_num + 1,
                        'method': 'please_verb'
                    })
                    break
    
    # Remove duplicates and sort by confidence
    unique_actions = []
    seen_texts = set()
    
    for action in action_items:
        if action['text'] not in seen_texts:
            unique_actions.append(action)
            seen_texts.add(action['text'])
    
    # Sort by confidence (highest first)
    unique_actions.sort(key=lambda x: x['confidence'], reverse=True)
    
    return unique_actions[:10]  # Return top 10 action items


def extract_ner_data(text: str) -> Dict[str, Any]:
    """
    Extract both dates and action items from text.
    
    Returns dictionary with:
    - dates: list of extracted dates
    - action_items: list of extracted action items
    - summary: summary of findings
    """
    if not text:
        return {
            'dates': [],
            'action_items': [],
            'summary': 'No text provided'
        }
    
    try:
        dates = extract_dates(text)
        action_items = extract_action_items(text)
        
        # Create summary
        summary_parts = []
        if dates:
            summary_parts.append(f"Found {len(dates)} date(s)")
        if action_items:
            summary_parts.append(f"Found {len(action_items)} action item(s)")
        
        summary = '; '.join(summary_parts) if summary_parts else 'No dates or action items found'
        
        return {
            'dates': dates,
            'action_items': action_items,
            'summary': summary
        }
        
    except Exception as e:
        logger.error(f"Error extracting NER data: {e}")
        return {
            'dates': [],
            'action_items': [],
            'summary': f'Error: {str(e)}'
        }


def get_primary_deadline(dates: List[Dict[str, Any]]) -> Optional[datetime]:
    """
    Get the primary deadline from a list of extracted dates.
    
    Returns the most likely deadline date, or None if no dates found.
    """
    if not dates:
        return None
    
    # Filter out past dates
    now = datetime.now()
    future_dates = [d for d in dates if d['parsed_date'] > now]
    
    if not future_dates:
        return None
    
    # Return the date with highest confidence
    return max(future_dates, key=lambda x: x['confidence'])['parsed_date']
