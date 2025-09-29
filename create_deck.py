import argparse
import json
import os
import sys
import uuid

from googleapiclient.discovery import build
from google.auth import default
from googleapiclient.errors import HttpError

from agents.base_agent import BaseAgent


def replace_page_object_ids(data, old, new):
    """Replace page object IDs in the request data."""
    for request in data.get("requests", []):
        if "replaceAllText" in request:
            if "pageObjectIds" in request["replaceAllText"]:
                request["replaceAllText"]["pageObjectIds"] = [new]
    return data


def main():
    parser = argparse.ArgumentParser(description="Create a presentation deck from a concept")
    parser.add_argument("--presentation-id", 
                       default="1kKzgzXhb4cc_Dn7z1lxui8sIfCan4xqs_Y-xHgzU0vk",
                       help="Source Google Slides presentation ID to copy from")
    parser.add_argument("--concept", 
                       required=True,
                       help="Creative concept for the deck (or path to text file containing concept)")
    parser.add_argument("--output-title", 
                       default="Generated Presentation",
                       help="Title for the new presentation")
    parser.add_argument("--config-file", 
                       default="config_files/deck_creative.yaml",
                       help="Path to deck creative config file")
    parser.add_argument("--schema-path", 
                       default="config_files/deck_schema.yaml",
                       help="Path to deck schema file")
    parser.add_argument("--templates-dir", 
                       default="slide_templates",
                       help="Directory containing slide templates")
    parser.add_argument("--llm", 
                       default="gemini",
                       choices=["openai", "gemini"],
                       help="LLM provider to use (default: gemini)")
    parser.add_argument("--model", 
                       help="Specific model to use for the LLM provider")
    parser.add_argument("--openai-api-key",
                       help="OpenAI API key (can also be set via OPENAI_API_KEY env var)")
    parser.add_argument("--gemini-api-key",
                       help="Gemini API key (can also be set via GEMINI_API_KEY env var)")
    
    args = parser.parse_args()
    
    # Set API keys from arguments if provided
    if args.openai_api_key:
        os.environ["OPENAI_API_KEY"] = args.openai_api_key
    if args.gemini_api_key:
        os.environ["GEMINI_API_KEY"] = args.gemini_api_key
    
    # Read concept from file if it's a path, otherwise use as string
    concept = args.concept
    if os.path.isfile(args.concept):
        with open(args.concept, 'r', encoding='utf-8') as f:
            concept = f.read()
    
    # Initialize Google services
    try:
        creds, _ = default()
        slides_service = build("slides", "v1", credentials=creds)
        drive_service = build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"Error initializing Google services: {e}")
        sys.exit(1)
    
    # Initialize deck creative agent
    agent_kwargs = {
        "config_file": args.config_file,
        "llm": args.llm,
        "schema_path": args.schema_path
    }
    if args.model:
        agent_kwargs["model"] = args.model
        
    try:
        deck_creative = BaseAgent(**agent_kwargs)
    except Exception as e:
        print(f"Error initializing agent: {e}")
        sys.exit(1)
    
    # Generate deck structure
    print("Generating deck structure...")
    try:
        deck_structure = deck_creative.basic_api_call_structured(concept)
        print(f"Generated {len(deck_structure.slides)} slides")
        
        for i, slide in enumerate(deck_structure.slides, 1):
            print(f"Slide {i}: {slide.slide_type}")
            
    except Exception as e:
        print(f"Error generating deck structure: {e}")
        sys.exit(1)
    
    # Copy the source presentation
    print(f"Copying source presentation...")
    copy_metadata = {'name': args.output_title}
    
    try:
        copied_file = drive_service.files().copy(
            fileId=args.presentation_id,
            body=copy_metadata
        ).execute()
        
        copied_presentation_id = copied_file.get('id')
        print(f"Presentation copied successfully: https://docs.google.com/presentation/d/{copied_presentation_id}/edit")
    except Exception as e:
        print(f"Error copying presentation: {e}")
        sys.exit(1)
    
    # Process each slide
    slide_index = 0
    
    for i, slide in enumerate(deck_structure.slides, 1):
        print(f"Processing slide {i}: {slide.slide_type}")
        
        try:
            slide_content = slide.slide_content
            slide_template_name = os.path.join(args.templates_dir, f"{slide.slide_type}.txt")
            
            # Check if template file exists
            if not os.path.isfile(slide_template_name):
                print(f"Warning: Template file not found: {slide_template_name}")
                continue
            
            with open(slide_template_name, 'r') as f:
                slide_template_data = json.load(f)
            
            slide_template = slide_template_data['slide']['json_object']
            slide_text_sections = slide_template_data['slide'].get('text_sections', [])
            
            # Apply text replacements
            text_content_index = 0
            for obj in slide_template['requests']:
                if "replaceAllText" in obj:
                    if text_content_index < len(slide_content):
                        obj["replaceAllText"]["replaceText"] = slide_content[text_content_index]
                        text_content_index += 1
                    else:
                        print(f"Warning: Not enough content for slide {i}, request {text_content_index}")
            
            # Update slide IDs
            request = slide_template
            old_id = list(request['requests'][0]['duplicateObject']['objectIds'].items())[0][0]
            new_slide_id = f"NewSlide_{uuid.uuid4().hex[:8]}"
            
            request['requests'][0]['duplicateObject']['objectIds'][old_id] = new_slide_id
            request = replace_page_object_ids(request, old_id, new_slide_id)
            
            # Create the slide
            try:
                response = slides_service.presentations().batchUpdate(
                    presentationId=copied_presentation_id,
                    body=request
                ).execute()
                
                slide_id = response['replies'][0]['duplicateObject']['objectId']
                
                # Position the slide
                insertion_object = {
                    "requests": [{
                        "updateSlidesPosition": {
                            "slideObjectIds": [slide_id],
                            "insertionIndex": slide_index
                        }
                    }]
                }
                
                slides_service.presentations().batchUpdate(
                    presentationId=copied_presentation_id,
                    body=insertion_object
                ).execute()
                
                slide_index += 1
                print(f"Successfully created slide {i}")
                
            except HttpError as e:
                print(f"Error creating slide {i}: {e}")
            
        except Exception as e:
            print(f"Error processing slide {i}: {e}")
    
    print(f"Deck creation complete: https://docs.google.com/presentation/d/{copied_presentation_id}/edit")


if __name__ == "__main__":
    main()