import json
import os
from datetime import datetime, timezone
from collections import defaultdict
from typing import Dict, List, Any
from app.config import settings
from app.logging import get_logger

logger = get_logger()

class GlobalTagManager:
    """
    Manages a global dictionary of tags and terminology from all processed videos
    to enhance correction accuracy across the entire corpus.
    """
    
    def __init__(self, metadata_dir=None):
        self.metadata_dir = metadata_dir or settings.TSTBTC_METADATA_DIR or "metadata/"
        self.dict_file = os.path.join(self.metadata_dir, "global_tag_dictionary.json")
        self.tag_dict = self._load_dictionary()
    
    def _load_dictionary(self) -> Dict[str, Any]:
        """Load existing global tag dictionary or create new one"""
        if os.path.exists(self.dict_file):
            try:
                with open(self.dict_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load global tag dictionary: {e}. Creating new one.")
        
        return self._create_new_dictionary()
    
    def _create_new_dictionary(self) -> Dict[str, Any]:
        """Create a new global tag dictionary structure"""
        return {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "version": "1.0",
            "tags": {},
            "technical_terms": [],  # Will be populated dynamically from video content
            "speaker_context": {
                "common_speakers": [],
                "expertise_areas": []
            },
            "project_names": [],  # Will be populated dynamically from video content
            "categories": {},  # Track category frequencies
            "video_count": 0,  # Track how many videos have been processed
            "common_words": {}  # Track frequently occurring words to identify technical terms
        }
    
    def _save_dictionary(self):
        """Save the global tag dictionary to file"""
        try:
            os.makedirs(os.path.dirname(self.dict_file), exist_ok=True)
            self.tag_dict["last_updated"] = datetime.now(timezone.utc).isoformat()
            
            with open(self.dict_file, 'w', encoding='utf-8') as f:
                json.dump(self.tag_dict, f, indent=4, ensure_ascii=False)
            
            logger.debug(f"Global tag dictionary saved to {self.dict_file}")
        except IOError as e:
            logger.error(f"Failed to save global tag dictionary: {e}")
    
    def update_from_transcript(self, transcript):
        """Update global dictionary with new transcript's metadata"""
        try:
            metadata = transcript.source.to_json()
            
            # Extract all tag sources
            manual_tags = metadata.get('tags', [])
            youtube_metadata = metadata.get('youtube', {})
            youtube_tags = youtube_metadata.get('tags', []) if youtube_metadata else []
            categories = metadata.get('categories', [])
            speakers = metadata.get('speakers', [])
            title = metadata.get('title', '')
            description = youtube_metadata.get('description', '') if youtube_metadata else ''
            
            # Increment video count
            self.tag_dict["video_count"] = self.tag_dict.get("video_count", 0) + 1
            
            # Combine all tags
            all_tags = manual_tags + youtube_tags + categories
            
            # Update tag frequencies and variations
            for tag in all_tags:
                if tag and isinstance(tag, str):
                    self._update_tag_entry(tag.strip())
            
            # Update categories tracking
            for category in categories:
                if category and isinstance(category, str):
                    self._update_category_frequency(category.strip())
            
            # Dynamically extract technical terms from title and description
            text_content = f"{title} {description}".lower()
            self._extract_technical_terms_dynamically(text_content, all_tags)
            
            # Update speaker context
            for speaker in speakers:
                if speaker and isinstance(speaker, str):
                    self._update_speaker_context(speaker.strip())
            
            # Dynamically identify project names from content
            self._identify_project_names_dynamically(text_content, all_tags)
            
            # Extract expertise areas from categories and tags
            self._update_expertise_areas(categories + all_tags)
            
            self._save_dictionary()
            logger.info(f"Updated global tag dictionary with transcript: {title}")
            
        except Exception as e:
            logger.error(f"Failed to update global tag dictionary: {e}")
    
    def _update_tag_entry(self, tag: str):
        """Update or create entry for a tag in the dictionary"""
        tag_lower = tag.lower()
        tags_dict = self.tag_dict["tags"]
        
        if tag_lower in tags_dict:
            # Update existing tag
            tags_dict[tag_lower]["frequency"] += 1
            tags_dict[tag_lower]["last_seen"] = datetime.now(timezone.utc).isoformat()
            
            # Add variation if not already present
            if tag not in tags_dict[tag_lower]["variations"]:
                tags_dict[tag_lower]["variations"].append(tag)
        else:
            # Create new tag entry
            tags_dict[tag_lower] = {
                "frequency": 1,
                "variations": [tag],
                "context": self._infer_context(tag_lower),
                "first_seen": datetime.now(timezone.utc).isoformat(),
                "last_seen": datetime.now(timezone.utc).isoformat()
            }
    
    def _update_speaker_context(self, speaker: str):
        """Update speaker information in the global context"""
        speaker_context = self.tag_dict["speaker_context"]
        if speaker not in speaker_context["common_speakers"]:
            speaker_context["common_speakers"].append(speaker)
            # Keep only the most recent 50 speakers to avoid bloat
            if len(speaker_context["common_speakers"]) > 50:
                speaker_context["common_speakers"] = speaker_context["common_speakers"][-50:]
    
    def _update_category_frequency(self, category: str):
        """Track category frequencies"""
        categories_dict = self.tag_dict.get("categories", {})
        category_lower = category.lower()
        categories_dict[category_lower] = categories_dict.get(category_lower, 0) + 1
        self.tag_dict["categories"] = categories_dict
    
    def _extract_technical_terms_dynamically(self, text_content: str, tags: List[str]):
        """Dynamically extract technical terms from content and tags"""
        technical_terms = self.tag_dict.get("technical_terms", [])
        
        # Look for bitcoin/blockchain related terms in tags
        bitcoin_indicators = ['bitcoin', 'btc', 'blockchain', 'crypto', 'lightning', 'ln']
        is_bitcoin_content = any(indicator in text_content or 
                               any(indicator in tag.lower() for tag in tags) 
                               for indicator in bitcoin_indicators)
        
        if is_bitcoin_content:
            # Extract potential technical terms from tags (longer, technical-sounding ones)
            for tag in tags:
                if tag and len(tag) > 3 and not tag.isdigit():
                    tag_lower = tag.lower()
                    # Add if it contains technical indicators or is already a known pattern
                    technical_indicators = ['network', 'protocol', 'script', 'sig', 'key', 'hash', 
                                          'node', 'chain', 'block', 'tx', 'vault', 'channel']
                    if (any(indicator in tag_lower for indicator in technical_indicators) or
                        tag_lower.startswith(('op_', 'bip', 'bolt')) or
                        tag_lower in ['taproot', 'segwit', 'multisig', 'htlc']):
                        if tag_lower not in technical_terms:
                            technical_terms.append(tag_lower)
        
        self.tag_dict["technical_terms"] = technical_terms
    
    def _identify_project_names_dynamically(self, text_content: str, tags: List[str]):
        """Dynamically identify project names from content and tags"""
        project_names = self.tag_dict.get("project_names", [])
        
        # Look for capitalized multi-word terms that might be project names
        import re
        
        # Common project patterns in tags
        for tag in tags:
            if tag and len(tag) > 2:
                # If tag has specific patterns that suggest it's a project name
                if (tag[0].isupper() or  # Starts with capital
                    'core' in tag.lower() or 'lightning' in tag.lower() or
                    any(pattern in tag.lower() for pattern in ['btc', 'lightning', 'wallet', 'pay'])):
                    if tag not in project_names:
                        project_names.append(tag)
        
        self.tag_dict["project_names"] = project_names
    
    def _update_expertise_areas(self, tags_and_categories: List[str]):
        """Update expertise areas based on categories and tags"""
        expertise_areas = self.tag_dict.get("speaker_context", {}).get("expertise_areas", [])
        
        # Map tags/categories to expertise areas
        expertise_mapping = {
            'development': ['development', 'dev', 'programming', 'coding', 'technical'],
            'podcast': ['podcast', 'interview', 'discussion'],
            'conference': ['conference', 'talk', 'presentation', 'summit'],
            'education': ['education', 'tutorial', 'learning', 'teaching'],
            'mining': ['mining', 'miner', 'hashrate', 'pool'],
            'security': ['security', 'privacy', 'cryptography', 'audit'],
            'payments': ['payments', 'lightning', 'channel', 'transaction'],
            'trading': ['trading', 'exchange', 'market', 'price']
        }
        
        for item in tags_and_categories:
            if item and isinstance(item, str):
                item_lower = item.lower()
                for area, keywords in expertise_mapping.items():
                    if any(keyword in item_lower for keyword in keywords):
                        if area not in expertise_areas:
                            expertise_areas.append(area)
        
        speaker_context = self.tag_dict.get("speaker_context", {})
        speaker_context["expertise_areas"] = expertise_areas
        self.tag_dict["speaker_context"] = speaker_context
    
    def _infer_context(self, tag: str) -> str:
        """Infer context category for a tag"""
        development_terms = ["script", "bdk", "core", "node", "api", "rpc", "development"]
        payment_terms = ["lightning", "payment", "channel", "invoice", "bolt"]
        security_terms = ["multisig", "signature", "key", "seed", "private", "security"]
        mining_terms = ["mining", "hash", "difficulty", "block", "pow"]
        
        if any(term in tag for term in development_terms):
            return "development"
        elif any(term in tag for term in payment_terms):
            return "payments"
        elif any(term in tag for term in security_terms):
            return "security"
        elif any(term in tag for term in mining_terms):
            return "mining"
        else:
            return "general"
    
    def get_correction_context(self) -> Dict[str, Any]:
        """Get enriched context for correction prompts"""
        tags_dict = self.tag_dict.get("tags", {})
        
        # Get most frequent tags
        frequent_tags = sorted(
            tags_dict.items(), 
            key=lambda x: x[1]["frequency"], 
            reverse=True
        )[:30]
        
        # Get most common categories
        categories_dict = self.tag_dict.get("categories", {})
        common_categories = sorted(
            categories_dict.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            'frequent_tags': [tag for tag, _ in frequent_tags],
            'tag_variations': self._get_tag_variations(),
            'technical_terms': self.tag_dict.get('technical_terms', []),
            'project_names': self.tag_dict.get('project_names', []),
            'common_speakers': self.tag_dict.get('speaker_context', {}).get('common_speakers', [])[:20],
            'common_categories': [cat for cat, _ in common_categories],
            'expertise_areas': self.tag_dict.get('speaker_context', {}).get('expertise_areas', []),
            'domain_context': self._build_domain_context(),
            'video_count': self.tag_dict.get('video_count', 0)
        }
    
    def _get_tag_variations(self) -> Dict[str, List[str]]:
        """Get mapping of tags to their variations"""
        variations = {}
        for tag, data in self.tag_dict.get("tags", {}).items():
            if len(data["variations"]) > 1:
                variations[tag] = data["variations"]
        return variations
    
    def _build_domain_context(self) -> str:
        """Build a domain context string for correction prompts based on actual data"""
        context_parts = []
        
        # Use expertise areas and categories to build context
        expertise_areas = self.tag_dict.get("speaker_context", {}).get("expertise_areas", [])
        categories = self.tag_dict.get("categories", {})
        
        # Get most common categories
        if categories:
            top_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:3]
            for category, _ in top_categories:
                if category in ["development", "technical"]:
                    context_parts.append("Bitcoin development and technical implementation")
                elif category in ["education", "tutorial"]:
                    context_parts.append("Bitcoin education and learning")
                elif category in ["podcast", "interview"]:
                    context_parts.append("Bitcoin discussion and interviews")
                elif category in ["conference", "presentation"]:
                    context_parts.append("Bitcoin conferences and presentations")
        
        # Add expertise areas
        for area in expertise_areas[:3]:
            if area == "payments" and "payment" not in " ".join(context_parts).lower():
                context_parts.append("Bitcoin payments and Lightning Network")
            elif area == "security" and "security" not in " ".join(context_parts).lower():
                context_parts.append("Bitcoin security and cryptography")
            elif area == "mining" and "mining" not in " ".join(context_parts).lower():
                context_parts.append("Bitcoin mining and network")
        
        return ", ".join(context_parts) or "Bitcoin and blockchain technology"
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the global tag dictionary"""
        tags_dict = self.tag_dict.get("tags", {})
        categories_dict = self.tag_dict.get("categories", {})
        
        return {
            "videos_processed": self.tag_dict.get("video_count", 0),
            "total_unique_tags": len(tags_dict),
            "total_tag_occurrences": sum(data["frequency"] for data in tags_dict.values()),
            "technical_terms_count": len(self.tag_dict.get("technical_terms", [])),
            "project_names_count": len(self.tag_dict.get("project_names", [])),
            "speakers_count": len(self.tag_dict.get("speaker_context", {}).get("common_speakers", [])),
            "categories_count": len(categories_dict),
            "expertise_areas_count": len(self.tag_dict.get("speaker_context", {}).get("expertise_areas", [])),
            "last_updated": self.tag_dict.get("last_updated"),
            "most_frequent_tags": sorted(
                tags_dict.items(), 
                key=lambda x: x[1]["frequency"], 
                reverse=True
            )[:10],
            "most_common_categories": sorted(
                categories_dict.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5] if categories_dict else []
        }