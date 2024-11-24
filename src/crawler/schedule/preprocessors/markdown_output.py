"""
Markdown Output Preprocessor
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

class MarkdownOutputError(Exception):
    """Raised when there's an error writing Markdown output"""
    pass

def save_schedule_markdown(data: List[Dict[str, Any]], output_path: Union[str, Path]) -> List[Dict[str, Any]]:
    """Save schedule data as formatted Markdown"""
    try:
        output_path = Path(output_path)
        
        with output_path.open('w', encoding='utf-8') as f:
            f.write("# Class Schedule\n\n")
            f.write(f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
            
            if len(data) == 1 and isinstance(data[0], dict) and 'days' in data[0]:
                days = data[0]['days']
            else:
                days = data

            for day in days:
                if not isinstance(day, dict):
                    continue
                        
                date = day.get('date')
                date_str = date.strftime("%A, %B %d, %Y") if isinstance(date, datetime) else str(date)
                f.write(f"## {date_str}\n\n")
                    
                if lessons := day.get("lessons"):
                    f.write("### Lessons\n\n")
                    for lesson in lessons:
                        f.write(f"**Period {lesson.get('index', '')}**\n")
                        f.write(f"- Subject: {lesson.get('subject', '')}\n")
                        f.write(f"- Room: {lesson.get('room', '')}\n")
                        if topic := lesson.get('topic'):
                            f.write(f"- Topic: {topic}\n")
                            
                        if hw := lesson.get('homework'):
                            f.write("- Homework:\n")
                            if hw.get('text'):
                                f.write(f"  - {hw['text']}\n")
                            for attachment in hw.get('attachments', []):
                                filename = attachment['filename']
                                url = attachment['url']
                                f.write(f"  - 📎 [{filename}]({url})\n")
                            for link in hw.get('links', []):
                                url = link.get('destination_url') or link.get('original_url')
                                if not url:
                                    continue  # Skip links with no URL

                                # Ensure the URL starts with 'http://' or 'https://'
                                if not url.startswith(('http://', 'https://')):
                                    url = 'https://' + url

                                # Use the last part of the URL as the link text or 'Link' if empty
                                link_text = url.split('/')[-1] or 'Link'
                                f.write(f"  - 🔗 [{link_text}]({url})\n")
                                
                        if mark := lesson.get('mark'):
                            f.write(f"- Mark: {mark}\n")
                        f.write("\n")
                    
                if announcements := day.get("announcements"):
                    f.write("### Announcements\n\n")
                    for announcement in announcements:
                        if announcement.get('type') == 'behavior':
                            f.write(f"**{announcement.get('behavior_type', '')}**\n")
                            f.write(f"- Description: {announcement.get('description', '')}\n")
                            f.write(f"- Rating: {announcement.get('rating', '')}\n")
                            f.write(f"- Subject: {announcement.get('subject', '')}\n")
                        else:
                            f.write(f"- {announcement.get('text', '')}\n")
                        f.write("\n")
                                
                f.write("---\n\n")
                    
        return data
            
    except Exception as e:
        raise MarkdownOutputError(f"Failed to save Markdown output: {str(e)}")

def create_markdown_output_step(output_path: Union[str, Path]):
    """Create a pipeline step function with configured output path"""
    def markdown_output_step(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return save_schedule_markdown(data, output_path)
    return markdown_output_step
